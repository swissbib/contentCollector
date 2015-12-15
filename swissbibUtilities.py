import os
import re

from xml.parsers.expat import ParserCreate
from oaipmh.error import ErrorBase
from oaipmh.metadata import MetadataRegistry
from pyexpat import ExpatError
from oaipmh.validation import ValidationSpec, validate
from datetime import datetime, timedelta

import xml
from swissbibHash import HashMarcContent, HashSwissBibMarcContent, HashDcContent, HashReroMarcContent, HashNebisMarcContent
#import swissbibHash
import smtplib






__author__ = 'swissbib'



class SwissbibUtilities():


    def __init__(self):

        self.parser = ParserCreate()
        self.recordsDeleted = 0
        self.recordsSkipped = 0
        self.recordsparseError = 0
        self.recordsToCBSInserted = 0
        self.recordsToCBSUpdated = 0

    @staticmethod
    def addBlockedMessageToLogSummary(procMess,configuration):
            if configuration.getBlocked():
                procMess.append("because process is blocked, collected content wasn't sent to CBS - there should be no symbolic link in the results directory")
            return procMess


    @staticmethod
    def sendNotificationMail(receivers="swissbib-ub@unibas.ch",
                                network="?",
                                numberDocuments="?",
                                mailserver="smtp.unibas.ch",
                                sender="swissbib-ub@unibas.ch"):

            receivers = receivers.split(';')
            to = ""
            for recipient in receivers:
                to += "\"" + recipient + "\" <" + recipient + ">;"
            to =  to[:-1]


            message =   ["From: \"{0}\" <{0}>",
                        "To: {1}",
                        "Subject: collected content not sent to CBS for {2}","",
                        "network: {2}",
                        "number of records: {3}",
                        "status of the repository is now blocked which means you have to activate the symbolic link on the host by yourself.",
                        "Additionally  you have to change the configuration from <blocked>TRUE</blocked> to <blocked/> in the configuration file for this source. (Otherwise the next collected documents are again not sent to CBS)"]


            #message = "\n".join(message).format(sender,";".join(receivers),network,str(numberDocuments))
            message = "\n".join(message).format(sender,to,network,str(numberDocuments))

            try:
                smtpObj = smtplib.SMTP(mailserver)
                smtpObj.sendmail(sender, receivers, message)

            except smtplib.SMTPException as smtpException:
               print smtpException.message
            except Exception as exception:
                print exception.message


    def getStructureHeaderPattern(self):
        return re.compile('<\?xml.*?<ListRecords>',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getStructureHeaderNEBISPattern(self):
        return re.compile("<\?xml.*?<identifier>(.*?)</identifier></header><metadata>",re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getWholeNEBISMarcPattern(self):
        #return re.compile("<ListRecords>(.*?)</ListRecords>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        return re.compile("<ListRecords>(.*?<metadata>).*?(<leader>.*?)</record>(.*?)</ListRecords>",re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getWholeNEBISMarcCorrectPattern(self):
        #return re.compile("<ListRecords>(.*?)</ListRecords>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        return re.compile("<ListRecords>(.*?<metadata>).*?(<leader>.*?)</record>(.*?)</ListRecords>",re.UNICODE | re.DOTALL | re.IGNORECASE)



    def getAllRecordsPattern(self):
        return re.compile('<record>.*?</record>',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getFineGranularityPatter(self):
        return re.compile('Thh:mm:ssZ',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getRecordNEBISPattern(self):
        return re.compile('<metadata>(<record.*?</record>)</metadata>',re.UNICODE | re.DOTALL)

    def getStructureFooterPattern(self):
        return re.compile('</ListRecords>.*?</OAI-PMH>',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def getResumptionTokenPattern(self):
        return re.compile('<resumptionToken.*?>(.*?)</resumptionToken>',re.UNICODE | re.DOTALL |re.IGNORECASE)

    def getHarvestingErrorPattern(self):
        return re.compile('<error .*?>.*?</error>',re.UNICODE | re.DOTALL |re.IGNORECASE)


    def getDeletedRecordPattern(self):
        return re.compile('status="deleted',re.UNICODE | re.IGNORECASE)


    def getNEBISHeaderText(self):
        return """<?xml version = "1.0" encoding = "UTF-8"?><OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"><ListRecords>"""



    def getNEBISFooterText(self):
        return """</metadata></record></ListRecords></OAI-PMH>"""



    def parseSingleRecord(self,record):

        try:
            self.parser.Parse(record)
        except ExpatError as expatInst:
            errMess = [str(expatInst) + "\n",'-'*60 + "\n",record + "\n",'-'*60 + "\n","lineno: " + str(expatInst.lineno) + "\n"]
            #errMess.append(str(expatInst) + "\n")
            #errMess.append('-'*60 + "\n")
            #errMess.append(record + "\n")
            #errMess.append('-'*60 + "\n")
            #errMess.append("lineno: " + str(expatInst.lineno) + "\n")
            #todo: wo baue ich die Fehlermeldung auf??
            raise expatInst


    def getNextTimestamp(self,harvestingConfigs):



        if self.getFineGranularityPatter().search(harvestingConfigs.getGranularity()):
            cTimeUTC =  datetime.utcnow()
            nTList = [str(cTimeUTC.date()),"T",str(cTimeUTC.hour),":",str(cTimeUTC.minute),":",str(cTimeUTC.second),"Z"]
            return "".join(nTList)
        else:
            return datetime.utcnow().strftime("%Y-%m-%d")


    def getFromFormat(self,stringToFormat,harvestingConfigs):


        if self.getFineGranularityPatter().search(harvestingConfigs.getGranularity()):
            return datetime.strptime(stringToFormat,"%Y-%m-%dT%H:%M:%SZ")
        else:
            #return datetime.strptime(harvestingConfigs.getTimestampUTC(),"%Y-%m-%d").strftime("%Y-%m-%d")
            return datetime.strptime(stringToFormat,"%Y-%m-%d")


    def getDateFormat(self,stringToFormat,harvestingConfigs):


        if self.getFineGranularityPatter().search(harvestingConfigs.getGranularity()):
            return datetime.strptime(stringToFormat,"%Y-%m-%dT%H:%M:%SZ")
        else:
            #return datetime.strptime(harvestingConfigs.getTimestampUTC(),"%Y-%m-%d").strftime("%Y-%m-%d")
            return datetime.strptime(stringToFormat,"%Y-%m-%d")



    def isDayGranularity(self,harvestingConfigs):
         if self.getFineGranularityPatter().search(harvestingConfigs.getGranularity()):
             return False
         else:
             return True


    def getUntilDate(self,untilValue,harvestingConfigs):
        tUntilDate = None

        try:

            daysDelta = int (untilValue)
            tUntilDate = (datetime(datetime.today().year,datetime.today().month,datetime.today().day) + timedelta(daysDelta))
        except:
            tUntilDate = None
            try:
                tUntilDate = self.getDateFormat(untilValue,harvestingConfigs)
            except:
                tUntilDate = None


        return tUntilDate

    def initializeDirectoriesForHarvesting(self,harvestingConfigs):
        if not os.path.isdir(harvestingConfigs.getDumpDir()):
            os.system("mkdir -p " + harvestingConfigs.getDumpDir())
        if not os.path.isdir(harvestingConfigs.getErrorLogDir()):
            os.system("mkdir -p " + harvestingConfigs.getErrorLogDir())
        if not os.path.isdir(harvestingConfigs.getProcessLogDir()):
            os.system("mkdir -p " + harvestingConfigs.getProcessLogDir())
        if not os.path.isdir(harvestingConfigs.getResultDir()):
            os.system("mkdir -p " + harvestingConfigs.getResultDir())
        if not os.path.isdir(harvestingConfigs.getArchiveDir()):
            os.system("mkdir -p " + harvestingConfigs.getArchiveDir())


    def createHashType(self, harvestingConfigs, record):
        hashContent = globals()[harvestingConfigs.getHashRenderer()](harvestingConfigs)
        try:
            #Python 3
            #xml.sax.parseString(bytes(tRecord,"UTF-8"), scrapContent)
            xml.sax.parseString(record, hashContent)
            return hashContent
        except Exception as exceptionInst :
            operation = self.AdministrationOperation()
            hashError = operation.formatException(exceptionType=exceptionInst,
                message="error while processing the hash value of the record",
                additionalText=record)

            operation = None
            raise ErrorHashProcesing("".join(hashError))



def validateArguments(verb, kw):
    validate(getattr(SwissbibValidationSpec, verb), kw)



class ReadError(ErrorBase):
    def __init__(self,errorMesage):
        self.swissbibMessage = errorMesage
        ErrorBase.__init__(self)
    def __str__(self):

        #die Liste enthaelt nicht nur strings sondern auch ganze Exceptionobjekte.
        #diese Objekte muessen toString Methode (Java) durchlaufen- Python hat sicherlich noch eine schoenere Methode....
        if isinstance(self.swissbibMessage,list):
            tempList = []
            for element in self.swissbibMessage[:]:
                tempList.append(str(element))

            return "".join(tempList)
        else:
            return self.swissbibMessage




class ErrorHashProcesing(ErrorBase):
    def __init__(self,errorMesage):
        self.swissbibMessage = errorMesage
        ErrorBase.__init__(self)
    def __str__(self):

        if isinstance(self.swissbibMessage,list):
            tempList = []
            for element in self.swissbibMessage[:]:
                tempList.append(str(element))

            return "".join(tempList)
        else:
            return self.swissbibMessage




class ErrorMongoProcessing(ErrorBase):
    def __init__(self,errorMesage):
        self.swissbibMessage = errorMesage
        ErrorBase.__init__(self)
    def __str__(self):

        if isinstance(self.swissbibMessage,list):
            tempList = []
            for element in self.swissbibMessage[:]:
                tempList.append(str(element))

            return "".join(tempList)
        else:
            return self.swissbibMessage


class SwissBibMetaDataRegistry(MetadataRegistry):
    #def __init__(self,harvestingConfigs,mongoWrapper,resultCollector):
    def __init__(self):
        MetadataRegistry.__init__(self)
        #self.configs = context.getConfiguration()
        #self.mongoWrapper = context.getMongoWrapper()
        #self.resultCollector = context.getResultCollector()
        #self.context = context

    #def getMongoDBWrapper(self):
    #    return self.mongoWrapper

    #def getHarvestingConfigs(self):
    #    return self.configs

    #def getResultCollector(self):
    #    return self.resultCollector

    #def getContext(self):
    #    return self.context





class SwissbibValidationSpec(ValidationSpec):


    #rero verlangt einen zusaetzlichen Parameter source=uc
    #im regulaeren pyoai client ist dieser parameter jedoch nicht zugelassen
    #deswegen muss die Spezifikation fuer ListRecords ueberschrieben werden
    ListRecords = {
        'from_':'optional',
        'until_':'optional',
        'set':'optional',
        'metadataPrefix':'required',
        'source':'optional',
        'resumptionToken':'exclusive'
        }




class ResultCollector:
    def __init__(self):

        self.recordsDeleted = 0
        self.recordsSkipped = 0
        self.recordsToCBSInserted = 0
        self.recordsToCBSUpdated = 0
        self.recordsToCBSNoSkip = 0
        self.recordsparseError = 0
        self.processedFiles = []
        self.processedRecordsNoFurtherDetails = 0
        self.collectedArchiveFiles = {}


        self.harvestingParameter = None
        self.WrittenToFile = False
        self.WrittenToMongo = False

    def getRecordsDeleted(self):
        return self.recordsDeleted

    def setRecordsDeleted(self,numerRecordsdeleted):
        self.recordsDeleted = numerRecordsdeleted

    def addRecordsDeleted(self,numerRecordsdeleted):
        self.recordsDeleted += numerRecordsdeleted

    def setWrittenToFile(self,value):
        self.WrittenToFile = value

    def getWrittenToFile(self):
        return self.WrittenToFile

    def setWrittenToMongo(self,value):
        self.WrittenToMongo = value

    def getWrittenToMongo(self):
        return self.WrittenToMongo

    def getRecordsSkipped(self):
        return self.recordsSkipped

    def setRecordsSkipped(self,numerRecordsskipped):
        self.recordsSkipped = numerRecordsskipped


    def getHarvestingParameter(self):
        return self.harvestingParameter

    def setHarvestingParameter(self,harvestingParams):
        self.harvestingParameter = harvestingParams

    def getNumberAllProcessedRecords(self):
        return self.getRecordsDeleted() + self.getRecordsSkipped() + self.getRecordsparseError() + self.getRecordsToCBSInserted() + self.getRecordsToCBSUpdated()

    def addRecordsSkipped(self,numerRecordsskipped):
        self.recordsSkipped += numerRecordsskipped


    def getRecordsToCBSInserted(self):
        return self.recordsToCBSInserted

    def getRecordsToCBSUpdated(self):
        return self.recordsToCBSUpdated


    def getRecordsToCBSNoSkip(self):
        return self.recordsToCBSNoSkip


    def setRecordsToCBSUpdated(self,numerRecordsToCBSUpdated):
        self.recordsToCBSUpdated = numerRecordsToCBSUpdated

    def setRecordsToCBSInserted(self,numerRecordsToCBS):
        self.recordsToCBSInserted = numerRecordsToCBS

    def addRecordsToCBSNoSkip(self,numerRecordsToCBSNoSkip):
        self.recordsToCBSNoSkip += numerRecordsToCBSNoSkip


    def addRecordsToCBSInserted(self,numerRecordsToCBSInserted):
        self.recordsToCBSInserted += numerRecordsToCBSInserted

    def addRecordsToCBSUpdated(self,numerRecordsToCBSUpdated):
        self.recordsToCBSUpdated += numerRecordsToCBSUpdated

    def getRecordsparseError(self):
        return self.recordsparseError

    def setRecordsparseError(self,numerRecordsParseError):
        self.recordsparseError = numerRecordsParseError

    def addRecordsparseError(self,numerRecordsParseError):
        self.recordsparseError += numerRecordsParseError


    def addProcessedFile(self,filename):
        self.processedFiles.append(filename)

    def getProcessedFile(self):
        return self.processedFiles

    def setIncrementProcessedRecordNoFurtherDetails(self):
        self.processedRecordsNoFurtherDetails += 1

    def getIncrementProcessedRecordNoFurtherDetails(self):
        return self.processedRecordsNoFurtherDetails

    def getCollectedArchiveFiles(self):
        return self.collectedArchiveFiles


    def setCollectedArchiveFiles(self,fileName, path):
        self.collectedArchiveFiles[fileName] = path



class AdministrationOperation:

    def moveProcessedContentFile(self,configsHarvesting):

        os.chdir(configsHarvesting.getDumpDir())
        os.system("mv " + configsHarvesting.getSummaryContentFile() + " " + configsHarvesting.getArchiveDir())
        tCommand = "gzip -9 " + configsHarvesting.getArchiveDir() + os.sep + configsHarvesting.getSummaryContentFile()
        os.system(tCommand)

        os.chdir(configsHarvesting.getResultDir())
        tCommand = "ln -s " + configsHarvesting.getArchiveDir() + os.sep +\
                   configsHarvesting.getSummaryContentFile() + ".gz " +\
                   configsHarvesting.getSummaryContentFile() + ".gz"
        os.system(tCommand)

        if os.path.isdir(configsHarvesting.getDumpDir()):
            os.system("rm -r " + configsHarvesting.getDumpDir())

    def setAndWriteConfigAfterError(self, configsHarvesting, baseNameConfFile):
        configsHarvesting.setActionFinished("no")
        configsHarvesting.setStoppageTime(str(datetime.now()))
        newConf = open(configsHarvesting.getConfdir() + os.sep +  baseNameConfFile,"w")
        newConf.write(configsHarvesting.getXMLasString())
        newConf.close()


    def writeLogAfterError(self, configsHarvesting = None, resultCollector= None, message= None):

        if not configsHarvesting is None:
            errorLog = open(configsHarvesting.getProcessLogDir() + "/" + configsHarvesting.getProcessLogFile(),"a")
            errorLog.write(message)

            if   not resultCollector is None and  not resultCollector.getHarvestingParameter() is None:
                usedOAIParameters = '\n'.join(['%s:: %s' % (key, value) for (key, value) in resultCollector.getHarvestingParameter().items()])
                errorLog.write(usedOAIParameters)

            errorLog.close()
        else:
            print "harvesting configuration is None while writing to logfile -> redirect error message to stdout\n"
            print message


    def writeErrorLogHarvesting(self, configsHarvesting = None, resultCollector= None, message= None):

        if not configsHarvesting is None:
            errorLog = open(configsHarvesting.getErrorLogDir() + "/" + configsHarvesting.getErrorLogFile(),"a")
            errorLog.write(message)

            if   not resultCollector is None and  not resultCollector.getHarvestingParameter() is None:
                usedOAIParameters = '\n'.join(['%s:: %s' % (key, value) for (key, value) in resultCollector.getHarvestingParameter().items()])
                errorLog.write(usedOAIParameters)

            errorLog.close()
        else:
            print "harvesting configuration is None while writing to logfile -> redirect error message to stdout\n"
            print message




    def writeNebisLogAfterError(self, configs, message):

        if not configs is None:
            errorLog = open(configs.getErrorLogDir() + "/" + configs.getErrorLogFile(),"a")
            errorLog.write(message)
            errorLog.close()
        else:
            print "harvesting configuration is None while writing to logfile -> redirect error message to stdout\n"
            print message

    def writeLogAfterError(self, message, context=None, exceptionType=None):

        if not context is None and context.getConfiguration() is not None:
            errorLog = open(context.getConfiguration().getErrorLogDir() + "/" + context.getConfiguration().getErrorLogFile(),"a")
            if exceptionType is not None:
                errorLog.write(str(exceptionType))
            errorLog.write(message)
            errorLog.close()
        else:
            print "harvesting configuration is None while writing to logfile -> redirect error message to stdout\n"
            print message




    def formatException(self,exceptionType = None, message = "", additionalText = ""):

        if not exceptionType is None:

            errMess = ["\n\n" + '-'*60 + "\n",str(datetime.now()) + "\n\n",
                       message + "\n",str(exceptionType) + "\n" + additionalText  +"\n" + '-'*60 + "\n"]
        else:
            errMess = ["\n\n" + '-'*60 + "\n",str(datetime.now()) + "\n\n",
                       message + "\n"," in swissbibUtilties.formatException -> no ExceptionType was passed" + "\n" + additionalText  +"\n" + '-'*60 + "\n"]

        return  errMess


    def getTestRecord(self):


        f = open("/home/swissbib/swissbib/code_checkout_svn/tools/python/oaiclient/notizen/example.rero.error.xml","r")
        content = f.read()
        f.close()
        return content



class MongoHostDefinition:

    def __init__(self,element):

        self.collections = {}

        self.hostname = element.attrib["name"]

        for child in element:
            if child.tag == "mongoConnection":
                self.mongoConnection = child.text

            elif child.tag == "mongoDB":
                self.mongoDB = child.text
            elif child.tag == "mongoCollections":
                for collectionChilds in child:
                    if collectionChilds.tag == "mongoCollection":
                        self.collections[collectionChilds.attrib["name"]] = collectionChilds.text

    def getCollections(self):
        return self.collections


    def getDB(self):
        return self.mongoDB


    def getConnection(self):
        return self.mongoConnection

    def getName(self):
        return self.hostname


class ProcessSingleRecord():

    def __init__(self,record, mongoWrapper,configs,collector,recordList,skippedRecordList,logSkippedRecords = True):

        self.record = record
        self.mongoWrapper = mongoWrapper
        self.configs = configs
        self.collector = collector
        self.recordList = recordList
        self.skippedRecordList = skippedRecordList
        self.logSkippedRecords = logSkippedRecords
        self.hashType = None

        self.utilities = SwissbibUtilities()


    #diese Methode ist obsolet
    def substituteCharacters(self):
        substituteChars = self.configs.getSubstituteCharacters()
        if not substituteChars is None:
            self.record = re.sub(substituteChars," ",self.record)
        return self.record

    def parseWellFormed(self):

        try:
            ParserCreate().Parse(self.record)

        except ExpatError as expatInst:


            self.collector.addRecordsparseError(1)
            operation = AdministrationOperation()
            errMess = operation.formatException(exceptionType=expatInst,
                message="error validating single record",
                additionalText=self.record)

            operation.writeErrorLogHarvesting( configsHarvesting=self.configs, resultCollector=None, message= "".join(errMess))
            operation = None
            raise expatInst


    def hashHandling(self):

        hashContent = self.createHashType()
        #hashContent = self.createHashType(harvestingConfigs,singleRecord)


        try:
            mongoStatus = self.mongoWrapper.processRecord(hashContent,self.configs)
            if mongoStatus is None:
                docid = "(" + self.configs.getNetworkPrefix() + ")" + hashContent.getDocid()
                mongoError = ["\n\n" + '-'*60 + "\n","error while processing record against MongoDB\n",
                              "return status in None which is not possible\n",
                              "docid: ", docid,
                              str(datetime.now()) + "\n\n",
                              self.record + "\n\n"]
                raise ErrorMongoProcessing(mongoError)
            elif mongoStatus == "writeToFileInserted":
                #recordsToCBSInserted += 1
                self.collector.addRecordsToCBSInserted(1)
                self.appendToStorage(self.record)
                #self.recordList.append(self.record)
                self.collector.setWrittenToMongo(True)
            elif mongoStatus == "writeToFileUpdated":
                #recordsToCBSUpdated += 1
                self.collector.addRecordsToCBSUpdated(1)

                self.appendToStorage(self.record)
                #self.recordList.append(self.record)
                self.collector.setWrittenToMongo(True)
            elif mongoStatus == "skip":
                #setWrittenToMongo=true not necessary because there is no change - only hint that a record is skipped

                #recordsSkipped += 1
                self.collector.addRecordsSkipped(1)
                self.appendToSkippedStorage(self.record)


        except ErrorMongoProcessing as mongoError:
            raise mongoError


    def getDocId(self):
        idValue = None

        #if self.hashType is None:
        sysPattern = self.configs.getOaiIdentifierSysNumber()
        sysPatternP =  re.compile(sysPattern,re.UNICODE | re.DOTALL | re.IGNORECASE)
        sysPatternT = sysPatternP.search(self.record)
        if not sysPatternT:
            #todo message
            print "Fehler"
        else:
            idValue = "(" + self.configs.getNetworkPrefix() + ")" + sysPatternT.group(1)
        #else:
        #    id =  "(" + self.configs.getNetworkPrefix() + ")" + self.hashType.getDocid(),

        return idValue


    def createHashType(self):
        hashType = globals()[self.configs.getHashRenderer()](self.configs)
        try:
            #Python 3
            #xml.sax.parseString(bytes(tRecord,"UTF-8"), scrapContent)
            xml.sax.parseString(self.record, hashType)
            self.hashType = hashType
            return hashType
        except Exception as exceptionInst :
            operation = AdministrationOperation()
            hashError = operation.formatException(exceptionType=exceptionInst,
                message="error while processing the hash value of the record",
                additionalText=self.record)
            self.hashType = None
            operation = None
            raise ErrorHashProcesing("".join(hashError))

    def appendToStorage(self,content):
        self.recordList.append(content)

    def appendToSkippedStorage(self,content):
        if self.logSkippedRecords:
            self.skippedRecordList.append("".join (["\n",content,"\n"]))



class ProcessSingleNebisRecord(ProcessSingleRecord):

    def __init__(self,record, nebisHeader, mongoWrapper,configs,collector,wholeContentFile,logSkippedRecords = True):

        ProcessSingleRecord.__init__(self,record=record,
                                            mongoWrapper=mongoWrapper,
                                            configs=configs,
                                            collector=collector,
                                            recordList=None,
                                            skippedRecordList=None,
                                            logSkippedRecords=logSkippedRecords)

        self.wholeContentFile = wholeContentFile
        self.nebisHeader = nebisHeader


    def appendToStorage(self,content):
        tList = ['\n',self.nebisHeader,self.record,self.utilities.getNEBISFooterText()]
        self.wholeContentFile.writelines(tList)
        self.collector.setWrittenToMongo(True)


    def appendToSkippedStorage(self,content):
        if self.logSkippedRecords:

            if not os.path.isdir(self.configs.getDumpDirSkipped()):
                os.system("mkdir -p " + self.configs.getDumpDirSkipped())


            #getSummaryContentFileSkipped
            tList = ['\n',self.nebisHeader,self.record,self.utilities.getNEBISFooterText(),"\n"]
            skippedRecordsLog = open(self.configs.getDumpDirSkipped() + os.sep + self.configs.getSummaryContentFileSkipped(),"a")
            #skippedRecordsLog.write(contentSingleFile)
            skippedRecordsLog.write("".join(tList))
            skippedRecordsLog.close()



    def getDocId(self):
        idValue = None

        #if self.hashType is None:
        sysPattern = self.configs.getOaiIdentifierSysNumber()
        sysPatternP =  re.compile(sysPattern,re.UNICODE | re.DOTALL | re.IGNORECASE)
        #bei Nebis ist der OAI identifier nicht innerhalb des records
        sysPatternT = sysPatternP.search(self.record)
        if not sysPatternT:
            #todo message
            print "Fehler"
        else:
            idValue = "(" + self.configs.getNetworkPrefix() + ")" + sysPatternT.group(1)
            #else:
        #    id =  "(" + self.configs.getNetworkPrefix() + ")" + self.hashType.getDocid(),

        return idValue
