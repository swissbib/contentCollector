import os
from datetime import datetime, timedelta
import types
import re
from swissbibUtilities import SwissbibUtilities




__author__ = 'swissbib'



class ApplicationContext:


    def __init__(self):
        pass




    def setMongoWrapper(self,wrapper):
        self.mongoWrapper = wrapper


    def getMongoWrapper(self):
        if hasattr(self,'mongoWrapper'):
            return self.mongoWrapper
        else:
            return None




    def setConfiguration(self,configuration):
        self.configuration = configuration


    def getConfiguration(self):
        if hasattr(self,'configuration'):
            return self.configuration
        return None



    def setResultCollector(self,collector):
        self.rCollector = collector


    def getResultCollector(self):
        if hasattr(self,'rCollector'):
            return self.rCollector
        else:
            return None


    def setWriteContext(self,writeContext):
        self.wContext = writeContext


    def getWriteContext(self):
        if hasattr(self,'wContext'):
            return self.wContext
        else:
            return None


class NLApplicationContext(ApplicationContext):
    def __init__(self):
        ApplicationContext.__init__(self)


    def setModsTransformation(self,modsTransformation):
        self.mTransformation = modsTransformation


    def getModsTransformation(self):
        if hasattr(self,'mTransformation'):
            return self.mTransformation
        else:
            return None




class WriteContext:

    def __init__(self,context):
        self.appContext = context
        self.granularityPattern = re.compile('Thh:mm:ssZ',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.nextTimeStamp = self.getNextTimestamp()
        self.footerWritten = False
        self.fileClosed = True



    def setOutFileName(self,fileName):
        self.outFileName = fileName
        self.wholeContentFile = open(self.outFileName,"w")
        self.fileClosed = False
        self.writeHeader()

    def getOutFileName(self):
        return self.outFileName

    def writeItem(self,item):
        tList = ['\n',item,"\n"]
        if self.appContext.getConfiguration().getWriteHarvestedFiles():
            self.wholeContentFile.writelines(tList)


    def closeWriteContext(self):

        if not self.wholeContentFile is None:
            self.writeFooter()
            self.flushContent()
            self.wholeContentFile.close()
            self.fileClosed = True
            self.wholeContentFile = None

        #todo: verschiebe file nach results

    def writeHeader(self):
        self.wholeContentFile.write("<collection>\n")

    def writeFooter(self):
        self.wholeContentFile.write("</collection>\n")


    def flushContent(self):
        self.wholeContentFile.flush()


    def moveContentFile(self):

        if not self.fileClosed is True:
            self.closeWriteContext()

        numberProcessedRecords = self.appContext.getResultCollector().getIncrementProcessedRecordNoFurtherDetails()
        maxDocuments = self.appContext.getConfiguration().getMaxDocuments()
        blocked = self.appContext.getConfiguration().getBlocked()
        #in case the configuration is set to blocked a

        if (not maxDocuments is None and not numberProcessedRecords is None
                and  int(numberProcessedRecords) > int(maxDocuments)) \
                or blocked:

            os.chdir(self.appContext.getConfiguration().getDumpDir())
            #collected content shouldn't be sent to CBS because number of collected records is too large
            os.system("mv " + self.appContext.getConfiguration().getSummaryContentFile() + " " + self.appContext.getConfiguration().getArchiveNotSent())
            tCommand = "gzip -9 " + self.appContext.getConfiguration().getArchiveNotSent() + os.sep + self.appContext.getConfiguration().getSummaryContentFile()
            os.system(tCommand)
            if not blocked:
                self.appContext.getConfiguration().setBlocked('true')

            os.chdir(self.appContext.getConfiguration().getResultDir())
            SwissbibUtilities.sendNotificationMail(receivers=self.appContext.getConfiguration().getEMailNotifification(),
                                                   network=self.appContext.getConfiguration().getNetworkPrefix(),
                                                   numberDocuments=numberProcessedRecords,
                                                   mailserver=self.appContext.getConfiguration().getMailServer())



        else:
            os.chdir(self.appContext.getConfiguration().getDumpDir())
            os.system("mv " + self.appContext.getConfiguration().getSummaryContentFile() + " " + self.appContext.getConfiguration().getArchiveDir())
            tCommand = "gzip -9 " + self.appContext.getConfiguration().getArchiveDir() + os.sep + self.appContext.getConfiguration().getSummaryContentFile()
            os.system(tCommand)

            os.chdir(self.appContext.getConfiguration().getResultDir())
            tCommand = "ln -s " + self.appContext.getConfiguration().getArchiveDir() + os.sep +\
                       self.appContext.getConfiguration().getSummaryContentFile() + ".gz " +\
                       self.appContext.getConfiguration().getSummaryContentFile() + ".gz"
            os.system(tCommand)

        if os.path.isdir(self.appContext.getConfiguration().getDumpDir()):
            os.system("rm -r " + self.appContext.getConfiguration().getDumpDir())


    def setAndWriteConfigAfterError(self):

        if not self.appContext is None and not self.appContext.getConfiguration() is None:

            cwd = os.getcwd()

            #we change at first directory because configfile-path might be relative
            os.chdir(self.appContext.getConfiguration().getApplicationDir())

            self.appContext.getConfiguration().setActionFinished("no")
            self.appContext.getConfiguration().setStoppageTime(str(datetime.now()))
            newConf = open(self.appContext.getConfiguration().getConfigFilename(),"w")
            newConf.write(self.appContext.getConfiguration().getXMLasString())
            newConf.close()


            os.chdir(cwd)


    def setAndWriteConfigAfterSuccess(self):

        if not self.appContext is None and not self.appContext.getConfiguration() is None:

            cwd = os.getcwd()

            #we change at first directory because configfile-path might be relative
            os.chdir(self.appContext.getConfiguration().getApplicationDir())

            self.appContext.getConfiguration().setTimestampUTC(self.nextTimeStamp)
            self.appContext.getConfiguration().setActionFinished("yes")
            self.appContext.getConfiguration().setCompleteListSize(str(self.appContext.getResultCollector().getNumberAllProcessedRecords()))

            self.appContext.getConfiguration().setStoppageTime(str(datetime.now()))
            conffilename = self.appContext.getConfiguration().getConfdir() + os.sep + os.path.basename(self.appContext.getConfiguration().getConfigFilename())
            newConf = open(conffilename,"w")
            newConf.write(self.appContext.getConfiguration().getXMLasString())
            newConf.close()

            os.chdir(cwd)
        else:
            print "writing of configuration file after successful processing wasn't possible - why is Appcontext or write Context None??"




    def handleOperationAfterError(self,exType=None, message="", additionalText=""):


        self.setAndWriteConfigAfterError()

        if not self.appContext.getResultCollector() is None and (
                                            self.appContext.getResultCollector().getRecordsDeleted() > 0 or
                                            self.appContext.getResultCollector().getRecordsToCBSInserted() > 0 or
                                            self.appContext.getResultCollector().getRecordsToCBSNoSkip() > 0 or
                                            self.appContext.getResultCollector().getRecordsToCBSUpdated() > 0 or

                                            self.appContext.getResultCollector().getRecordsSkipped() > 0 ) :

            self.moveContentFile()
            label = "an error occured - already collected content was moved"
        else:
            label = "an error occured - no already collected content to move available"


        if not exType is None:
            self.writeErrorLog(header="an error occured - already collected content was moved", message=[message,additionalText,exType])
        else:
            self.writeErrorLog(header="an error occured - already collected content was moved", message=[message,additionalText])




    def writeErrorLog(self,  header=None, message= None):

        if header is None:
            header = [str(datetime.now()) + " - error message"]
        elif isinstance(header,types.ListType):
            header.insert(0,str(datetime.now()) )
        else:
            header =  [str(datetime.now()) + " " + str(header)]

        if message is None:
            message = ["no error message provided"]
        elif isinstance(message,types.StringType):
            message = [message]
        elif isinstance(message,types.ListType):
            pass
        else:
            message = ["no proper error-message-type was provided"]

        if not  self.appContext is None and not self.appContext.getConfiguration() is None:
            #logTyp 2 = error message
            self._writeLog(header,message,logType=2)
        else:
            self._writeLog(header,message,logType=2, writeToStdOut=True)



    def writeLog(self,  header=None, message= None):


        if header is None:
            header = [str(datetime.now()) + " - log message"]
        elif isinstance(header,types.ListType):
            header.insert(0,str(datetime.now()) )
        else:
            header =  [str(datetime.now()) + " " + str(header)]

        if message is None:
            message = ["no log message provided"]
        elif isinstance(message,types.StringType):
            message = [message]
        elif isinstance(message,types.ListType):
            pass
        else:
            message = ["no proper log-message-type was provided"]

        if not  self.appContext is None and not self.appContext.getConfiguration() is None:
            #logTyp 1 = log message standard
            self._writeLog(header,message)
        else:
            self._writeLog(header,message,writeToStdOut=True)



    def _writeLog(self, header, message, logType=1,writeToStdOut=False):
        try:

            if writeToStdOut is False:

                if logType == 1: #log-message

                    fileName = self.appContext.getConfiguration().getProcessLogDir() + os.sep + self.appContext.getConfiguration().getProcessLogFile()
                else: #error-message
                    fileName = self.appContext.getConfiguration().getErrorLogDir() + os.sep + self.appContext.getConfiguration().getErrorLogFile()

                procLog = open(fileName,"a")

                procLog.write('-'*60 + "\n")
                procLog.write("\n".join(header) + "\n")

                for value in message:
                    procLog.write(str(value) + "\n")
                procLog.write('-'*60 + "\n")

                procLog.close()

            else:
                print '-'*60 + "\n"
                print "\n".join(header) + "\n"
                for value in message:
                    print str(value) + "\n"
                print '-'*60 + "\n"


        except Exception as exInWrite:
            procLog = open(self.appContext.getConfiguration().getErrorLogDir() + os.sep + self.appContext.getConfiguration().getErrorLogFile(),"a")
            procLog.write('-'*60 + "\n")
            procLog.write("error while writing error log")
            procLog.write(str(exInWrite))
            procLog.write('-'*60 + "\n")
            procLog.close()



    def getNextTimestamp(self):

        granularity = self.appContext.getConfiguration().getGranularity()

        if not granularity is None and  self.granularityPattern.search(granularity):
            cTimeUTC =  datetime.utcnow()
            nTList = [str(cTimeUTC.date()),"T",str(cTimeUTC.hour),":",str(cTimeUTC.minute),":",str(cTimeUTC.second),"Z"]
            return "".join(nTList)
        else:
            return datetime.utcnow().strftime("%Y-%m-%d")






class HarvestingWriteContext(WriteContext):

    def __init__(self,context):
        WriteContext.__init__(self,context)
        self.setOutFileName("".join([self.appContext.getConfiguration().getDumpDir(),os.sep, self.appContext.getConfiguration().getSummaryContentFile()]))



    def getOutFileName(self):
        return self.outFileName







class FilePushWriteContext(WriteContext):

    def __init__(self,context):
        WriteContext.__init__(self,context)

    def closeWriteContext(self):

        #kann ich den pfad eines files abfragen
        self.writeFooter()
        self.wholeContentFile.close()
        os.system("mv " + self.getOutFileName() + " " + self.appContext.getConfiguration().getArchiveDir())
        tCommand = "gzip -9 --force " + self.appContext.getConfiguration().getArchiveDir() + os.sep + os.path.basename(self.getOutFileName())
        os.system(tCommand)

        resultDir = self.appContext.getConfiguration().getResultDir()
        os.chdir(resultDir)
        tCommand = "ln -s " + self.appContext.getConfiguration().getArchiveDir() + os.sep + \
                   os.path.basename(self.getOutFileName()) + ".gz " + \
                   self.appContext.getConfiguration().getResultDir() + \
                   os.sep + os.path.basename(self.getOutFileName()) + ".gz"
        os.system(tCommand)

        self.appContext.getResultCollector().setCollectedArchiveFiles(os.path.basename(self.getOutFileName()) + '.gz',self.appContext.getConfiguration().getArchiveDir() )

        #os.chdir(self.appContext.getConfiguration().getClusteringDir())

        #os.system("rm -r " + self.appContext.getConfiguration().getCollectedDir())


    def handleOperationAfterError(self,exType=None, message="", additionalText=""):


        self.setAndWriteConfigAfterError()
        label = "an error occured in Nebis File Processig: "

        if not exType is None:
            self.writeErrorLog(header=label, message=[message,additionalText,exType])
        else:
            self.writeErrorLog(header=label, message=[message,additionalText])



class FileWebdavWriteContext(WriteContext):

    def __init__(self,context):
        WriteContext.__init__(self,context)

    def setOutFileName(self,fileName):
        self.outFileName = fileName

        self.outFileNameWithPath = self.appContext.getConfiguration().getDumpDir() + os.sep + self.outFileName

        self.wholeContentFile = open(self.outFileNameWithPath,"w")
        self.writeHeader()


    def closeWriteContext(self):

        #kann ich den pfad eines files abfragen
        self.writeFooter()
        self.wholeContentFile.close()
        os.system("mv " + self.outFileNameWithPath + " " + self.appContext.getConfiguration().getArchiveDir())
        fileInArchive = self.appContext.getConfiguration().getArchiveDir() + os.sep + self.outFileName
        tCommand = "gzip -9 --force " + fileInArchive
        os.system(tCommand)
        fileInArchiveZipped = fileInArchive + ".gz"

        os.chdir(self.appContext.getConfiguration().getResultDir())
        tCommand = "ln -s " + fileInArchiveZipped  + " " +self.outFileName + ".gz"
        os.system(tCommand)
        self.appContext.getResultCollector().setCollectedArchiveFiles(self.outFileName + ".gz",self.appContext.getConfiguration().getArchiveDir() )



class TaskContext:


    def __init__(self,appContext=None):
        self.appContext = appContext


    def getDBWrapper(self):
        return self.appContext.getMongoWrapper()

    def getConfiguration(self):
        return self.appContext.getConfiguration()


    def getResultCollector (self):

        return self.appContext.getResultCollector()


    def getWriteContext(self):

        return self.appContext.getWriteContext()



class StoreNativeRecordContext(TaskContext):

    def __init__(self,appContext=None,rID=None,singleRecord="",deleted=False):

        TaskContext.__init__(self,appContext=appContext)
        self.dateTimeStamp = re.compile('<header.*?>.*?<datestamp>(.*?)</datestamp>.*?</header>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.rID = rID
        self.singleRecord = singleRecord
        self.deleted = deleted


    def getID(self):

        return self.rID

    #todo: necessary only for Initial GND??
    def setID(self,rID):

        self.rID = rID

    def getRecordTimestamp(self):
        recordTimestamp = None
        if not self.singleRecord is None and self.appContext.getConfiguration().getAddRecordTimeStamp():
            existTimestamp = self.dateTimeStamp.search(self.singleRecord)
            if existTimestamp:
                recordTimestamp = existTimestamp.group(1)

        return recordTimestamp


    def getRecord(self):

        return self.singleRecord

    #we need this method because in relation to GND (initial loading)
    #sentences are going to be prepared before storing into Mongo
    #this is done 'after' creation of the object
    def setRecord(self, record):

        self.singleRecord = record


    def isDeleted(self):

        return self.deleted




class StoreNativeNLRecordContext(StoreNativeRecordContext):


    def __init__(self, appContext=None, rID=None, jatsRecord="", deleted=False,
                 modsRecord=""):
        StoreNativeRecordContext.__init__(self,appContext,rID,jatsRecord,deleted)

        self.modsRecord = modsRecord


    def getModsRecord(self):
        return self.modsRecord


    # we need this method because in relation to GND (initial loading)
    # sentences are going to be prepared before storing into Mongo
    # this is done 'after' creation of the object
    def setModsRecord(self, record):
        self.modsRecord = record
