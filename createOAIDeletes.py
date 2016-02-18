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
import re
#from createOAIDeletes import CreateSNLDeleteMessages
#import CreateSNLDeleteMessages




__author__ = 'swissbib - UB Basel, Switzerland, Guenter Hipler'
__copyright__ = "Copyright 2016, swissbib project"
__credits__ = "https://github.com/swissbib/contentCollector/issues/5"
__license__ = "http://opensource.org/licenses/gpl-2.0.php GNU General Public License"
__version__ = "0.1"
__maintainer__ = "Guenter Hipler"
__email__ = "guenter.hipler@unibas.ch"
__status__ = "in development"
__description__ = """
                    https://github.com/swissbib/contentCollector/issues/5
                    plus general enhancement to create delete messages e.g. for summon ebooks
                    """


class CreateDeletes:


    def __init__(
            self, applicationContext=None,  writeContext = None):

        self.applicationContext = applicationContext
        self.writeContext = writeContext


    def setFileName(self,fileName):
        self.fileName = fileName

    def createGeneratorForDeleteIds(self):
        #default Generator returns nothing
        emptyList = range(0)
        for i in emptyList:
            yield i


    def getFileName(self):
        return self.fileName


    def createXMLDeleteStructure(self, recordID):
        return "<record><header status=\"deleted\"><identifier>" + recordID + \
                                 "</identifier></header></record>"

    def processDeletes(self):


        for idToDelete in self.createGeneratorForDeleteIds():


            self.applicationContext.getResultCollector().addRecordsToCBSNoSkip(1)
            recordStructure = self.createXMLDeleteStructure(idToDelete)

            self.applicationContext.getWriteContext().writeItem(recordStructure)

            for taskName,task  in  self.applicationContext.getConfiguration().getDedicatedTasks().items():

                try:

                    if isinstance(task,PersistRecordMongo):
                        taskContext = StoreNativeRecordContext(appContext=self.applicationContext,
                                                                rID=idToDelete,singleRecord=recordStructure,
                                                                deleted=True)
                        task.processRecord(taskContext)
                except Exception as pythonBaseException:

                    self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a task"],message=[str(pythonBaseException), idToDelete])
                    continue

        #self._moveFileWithDeletedIds(deletesAbsolutePath, oaiDeletes)


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


    def _moveFileWithDeletedIds(self,pathSourceFileAbsolute, sourceFileName):
        archiveDirSourceDeleteMessages = self.applicationContext.getConfiguration().getArchiveDir() + os.sep + "processedDeleteMessages"
        if not os.path.isdir(archiveDirSourceDeleteMessages):
            os.system("mkdir -p " + archiveDirSourceDeleteMessages)

        targetFile = "".join(['{:%Y%m%d%H%M%S}'.format(datetime.now()),".",sourceFileName])
        deletesFileAbsolutePath = pathSourceFileAbsolute + os.sep + sourceFileName
        os.system("mv " + deletesFileAbsolutePath + " " + archiveDirSourceDeleteMessages + os.sep + targetFile)

        tCommand = "gzip -9 " + archiveDirSourceDeleteMessages + os.sep + targetFile
        os.system(tCommand)


class CreateSNLDeleteMessages(CreateDeletes):
    pass

class CreateSummonDeleteMessages(CreateDeletes):

    def __init__(self,
                 applicationContext=None,  writeContext = None):
        CreateDeletes.__init__(self,applicationContext=applicationContext, writeContext=writeContext)

        self.pSummonDeletedRecordId = re.compile('^(.*?),',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def createGeneratorForDeleteIds(self):

        deleteDir = self.applicationContext.getConfiguration().getOaiDeleteDir()

        for deleteMessageFile in [ f for f in listdir(deleteDir) if isfile(join(deleteDir,f)) ]:

            if (deleteMessageFile.startswith(self.applicationContext.getConfiguration().getPrefixSummaryFile() + "-")):
                deletesAbsolutePath = join(deleteDir,deleteMessageFile)
                fileHandle = open(deletesAbsolutePath, 'r')
                linenumber = 0
                for line in fileHandle:
                    if linenumber == 0:
                        # we don't want the first line of the csv header file
                        linenumber += 1
                        continue
                    searchedNumberPattern =  self.pSummonDeletedRecordId.search(line)
                    if searchedNumberPattern:
                        recordNumber =  searchedNumberPattern.group(1)
                        #print recordNumber
                        yield recordNumber

                fileHandle.close()
                self._moveFileWithDeletedIds(deleteDir, deleteMessageFile)







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

        deleteGenerator = globals()[sConfigs.getDeleteMessagesProcessorType()](appContext,writeContext)



        if deleteGenerator.hasOAIDeletes():

            deleteGenerator.processDeletes()
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




