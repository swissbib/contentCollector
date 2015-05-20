import re
import xml
from xml.parsers.expat import ParserCreate
from pyexpat import ExpatError
from swissbibUtilities import AdministrationOperation

from swissbibUtilities import ErrorHashProcesing, ErrorMongoProcessing
from datetime import datetime
from swissbibHash import HashMarcContent, HashSwissBibMarcContent, HashDcContent, HashReroMarcContent
import os




__author__ = 'swissbib'


class SwissbibPreImportProcessor:

    def __init__(self,context):
        self.context = context
        sysPattern = self.context.getConfiguration().getOaiIdentifierSysNumber()
        self.pRecordId =  re.compile(sysPattern,re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.pDeleted = re.compile('status="deleted',re.UNICODE | re.IGNORECASE)
        self.pHeader = re.compile('<header.*?>.*?</header>',re.UNICODE | re.DOTALL | re.IGNORECASE)

        self.pMetadata = re.compile('<metadata>(.*?)</metadata>',re.UNICODE |  re.DOTALL |re.IGNORECASE)

        self.pMarcRecord = re.compile("(<record>.*?<metadata.*?>).*?(<leader>.*?)</record>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.pNebisDeleteRecord = re.compile("(<record>.*?</header>).*?</metadata>(</record>)",re.UNICODE | re.DOTALL | re.IGNORECASE)


    def prepareDeleteRecord(self,recordToDelete):
        #basically nothing to do with the record to be deleted
        return recordToDelete


    def getRecordId(self,record):
        #raise Exception("couldn't find a record ID in: " + record)

        sysPatternT = self.pRecordId.search(record)
        if not sysPatternT:
            raise Exception("couldn't find a record ID in: " + record)
        else:
            recordID = "(" + self.context.getConfiguration().getNetworkPrefix() + ")" + sysPatternT.group(1)

        return recordID


    def isDeleteRecord(self,record):
        header = self.pHeader.search(record)
        deleted = False
        if header:
            tHeader = header.group(0)
            pD = self.pDeleted.search(tHeader)
            if pD:
                deleted = True

        return deleted


    def parseWellFormed(self,record):

        try:
            #https://mail.python.org/pipermail/python-list/2005-February/337668.html  -> encoding bei Parse
            ParserCreate().Parse(record)

        except ExpatError as expatInst:

            raise expatInst


    def hashHandling(self,record,recordId):

        hashContent = self.createHashType(record)
        #hashContent = self.createHashType(harvestingConfigs,singleRecord)


        try:
            #todo: recordId muss OAI ID verwendet werden und nicht die vom hashtype welche 001 ist
            #todo: append to storage wenn keine Exception geworfen wird
            mongoStatus = self.context.getMongoWrapper().processRecord(hashContent,self.context.getConfiguration())
            if mongoStatus is None:
                docid = "(" + self.context.getConfiguration().getNetworkPrefix() + ")" + hashContent.getDocid()
                mongoError = ["\n\n" + '-'*60 + "\n","error while processing record against MongoDB\n",
                              "return status in None which is not possible\n",
                              "docid: ", recordId,
                              str(datetime.now()) + "\n\n",
                              record + "\n\n"]
                raise ErrorMongoProcessing(mongoError)
            elif mongoStatus == "writeToFileInserted":
                #recordsToCBSInserted += 1
                self.context.getResultCollector().addRecordsToCBSInserted(1)
                #self.appendToStorage(self.record)
                #self.recordList.append(self.record)
                self.context.getResultCollector().setWrittenToMongo(True)
            elif mongoStatus == "writeToFileUpdated":
                #recordsToCBSUpdated += 1
                self.context.getResultCollector().collector.addRecordsToCBSUpdated(1)

                #self.appendToStorage(record)
                #self.recordList.append(self.record)
                self.context.getResultCollector().setWrittenToMongo(True)
            elif mongoStatus == "skip":
                #setWrittenToMongo=true not necessary because there is no change - only hint that a record is skipped

                #recordsSkipped += 1
                self.context.getResultCollector().addRecordsSkipped(1)
                #self.appendToSkippedStorage(self.record)


        except ErrorMongoProcessing as mongoError:
            raise mongoError

    def createHashType(self,record):
        hashType = globals()[self.context.getConfiguration().getHashRenderer()](self.context.getConfiguration())
        try:
            #Python 3
            #xml.sax.parseString(bytes(tRecord,"UTF-8"), scrapContent)
            xml.sax.parseString(record, hashType)
            #self.hashType = hashType
            return hashType
        except Exception as exceptionInst :
            operation = AdministrationOperation()
            hashError = operation.formatException(exceptionType=exceptionInst,
                                                  message="error while processing the hash value of the record",
                                                  additionalText=record)
            #self.hashType = None
            operation = None
            raise ErrorHashProcesing("".join(hashError))


    def getMetaDataOfRecord(self,record):
        metadata = self.pMetadata.search(record)
        if metadata:
            return metadata.group(1)
        else:
            #todo: throw exception
            return ""



    def _processSkipRecord(self,singleRecord):
        raise Exception("no implementation of skipRecord Functionality in base class")

        #former implementation in Nebis
        #if recordDeleted:
            #recordsDeleted += 1
        #    self.context.getResultCollector().addRecordsDeleted(1)
        #    self.context.getWriteContext().writeItem(contentSingleRecord)
            #mark record in hash db as deleted
            #wholeContentFile.write(contentSingleFile)

        #else:

            #exception handling

        #    try:

        #        recordMetadata = self.getMetaDataOfRecord(contentSingleRecord)
        #        self.hashHandling(recordMetadata,recordId)

        #    except:

        #    else:
                #write to file
        #        pass

        #former implementation in OAI client
        #if recordDeleted:
        #    #recordsDeleted += 1
        #    self.context.getResultCollector().addRecordsDeleted(1)
        #    # mark record in hash db as deleted
        #    self.context.getWriteContext().writeItem(contentSingleRecord)
        #    #recordList.append("".join(["\n",contentSingleRecord]))
        #    #self.writeContext.writeItem(contentSingleRecord)

        #else:

        #    #can we do better exception handling
        #    try:

        #        recordMetadata = self.getMetaDataOfRecord(contentSingleRecord)
        #        self.hashHandling(recordMetadata,recordId)

        #    except Exception  as exHandlingHash:
        #        self.context.getWriteContext().writeErrorLog(header=["error in hash processing"],message=[str(exHandlingHash), contentSingleRecord])
        #        continue

        #    else:
        #        self.context.getWriteContext().writeItem(contentSingleRecord)


    def transformRecordNamespace(self,contentSingleRecord):

        trMarcPattern = ""
        prMarcRecord = self.pMarcRecord.search(contentSingleRecord)

        if prMarcRecord:
            #trMarcPattern = prMarcRecord.group(1) + "<marc:record xmlns:marc=\"http://www.loc.gov/MARC21/slim\"  \n xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" \n xsi:schemaLocation=\"http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd\">" + prMarcRecord.group(2) + "</marc:record>" + prMarcRecord.group(3)
            trMarcPattern = prMarcRecord.group(1) + "<marc:record xmlns:marc=\"http://www.loc.gov/MARC21/slim\"  \n xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" \n xsi:schemaLocation=\"http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd\">" + prMarcRecord.group(2) + "</marc:record>" + "</metadata></record>"

            return trMarcPattern
        else:
            raise Exception("transformation of namespace wasn't possible - pattern didn't match")




    def initialize(self):
        if not os.path.isdir(self.context.getConfiguration().getArchiveDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getArchiveDir())

        if not os.path.isdir(self.context.getConfiguration().getResultDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getResultDir())

        if not os.path.isdir(self.context.getConfiguration().getErrorLogDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getErrorLogDir())

        if not os.path.isdir(self.context.getConfiguration().getProcessLogDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getProcessLogDir())



