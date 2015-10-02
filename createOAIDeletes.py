from datetime import datetime
import os

from urllib2 import HTTPError, URLError
from oaipmh.error import NoRecordsMatchError, ErrorBase, BadVerbError
from argparse import ArgumentParser

from swissbibHarvestingConfigs import HarvestingConfigs
from swissbibOAIClient import ReadError
from swissbibUtilities import  ErrorHashProcesing, ResultCollector, SwissbibUtilities

from swissbibMongoHarvesting import MongoDBHarvestingWrapper

from Context import ApplicationContext, HarvestingWriteContext
from os import listdir
from os.path import isfile, join
from harvestingTasks import PersistRecordMongo
from Context import StoreNativeRecordContext




__author__ = 'swissbib - UB Basel, Switzerland, Guenter Hipler'
__copyright__ = "Copyright 2015, swissbib project"
__credits__ = "https://github.com/swissbib/contentCollector/issues/5"
__license__ = "http://opensource.org/licenses/gpl-2.0.php GNU General Public License"
__version__ = "0.1"
__maintainer__ = "Guenter Hipler"
__email__ = "guenter.hipler@unibas.ch"
__status__ = "in development"
__description__ = """
                    https://github.com/swissbib/contentCollector/issues/5
                    """


class CreateOAIDeletes:


    def __init__(
            self, applicationContext=None,  writeContext = None):

        self.applicationContext = applicationContext
        self.writeContext = writeContext


    def setFileName(self,fileName):
        self.fileName = fileName

    def getFileName(self):
        return self.fileName

    def processOAIDeletes(self):
        deleteDir = self.applicationContext.getConfiguration().getOaiDeleteDir()
        #oai:helveticat.ch:244   ->> SNL
        #<record><header status="deleted"><identifier>aleph-publish:004127018</identifier></header></record>
        #oai:aleph.unibas.ch:DSV01-005588958


        for oaiDeletes in [ f for f in listdir(deleteDir) if isfile(join(deleteDir,f)) ]:

            self.applicationContext.getConfiguration().getPrefixSummaryFile()

            if (oaiDeletes.startswith(self.applicationContext.getConfiguration().getPrefixSummaryFile() + "-")):

                deletesAbsolutePath = join(deleteDir,oaiDeletes)
                fileHandle = open(deletesAbsolutePath, 'r')
                for line in fileHandle:

                    #we don't want to process empty lines
                    line = line.strip('\n\r')
                    if len(line) > 0:
                        self.applicationContext.getResultCollector().addRecordsToCBSNoSkip(1)
                        recordId = self.getRecordId(line.strip('\n\r'))
                        oaiDeleteStructure = "<record><header status=\"deleted\"><identifier>" + line + \
                                             "</identifier></header></record>"

                        self.applicationContext.getWriteContext().writeItem(oaiDeleteStructure)

                        for taskName,task  in  self.applicationContext.getConfiguration().getDedicatedTasks().items():

                            try:

                                if isinstance(task,PersistRecordMongo):
                                    taskContext = StoreNativeRecordContext(appContext=self.applicationContext,
                                                                            rID=recordId,singleRecord=oaiDeleteStructure,
                                                                            deleted=True)
                                    task.processRecord(taskContext)
                            except Exception as pythonBaseException:

                                self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a task"],message=[str(pythonBaseException), line])
                                continue

                fileHandle.close()
                self._moveFileWithDeletedIds(deletesAbsolutePath, oaiDeletes)


    def hasOAIDeletes(self):
        deleteDir = self.applicationContext.getConfiguration().getOaiDeleteDir()
        hasDeletes = False
        for oaiDeletes in [ f for f in listdir(deleteDir) if isfile(join(deleteDir,f)) ]:
            if (oaiDeletes.startswith(self.applicationContext.getConfiguration().getPrefixSummaryFile() + "-")):
                hasDeletes = True
                break
        return hasDeletes


    def getRecordId(self,idWithoutNetwork):
        return "(" + self.applicationContext.getConfiguration().getNetworkPrefix() + ")" + idWithoutNetwork


    def _moveFileWithDeletedIds(self,fileNameAbsolute, fileName):
        movedFile = self.applicationContext.getConfiguration().getArchiveDir() + os.sep + fileName +  "_deletesNoOai"
        os.system("mv " + fileNameAbsolute + " " + movedFile)
        tCommand = "gzip -9 " + movedFile
        os.system(tCommand)


if __name__ == '__main__':


    oParser = None
    args = None
    sConfigs = None
    cwd = None
    startTime = None
    sU = None
    rCollector = None
    untilDate = None
    mongoWrapper = None
    client = None
    writeContext = None
    appContext = None



    def _writeErrorMessages(writeContext, exceptionType, exceptionName):
        if not writeContext is None:
            writeContext.handleOperationAfterError(exType=exceptionType,
                                                        message="Exception " + exceptionName + " in swissbibHarvesting.py" )
        else:
            print "no WriteContext after Error: " + exceptionName + " Handler\n"
            print "redirect error message to stdout\n"
            print str(exceptionType) + "\n"


    try:

        oParser = ArgumentParser()
        oParser.add_argument("-c", "--config", dest="confFile")
        args = oParser.parse_args()



        sConfigs = HarvestingConfigs(args.confFile)
        sConfigs.setApplicationDir(os.getcwd())


        startTime = datetime.now()
        sU = SwissbibUtilities()
        sU.initializeDirectoriesForHarvesting(sConfigs)

        rCollector = ResultCollector()
        appContext = ApplicationContext()
        appContext.setResultCollector(rCollector)
        appContext.setConfiguration(sConfigs)


        mongoWrapper = MongoDBHarvestingWrapper(applicationContext=appContext)

        appContext.setMongoWrapper(mongoWrapper)


        writeContext = HarvestingWriteContext(appContext)
        appContext.setWriteContext(writeContext)
        deleteGenerator = CreateOAIDeletes(
                                   applicationContext=appContext,
                                   writeContext=writeContext)

        if deleteGenerator.hasOAIDeletes():

            deleteGenerator.processOAIDeletes()
            writeContext.closeWriteContext()
            writeContext.moveContentFile()




    except NoRecordsMatchError as noRecords:
        _writeErrorMessages(writeContext,noRecords,"NoRecordsMatchError")


    except BadVerbError as badverbException:
        _writeErrorMessages(writeContext,badverbException,"BadVerbError")


    except ReadError as readException:
        _writeErrorMessages(writeContext,readException,"ReadError")



    except ErrorHashProcesing as hashError:
        _writeErrorMessages(writeContext,hashError,"ErrorHashProcesing")


    except ErrorBase as errorBase:
        _writeErrorMessages(writeContext,errorBase,"ErrorBase")


    except HTTPError as httpError:
        _writeErrorMessages(writeContext,httpError,"HTTPError")



    except URLError as urlError:
        _writeErrorMessages(writeContext,urlError,"URLError")

    except Exception as pythonBaseException:
        _writeErrorMessages(writeContext,pythonBaseException,"Exception")


    else:

        if not writeContext is None:
            writeContext.setAndWriteConfigAfterSuccess()


            usedOAIParameters = ""
            if not  appContext.getResultCollector() is None:
                if appContext.getResultCollector().getRecordsDeleted() > 0:
                    procMess = ["start time: ",  str( startTime) ,
                                "end time: " + str(datetime.now()),
                                "outputfile: " + appContext.getConfiguration().getSummaryContentFile(),
                                "records deleted and shipped to CBS: " + str(appContext.getResultCollector().getRecordsDeleted()),
                                "\n"]

                    writeContext.writeLog(header="records deleted we haven't got via the standard OAI channel",message=procMess )
                else:
                    procMess = ["\n",
                                "start time: ",  str( startTime) ,
                                "end time: " + str(datetime.now()),
                                "\n"]

                    writeContext.writeLog(header="We haven't got a compilation of deleted records that should be shipped to CBS",message=procMess )

            else:
                writeContext.writeErrorLog(message= "ResultCollector was None - Why?")
                writeContext.writeLog(message= "ResultCollector was None - Why?")


    if not mongoWrapper is None:
        mongoWrapper.closeResources()

    os.chdir(appContext.getConfiguration().getApplicationDir())




