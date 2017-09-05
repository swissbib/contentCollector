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
from os.path import isfile, join, isdir
from harvestingTasks import PersistRecordMongo, PersistNLMongo, PersistSpringerNLMongo
from Context import StoreNativeRecordContext, StoreNativeNLRecordContext
import re


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

        deleteDir = self.applicationContext.getConfiguration().getOaiDeleteDir()

        generatorActivated = False
        for deleteMessageFile in [f for f in listdir(deleteDir) if isfile(join(deleteDir, f))]:

            if (deleteMessageFile.startswith(self.applicationContext.getConfiguration().getPrefixSummaryFile() + "-")):

                deletesAbsolutePath = join(deleteDir, deleteMessageFile)
                fileHandle = open(deletesAbsolutePath, 'r')
                linenumber = 0
                for line in fileHandle:
                    if not self.filterForCurrentLine(linenumber,line):
                        # we don't want the first line of the csv header file
                        linenumber += 1
                        continue
                    linenumber += 1
                    recordNumber = self.getIdFromStructure(line)
                    if not recordNumber is None:
                        generatorActivated = True
                        yield recordNumber

                fileHandle.close()
                self._moveFileWithDeletedIds(deleteDir, deleteMessageFile)
        if not generatorActivated:
            #in case we haven't yielded any records a default empty list is created to satisfy the client expecting
            #a result of a list iteration
            emptyList = range(0)
            for i in emptyList:
                yield i


    def getFileName(self):
        return self.fileName


    def createXMLDeleteStructure(self, recordID):
        # 2016-04-18T07:18:44Z (as example)
        #we need the datetimestamp for the crafted delete structure because for the majaority of the repositories
        # (with the exception of Nebis and rero) we want to seperate this datetime-stamp in a single field of the
        #Mongo Index. And because we configured this for the default case it causes troubles when datetime-stamps
        #are not part of the crafted deleted structure
        currentTime = '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.now())
        return "<record><header status=\"deleted\"><identifier>" + recordID + \
                                 "</identifier>" + \
               "<datestamp>" + currentTime + "</datestamp>" + \
               "</header></record>"

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
        if isdir(deleteDir):
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

    def getIdFromStructure(self, structure):
        #default behaviour: structure is already the searched ID which should be deleted
        #we don't have to search the ID as part of the structure
        return structure.rstrip('\n\r ')

    def filterForCurrentLine(self, linenumber, structure):
        #default behaviour: use every single line
        return True


    def getCurrentTimeFormated(self):
        return '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.now())


class CreateSNLDeleteMessages(CreateDeletes):
    def __init__(self,
                 applicationContext=None, writeContext=None):
        CreateDeletes.__init__(self, applicationContext=applicationContext, writeContext=writeContext)
        #self.plineWithRecordId = re.compile('Record ID:', re.UNICODE | re.DOTALL | re.IGNORECASE)
        #self.psearchedRecordId = re.compile('.*?([\d]+)', re.UNICODE | re.DOTALL | re.IGNORECASE)



    #def filterForCurrentLine(self, linenumber, structure):
        # SNL sends us a text file (via email) which contains the following structure for each record to be deleted
        #matter of interest for us is only the line Record ID
        # Record ID: 1797285
        # Username: root
        # Timestamp: 24-NOV-2015 09:13:53
        # Bibliographic Level: m
        # Record Type: a
        # Record State: Deleted
        #hasSearchedPattern = self.plineWithRecordId.search(structure)
        #return hasSearchedPattern
        #this was the former version of the delivered messages. Now it seems we get single lines which contain only
        #the number we intended to extract
        #so we jab just use the parent method
    #    pass



    def processDeletes(self):

        for idToDelete in self.createGeneratorForDeleteIds():

            self.applicationContext.getResultCollector().addRecordsToCBSNoSkip(1)

            splitted = idToDelete.split('###')
            if not len(splitted) == 2:
                #we expect two Id's
                self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a record"],
                                                                        message=["iterator didn't provide the expected two IDs",
                                                                                 " ".join(splitted)])
                continue


            recordStructure = self.createXMLDeleteStructure(splitted[1])

            self.applicationContext.getWriteContext().writeItem(recordStructure)


            recordStructureMongo = self._createRecordStructureForMongo(splitted[0])

            for taskName, task in self.applicationContext.getConfiguration().getDedicatedTasks().items():

                try:

                    if isinstance(task, PersistRecordMongo):
                        taskContext = StoreNativeRecordContext(appContext=self.applicationContext,
                                                               rID=splitted[0], singleRecord=recordStructureMongo,
                                                               deleted=True)
                        task.processRecord(taskContext)
                except Exception as pythonBaseException:

                    self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a task"],
                                                                            message=[str(pythonBaseException),
                                                                                     idToDelete])
                    continue

                    # self._moveFileWithDeletedIds(deletesAbsolutePath, oaiDeletes)


    def getIdFromStructure(self, structure):
        # default behaviour: structure is already the searched ID which should be deleted
        # we don't have to search the ID as part of the structure
        #searchedNumberPattern = self.psearchedRecordId.search(structure)
        #if searchedNumberPattern:
        #    numberInline = searchedNumberPattern.group(1)
        #    #noch aufbereiten
        #    return numberInline
        #    #return searchedNumberPattern.group(1)
        #else:
        #    return None

        #for SNL the procedure is a little bit tricky...
        #the CBS delete messages should use a number with nine charracters padded with leading zeroes if less and an
        #additional prefix vtls. Otherwise CBS seems not to be able (at least in the current implementation to delete
        #the records

        #for the raw data storage Mongo we need the original id together with the leading OAI repository label
        #so I used the solution to return both numbers (getched by the iterator) with the disadvantage to implement a
        #specialized processDeletes method being able to handle bothe numbers (not very nice...)

        idOnly = structure.rstrip('\n\r ')
        paddingAndAligned = 'vtls' + '{:0>9}'.format(idOnly)
        return '(SNL)oai:helveticat.ch:' + idOnly + '###' + paddingAndAligned

    def _createRecordStructureForMongo(self, recordID):
        # 2016-04-18T07:18:44Z (as example)
        #we need the datetimestamp for the crafted delete structure because for the majaority of the repositories
        # (with the exception of Nebis and rero) we want to seperate this datetime-stamp in a single field of the
        #Mongo Index. And because we configured this for the default case it causes troubles when datetime-stamps
        #are not part of the crafted deleted structure

        return "<record><header status=\"deleted\"><identifier>" + recordID + \
                                 "</identifier>" + \
               "<datestamp>" + self.getCurrentTimeFormated() + "</datestamp>" + \
               "</header></record>"



class CreateIDSBBDeleteMessages(CreateDeletes):
    def __init__(self,
                 applicationContext=None, writeContext=None):
        CreateDeletes.__init__(self, applicationContext=applicationContext, writeContext=writeContext)


    def getRecordId(self,idWithoutNetwork):

        return "".join("oai:aleph.unibas.ch:DSV01-" + idWithoutNetwork)


    def createXMLDeleteStructure(self, recordID):
        # 2016-04-18T07:18:44Z (as example)
        #we need the datetimestamp for the crafted delete structure because for the majaority of the repositories
        # (with the exception of Nebis and rero) we want to seperate this datetime-stamp in a single field of the
        #Mongo Index. And because we configured this for the default case it causes troubles when datetime-stamps
        #are not part of the crafted deleted structure
        currentTime = '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.now())
        return "<record><header status=\"deleted\"><identifier>" + "".join(["oai:aleph.unibas.ch:DSV01-",recordID]) + \
                                 "</identifier>" + \
               "<datestamp>" + currentTime + "</datestamp>" + \
               "<setSpec>SWISSBIB-FULL-OAI</setSpec>" + \
               "</header></record>"


    def getIdFromStructure(self, structure):

        idOnly = structure.rstrip('\n\r ')
        return '(IDSBB)oai:aleph.unibas.ch:DSV01-' + idOnly + '###' + idOnly


    def processDeletes(self):

        for idToDelete in self.createGeneratorForDeleteIds():
            self.applicationContext.getResultCollector().addRecordsToCBSNoSkip(1)
            splitted = idToDelete.split('###')
            if not len(splitted) == 2:
                self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a record"],
                                                                        message=["iterator didn't provide the expected two IDs",
                                                                                 " ".join(splitted)])
                continue


            recordStructure = self.createXMLDeleteStructure(splitted[1])
            self.applicationContext.getWriteContext().writeItem(recordStructure)


            #recordStructureMongo = self._createRecordStructureForMongo(splitted[0])

            for taskName, task in self.applicationContext.getConfiguration().getDedicatedTasks().items():

                try:

                    if isinstance(task, PersistRecordMongo):
                        taskContext = StoreNativeRecordContext(appContext=self.applicationContext,
                                                               rID=splitted[0], singleRecord=recordStructure,
                                                               deleted=True)
                        task.processRecord(taskContext)
                except Exception as pythonBaseException:

                    self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a task"],
                                                                            message=[str(pythonBaseException),
                                                                                     idToDelete])
                    continue





class CreateSummonDeleteMessages(CreateDeletes):

    def __init__(self,
                 applicationContext=None,  writeContext = None):
        CreateDeletes.__init__(self,applicationContext=applicationContext, writeContext=writeContext)

        self.pSummonDeletedRecordId = re.compile('^(.*?)$',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getIdFromStructure(self, structure):
        # default behaviour: structure is already the searched ID which should be deleted
        # we don't have to search the ID as part of the structure
        searchedNumberPattern = self.pSummonDeletedRecordId.search(structure)
        if searchedNumberPattern:
            return searchedNumberPattern.group(1)
        else:
            return None

    def filterForCurrentLine(self, linenumber, structure):
        #summon file with records to be deleted is a CSV structure with the first line as header
        #possible alternative: look for patterns
        #return False
        return False if linenumber == 0 else True


class CreateNationalLicencesDeleteMessages(CreateDeletes):
    def __init__(self,
                 applicationContext=None, writeContext=None):
        CreateDeletes.__init__(self, applicationContext=applicationContext, writeContext=writeContext)

    #for National Licences, the file has a list of id's like this :
        #cambridge-10.1017/S0021875816001067
        #cambridge-10.1017/S0021875816001225
        #cambridge-10.1017/S0021875816001122

    def processDeletes(self):

        for idToDelete in self.createGeneratorForDeleteIds():

            self.applicationContext.getResultCollector().addRecordsToCBSNoSkip(1)




            recordStructure = self.createXMLDeleteStructure(idToDelete)

            self.applicationContext.getWriteContext().writeItem(recordStructure)


            for taskName, task in self.applicationContext.getConfiguration().getDedicatedTasks().items():

                try:

                    if isinstance(task, PersistNLMongo):
                        taskContext = StoreNativeNLRecordContext(appContext=self.applicationContext,
                                                               rID=idToDelete, jatsRecord=recordStructure, modsRecord=recordStructure,
                                                               deleted=True)
                        task.processRecord(taskContext)

                    if isinstance(task, PersistSpringerNLMongo):
                        taskContext = StoreNativeNLRecordContext(appContext=self.applicationContext,
                                                               rID=idToDelete, modsRecord=recordStructure,
                                                               deleted=True)
                        task.processRecord(taskContext)
                except Exception as pythonBaseException:

                    self.applicationContext.getWriteContext().writeErrorLog(header=["error while processing a task"],
                                                                            message=[str(pythonBaseException),
                                                                                     idToDelete])
                    continue

                    # self._moveFileWithDeletedIds(deletesAbsolutePath, oaiDeletes)




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
            writeContext.setAndWriteConfigAfterSuccess(setTimeStamp=False)


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




