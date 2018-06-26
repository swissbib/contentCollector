
from pymongo import MongoClient
from datetime import datetime
import sys
import hashlib
import zlib
import os
import re
from bson.binary import Binary
#from pymongo.binary import Binary

import time


from swissbibUtilities import ErrorMongoProcessing


__author__ = 'swissbib'




class MongoDBHarvestingWrapper():

    def __init__(self,applicationContext=None):

        self.dbConnections = {}
        self.appContext = applicationContext

        for key in self.appContext.getConfiguration().getMongoHosts():
            host = self.appContext.getConfiguration().getMongoHosts() [key]
            sConnection = host.getConnection()
            dbConnection = {}
            client = MongoClient(sConnection)
            #connection = Connection(sConnection)
            dbConnection["connection"] = client
            #dbConnection["dbname"] = host.getDB()
            dbConnection["db"] = client[host.getDB()]

            collections = {}
            for key in host.getCollections():
                name = host.getCollections()[key]
                if not name is None:
                    collections[key] = dbConnection["db"][name]

            dbConnection["collections"] = collections
            self.dbConnections[host.getName()] = dbConnection





        #self.host = harvestingConfig.getMongoHost()
        #self.port = harvestingConfig.getMongoPort()
        #self.dbName = harvestingConfig.getMongoDB()
        #self.collectionName = harvestingConfig.getMongoCollection()
        #there is a bug in pymongo related to MongoDB >= 2.1.x
        #therefor we use so far the admin user
        #https://jira.mongodb.org/browse/PYTHON-371
        #I have to practice at first how to update python libraries
        #self.connection = Connection(self.host)
        #info = self.connection.server_info()
        #{u'ok': 1.0,
        # u'sysInfo': u'Linux ip-10-2-29-40 2.6.21.7-2.ec2.v1.2.fc8xen #1 SMP Fri Nov 20 17:48:28 EST 2009 x86_64 BOOST_LIB_VERSION=1_49',
        # u'version': u'2.2.1', u'versionArray': [2, 2, 1, 0],
        # u'debug': False,
        # u'maxBsonObjectSize': 16777216,
        # u'bits': 64,
        # u'gitVersion': u'd6764bf8dfe0685521b8bc7b98fd1fab8cfeb5ae'}
        #self.db = self.connection[self.dbName]

        self.collectedIds = {}

        #if not self.collectionName is None:
        #    self.collectionRecords = self.db[self.collectionName]


    def getDBConnections(self):
        return self.dbConnections


    def processRecord(self,hashType,configuration):

        tCollection = self.dbConnections["harvesting"]["collections"]["repository"]

        ##otherwise varibale docId might not be defined in exception
        docId = ""
        try:

            docId = "(" + configuration.getNetworkPrefix() + ")" + hashType.getDocid()
            #tobehashed = hashType.getMarccontent()

            #attention only name hash shadows an internal name
            hashValue = hashlib.md5(hashType.getMarccontent().encode("utf8")).hexdigest()

            mongoRecord = tCollection.find_one({"_id": docId})
            #mongoRecord = self.collectionRecords.find_one({"_id": docId})

            status = None

            #todo: remove hashcontent after testing!

            if not mongoRecord:


                newrecord = {"_id":docId,
                             "hash":hashValue,
                             "lastdate":str(datetime.now())[:10],
                             "laststatus":"insertedToCBS",
                             "sizeHistory": 1,
                             "history" : [
                                     {
                                     "datum": datetime.now(),
                                     "status": "insertedToCBS",
                                     "hash" : hashValue
                                     #"hashcontent" : hashType.getMarccontent()
                                 }
                             ]
                }
                tCollection.insert(newrecord)
                #self.collectionRecords.insert(newrecord)
                status = "writeToFileInserted"

            elif mongoRecord and mongoRecord["hash"] == hashValue:

                newHistoryItem ={
                    "datum":datetime.now(),
                    "status": "skipped",
                    "hash":hashValue
                    #"hashcontent" : hashType.getMarccontent()

                }

                mongoRecord["history"].append(newHistoryItem)
                mongoRecord["sizeHistory"] = len(mongoRecord["history"])
                mongoRecord["lastdate"] = str(datetime.now())[:10]
                mongoRecord["laststatus"] = "skipped"
                #tCollection.save(mongoRecord,safe=True)
                tCollection.replace_one({"_id": docId}, mongoRecord)
                #self.db[self.collectionName].save(mongoRecord)
                #self.collectionRecords.save(mongoRecord,safe=True)

                status = "skip"

            elif mongoRecord and mongoRecord["hash"] != hashValue:

                newHistoryItem ={
                    "datum":datetime.now(),
                    "status": "updatedToCBS",
                    "hash":hashValue
                    #"hashcontent" : hashType.getMarccontent()

                }

                mongoRecord["history"].append(newHistoryItem)
                mongoRecord["sizeHistory"] = len(mongoRecord["history"])
                mongoRecord["lastdate"] = str(datetime.now())[:10]
                mongoRecord["laststatus"] = "updatedToCBS"
                mongoRecord["hash"] = hashValue
                #self.db[self.collectionName].save(mongoRecord)
                #tCollection.save(mongoRecord,safe=True)
                tCollection.replace_one({"_id": docId}, mongoRecord)
                #self.collectionRecords.save(mongoRecord,safe=True)

                status = "writeToFileUpdated"

            return  status
        except:
            message = ["error while processing reord against Mongo\n",
                       "docid: ", docId,
                       "SytemInfo: ", sys.exc_info()]
            raise ErrorMongoProcessing(message)



    def closeResources(self):

        for connectionKey in self.dbConnections:
            if not self.dbConnections[connectionKey] is None:
                self.dbConnections[connectionKey]["connection"].close()


    def storeResultOfProcessing(self,resultCollector,harvestingConfig):

        tCollection = self.dbConnections["harvesting"]["collections"]["summary"]

        if resultCollector.getHarvestingParameter() is None:

            newSummary = {
                         "datum":datetime.now(),
                         "repository":harvestingConfig.getNetworkPrefix(),
                         "skipped":resultCollector.getRecordsSkipped(),
                         "tocbs" :resultCollector.getRecordsToCBS(),
                         "deleted":resultCollector.getRecordsDeleted(),
                         "parseError":resultCollector.getRecordsparseError()
                        }
        else:

            newSummary = {
                "datumExact":datetime.now(),
                "datum":datetime.now().strftime("%Y-%m-%d"),
                "repository":harvestingConfig.getNetworkPrefix(),
                "skipped":resultCollector.getRecordsSkipped(),
                "tocbsInserted" :resultCollector.getRecordsToCBSInserted(),
                "tocbsUpdated" :resultCollector.getRecordsToCBSUpdated(),
                "deleted":resultCollector.getRecordsDeleted(),
                "parseError":resultCollector.getRecordsparseError(),
                "oaiParameter":resultCollector.getHarvestingParameter()
            }

        tCollection.insert(newSummary)


    def storeResultOfNebisProcessing(self,resultCollector,harvestingConfig):

        filenames = ""
        #for filename in resultCollector.getProcessedFile():
        #    filenames +

        tCollection = self.dbConnections["harvesting"]["collections"]["summary"]

        newSummary = {
            "datum":datetime.now(),
            "repository":harvestingConfig.getNetworkPrefix(),
            "skipped":resultCollector.getRecordsSkipped(),
            "tocbs inserted" :resultCollector.getRecordsToCBSInserted(),
            "tocbs updated" :resultCollector.getRecordsToCBSUpdated(),
            "deleted":resultCollector.getRecordsDeleted(),
            "parseError":resultCollector.getRecordsparseError(),
            "processedFiles" : "#".join(resultCollector.getProcessedFile())
        }
        tCollection.insert(newSummary)




class MongoDBHarvestingWrapperAdmin(MongoDBHarvestingWrapper):
    def __init__(self,applicationContext=None):
        MongoDBHarvestingWrapper.__init__(self,applicationContext=applicationContext)

        #Todo: der Wrapper sollte eine Refernz auf die configs behalten
        #und nicht nur einfach Werte lesen und dann die iNstanz nicht weiter beachten
        #Refactoring!

        self.backupItemOpen = "<backupitem>"
        self.backupItemClose = "</backupitem>"
        self.idTagItemOpen = "<recordId>"
        self.idTagItemClose = "</recordId>"
        self.statusTagItemOpen = "<recordStatus>"
        self.statusTagItemClose = "</recordStatus>"
        self.dateTagItemOpen = "<recordDate>"
        self.dateTagItemClose = "</recordDate>"
        self.metadataTagItemOpen = "<recordMetadata>"
        self.metadataTagItemClose = "</recordMetadata>"

        self.ptagIdItem = re.compile("<recordId>(.*?)</recordId>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.ptagStatusItem = re.compile("<recordStatus>(.*?)</recordStatus>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.ptagDateItem = re.compile("<recordDate>(.*?)</recordDate>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.ptagMetadataItem = re.compile("<recordMetadata>(.*?)</recordMetadata>",re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.sourceOAIExtensions = {}
        self.sourceMappings = {}
        self.userDateStamp = None
        self.pRecordUserDatestamp = re.compile("(.*?<datestamp>).*?(</datestamp>.*)",re.UNICODE | re.DOTALL | re.IGNORECASE)



    def readRecordsWithTimeStamp(self, startDate=None, endDate=None, outDir=None, fileSize=None, countToRead = None):

        sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]
        regExpdateTimeStamp = re.compile('<header>.*?<datestamp>(.*?)</datestamp>.*?</header>',re.UNICODE | re.DOTALL |
                                         re.IGNORECASE)


        if not startDate is None and not endDate is None:
            tStartDate = datetime.strptime(startDate, "%Y-%m-%dT%H:%M:%SZ")
            tEndDate = datetime.strptime(endDate, "%Y-%m-%dT%H:%M:%SZ")

            clause = {
                '$and': [{'recordTimestamp': {'$exists': True}},
                         {'recordTimestamp': {'$ne': None}},
                         {'recordTimestamp': {'$gte': tStartDate}},
                         {'recordTimestamp': {'$lte': tEndDate}}]
            }

        elif not startDate is None:
            tStartDate = datetime.strptime(startDate, "%Y-%m-%dT%H:%M:%SZ")
            clause = {
                '$and': [{'recordTimestamp': {'$exists': True}},
                         {'recordTimestamp': {'$ne': None}},
                         {'recordTimestamp': {'$gte': tStartDate}}]
            }
        elif not endDate is None:
            tEndDate = datetime.strptime(endDate, "%Y-%m-%dT%H:%M:%SZ")
            clause = {
                '$and': [{'recordTimestamp': {'$exists': True}},
                         {'recordTimestamp': {'$ne': None}},
                         {'recordTimestamp': {'$lte': tEndDate}}]
            }
        else:
            clause = None

        lastTimeStamp = "not defined so far"
        if not clause is None:
            outDir = self.checkAndCreateOutDir(outDir)
            outfile = self.defineOutPutFile(outDir)
            fileToWrite = open(outfile, "w")
            self.writeHeader(fileToWrite)

            #at the moment ascending sort order is the only possibility

            print "".join(["number of total records in the current pipe: ", str(sourceCollection.find(clause).count()),"\n"])
            if not countToRead is None:
                print "number of max. records being processed: " + str(countToRead)

            result = sourceCollection.find(clause).sort([('recordTimestamp', +1)])
            numberOfRecordsAlreadyRead = 0
            for document in result:
                numberOfRecordsAlreadyRead += 1
                #lese den letzten timestamp

                if not countToRead is None and numberOfRecordsAlreadyRead > int(countToRead)  :
                    break
                r = zlib.decompress(document["record"])

                currentRecordTimestamp = regExpdateTimeStamp.search(r)
                if not currentRecordTimestamp:
                    #severe error, must not happen because of pre conditions
                    self.writeFooter(fileToWrite)
                    fileToWrite.close()
                    raise Exception("".join([ "record: ", r, " doesn't contain a timestamp which shouldn't be possible"] ))
                else:
                    lastTimeStamp = currentRecordTimestamp.group(1)

                fileToWrite.write(r + "\n\n")

                fileToWrite.flush()

                if (not fileSize is None):

                    statinfo = os.stat(outfile)
                    size = statinfo.st_size

                    forCompare = int(fileSize) * 1000000

                    if size > forCompare :
                        self.writeFooter(fileToWrite)
                        fileToWrite.close()
                        outfile = self.defineOutPutFile(outDir)
                        fileToWrite = open(outfile, "w")
                        self.writeHeader(fileToWrite)

            if not fileToWrite is None:
                self.writeFooter(fileToWrite)
                fileToWrite.close()


        fileLastTimestamp =  open(os.getcwd() + os.sep + "lastTimestamp.txt","w")
        fileLastTimestamp.write(lastTimeStamp)
        fileLastTimestamp.flush()
        fileLastTimestamp.close()


    def readRecords(self,rId=None,countToRead=None,fileSize=None,outDir=None,condition=None,
                    inputFile=None,userDatestamp=None, docRecordField=None):

        self.userDateStamp = userDatestamp

        if not inputFile is None:

            self.prepareMappings()

            fileToRead = open(inputFile,"r")
            outDir = self.checkAndCreateOutDir(outDir)
            outfile = self.defineOutPutFile(outDir)

            fileToWrite = open(outfile,"w")
            self.writeHeader(fileToWrite)

            pRecordPrefix = re.compile("(\((.*?)\))(.*)",re.UNICODE | re.DOTALL | re.IGNORECASE)


            for line in fileToRead:

                nCRline = line[:-1]


                spRecordPrefix = pRecordPrefix.search(nCRline)
                if spRecordPrefix:

                    try:

                        network = spRecordPrefix.group(2)
                        firstPart = spRecordPrefix.group(1)
                        secondPart = spRecordPrefix.group(3)
                        collection = self.sourceMappings[network]
                        dbConnection = self.getDBConnections()["nativeSources"]['db']
                        sourceCollection = dbConnection[collection]

                        searchedID = firstPart + self.sourceOAIExtensions[network] + secondPart

                        document = sourceCollection.find_one({"_id": searchedID})
                        if document:
                            r = document["record"]
                            #print  zlib.decompress(r)
                            fileToWrite.write(self.setCustomDatestamp(zlib.decompress(r)) + "\n\n")


                            fileToWrite.flush()

                            if (not fileSize is None):

                                statinfo = os.stat(outfile)
                                size = statinfo.st_size

                                forCompare = int(fileSize) * 1000000

                                if (size > forCompare):
                                    self.writeFooter(fileToWrite)
                                    fileToWrite.close()
                                    outfile = self.defineOutPutFile(outDir)
                                    fileToWrite = None
                                    fileToWrite = open(outfile,"w")
                                    self.writeHeader(fileToWrite)





                        else:
                            print >> sys.stderr,  "".join(["ID: ", nCRline,"\n" ," transformed to: ", searchedID, " not found"])


                    except Exception as pythonBaseException:
                        print >> sys.stderr,  "".join(["Exception: ", str(pythonBaseException), "\n" "ID: ", nCRline])


            if (fileToWrite is not None):
                self.writeFooter(fileToWrite)
                fileToWrite.close()




        else:




            sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


            if (not rId is None):

                print "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                print "<" + self.appContext.getConfiguration().getRoottag() + ">"
                document = sourceCollection.find_one({"_id": rId})
                if document:

                    docFieldName = docRecordField is not None and docRecordField or "record"
                    r = document[docFieldName]
                    print  self.setCustomDatestamp(zlib.decompress(r))
                print "</" + self.appContext.getConfiguration().getRoottag() + ">"

            elif (fileSize is None and  outDir is not None):

                outDir = self.checkAndCreateOutDir(outDir)
                outfile = self.defineOutPutFile(outDir)
                fileToWrite = open(outfile,"w")
                self.writeHeader(fileToWrite)

                if condition is None:
                    result = sourceCollection.find()
                else:
                    result = sourceCollection.find(self.tokenizeCondition(condition))
                alreadyRead = 0

                for document in result:
                    if countToRead is not None and alreadyRead >= int(countToRead):
                        break
                    docFieldName = docRecordField is not None and docRecordField or "record"
                    r = document[docFieldName]

                    #r = document["record"]
                    fileToWrite.write(self.setCustomDatestamp(zlib.decompress(r) + "\n"))

                    alreadyRead +=1
                self.writeFooter(fileToWrite)
                fileToWrite.flush()
                fileToWrite.close()

            else:

                outDir = self.checkAndCreateOutDir(outDir)
                outfile = self.defineOutPutFile(outDir)
                fileToWrite = open(outfile,"w")
                self.writeHeader(fileToWrite)

                if condition is None:
                    result = sourceCollection.find()
                else:
                    result = sourceCollection.find(self.tokenizeCondition(condition))
                alreadyRead = 0
                for document in result:
                    if countToRead is not None and alreadyRead >= int(countToRead):
                        break
                    docFieldName = docRecordField is not None and docRecordField or "record"
                    r = document[docFieldName]

                    #wholeRecordUnzipped = zlib.decompress(r)
                    #we don't want to have any linebreaks because it's easier to work with
                    #rNoBreaks =  "".join(wholeRecordUnzipped.splitlines())
                    #fileToWrite.write("".join(zlib.decompress(r).splitlines()) + "\n")
                    fileToWrite.write(self.setCustomDatestamp(zlib.decompress(r) + "\n"))


                    alreadyRead +=1
                    fileToWrite.flush()
                    statinfo = os.stat(outfile)
                    size = statinfo.st_size

                    forCompare = int(fileSize) * 1000000

                    if (size > forCompare):
                        self.writeFooter(fileToWrite)
                        fileToWrite.flush()
                        fileToWrite.close()
                        outfile = self.defineOutPutFile(outDir)
                        fileToWrite = None
                        fileToWrite = open(outfile,"w")
                        self.writeHeader(fileToWrite)



                if (fileToWrite is not None):
                    self.writeFooter(fileToWrite)
                    fileToWrite.flush()
                    fileToWrite.close()




    def tokenizeCondition(self,condition):

        pTokenCondition = re.compile(':',re.UNICODE | re.DOTALL | re.IGNORECASE)

        searchColon =  pTokenCondition.search(condition)
        if searchColon:
            splitted = condition.split(":")
            dictCondition = {splitted[0] : splitted[1]}
        else:
            #we assume a date search with the operators $gt|$lt
            splitted = condition.split("#")
            if (len(splitted) == 2):
                dictCondition = {'datum': {splitted[0] : splitted[1]}}
            elif (len(splitted) == 3):
                dictCondition = {
                    '$and': [
                        {splitted[0]: {splitted[1]: int(splitted[2])}}, # for example 'year#$lte#2015'
                        {'includedInNationalLicences': { '$not': { '$eq' : 'no' }} } #does not include articles which are not part of National Licences
                    ]
                }
            else:
                dictCondition = {}


        return dictCondition



    def writeBackupRecords(self,fileSize=None,outDir=None):

        sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

        self.checkAndCreateOutDir(outDir)
        outfile = self.defineOutPutFile(outDir)


        outfile = self.defineOutPutFile(outDir)
        fileToWrite = open(outfile,"w")

        self.writeHeader(fileToWrite)

        result = sourceCollection.find()
        for document in result:

            #decomp = zlib.decompress(document["record"])
            _recordToWrite = [self.backupItemOpen,
                              self.idTagItemOpen,document["_id"].encode('utf-8'),self.idTagItemClose ,
                              self.statusTagItemOpen,document["status"].encode('utf-8'),self.statusTagItemClose,
                              self.metadataTagItemOpen,zlib.decompress(document["record"]),self.metadataTagItemClose,
                              self.dateTagItemOpen,document["datum"].encode('utf-8'), self.dateTagItemClose,
                              self.backupItemClose]
            fileToWrite.write("".join(_recordToWrite) + os.linesep)


            fileToWrite.flush()
            statinfo = os.stat(outfile)
            size = statinfo.st_size

            forCompare = int(fileSize) * 1000000

            if (size > forCompare):
                self.writeFooter(fileToWrite)
                fileToWrite.flush()
                fileToWrite.close()
                outfile = self.defineOutPutFile(outDir)
                fileToWrite = None
                fileToWrite = open(outfile,"w")
                self.writeHeader(fileToWrite)



        if (fileToWrite is not None):
            self.writeFooter(fileToWrite)
            fileToWrite.flush()
            fileToWrite.close()


    def restoreBackupRecords(self,outDir=None):

        self.checkOutDir(outDir)

        sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

        for fname in os.listdir(outDir):

            itemLines = []
            start = False
            for line in open(outDir + os.sep +  fname,"r"):
                if line.find(self.backupItemOpen) != -1:
                    itemLines.append(line)
                    start = True
                elif start == True and line.find(self.backupItemClose) == -1:
                    itemLines.append(line)
                elif start == True and line.find(self.backupItemClose) != -1:
                    itemLines.append(line)



                    _values = self.valuesRestoredRecord("".join(itemLines))
                    mongoRecord = sourceCollection.find_one({"_id": _values["id"]})
                    binary = Binary( zlib.compress(_values["record"],9))
                    if not mongoRecord:
                        newRecord = {"_id":_values["id"],
                                     "datum":_values["date"],
                                     "record":binary,
                                     "status":_values["status"]
                        }

                        sourceCollection.insert(newRecord)
                    else:
                        mongoRecord["record"] = binary
                        mongoRecord["status"] = _values["status"]
                        mongoRecord["datum"] = _values["date"]
                        sourceCollection.replace_one({"_id": _values["id"]}, mongoRecord)
                        #sourceCollection.save(mongoRecord,safe=True)

                    itemLines = []
                    start = False





    def defineOutPutFile(self,outdir):
        prefix = self.appContext.getConfiguration().getNetworkPrefix()
        time.sleep(5)
        outfile = "".join([outdir,os.sep,str(prefix),
                                    "-","export.",
                                    '{:%Y%m%d%H%M%S}'.format(datetime.now()),
                                    ".xml"])

        return outfile

    def checkAndCreateOutDir(self,outdir):
        if not outdir[-1] == os.sep:
            outdir = "".join([outdir,os.sep])

        outdir = "".join([outdir, '{:%Y%m%d%H%M%S}'.format(datetime.now())])

        if not os.path.exists(outdir):
            os.makedirs(outdir)

        return outdir



    def checkOutDir(self,outdir):
        if not os.path.exists(outdir):
            raise Exception("outDir doesn't exist")


    def valuesRestoredRecord(self,structureRestoredRecord):

        _values = {}

        _id = self.ptagIdItem.search(structureRestoredRecord)
        if _id:
            _values ['id']= _id.group(1)
        else:
            raise Exception("restored record doesn't contain an recordID" + os.linesep + structureRestoredRecord)


        _status = self.ptagStatusItem.search(structureRestoredRecord)
        if _status:
            _values ['status']= _status.group(1)
        else:
            raise Exception("restored record doesn't contain status" + os.linesep + structureRestoredRecord)

        _date = self.ptagDateItem.search(structureRestoredRecord)
        if _date:
            _values ['date']= _date.group(1)
        else:
            raise Exception("restored record doesn't contain date field" + os.linesep + structureRestoredRecord)

        _metaData = self.ptagMetadataItem.search(structureRestoredRecord)
        if _metaData:
            _values ['record']= _metaData.group(1)
        else:
            raise Exception("restored record doesn't contain metadata" + os.linesep + structureRestoredRecord)


        return _values


    def writeHeader (self,fileToWrite):
        fileToWrite.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        fileToWrite.write("<" + self.appContext.getConfiguration().getRoottag() + ">\n")
        fileToWrite.flush()


    def writeFooter (self,fileToWrite):
        fileToWrite.write("</" + self.appContext.getConfiguration().getRoottag() + ">\n")
        fileToWrite.flush()


    def prepareMappings(self):

        definitionsPrefixMappings = self.appContext.getConfiguration().getSourcePrefixMapping()
        definitionsSourceOAIExtensions =  self.appContext.getConfiguration().getSourceOAIExtension()

        if definitionsPrefixMappings is None or definitionsSourceOAIExtensions is None:
            raise Exception("please provide sourceOAIExtension and sourcePrefixMapping in configuration file for export of multiple colletions")

        prefixMappings = re.split('##',definitionsPrefixMappings)
        self.sourceMappings = {}
        for mapping in prefixMappings:
            tm = re.split('=',mapping)
            self.sourceMappings[tm[0]] = tm[1]


        oaiExtensions = re.split('##',definitionsSourceOAIExtensions)
        self.sourceOAIExtensions = {}
        for mapping in oaiExtensions:
            tOAI = re.split('=',mapping)
            self.sourceOAIExtensions[tOAI[0]] = tOAI[1]



    def setCustomDatestamp(self,record):

        if (not self.userDateStamp is None):
            sRecord = self.pRecordUserDatestamp.search(record)
            if (sRecord):
                return "".join([sRecord.group(1),self.userDateStamp, sRecord.group(2)])
        else:
            return record





class MongoDBHarvestingWrapperFixRecords(MongoDBHarvestingWrapperAdmin):

    def __init__(self,applicationContext=None):

        self.pReroDeleteRecord = re.compile("(<record>.*?</header>).*",re.UNICODE | re.DOTALL | re.IGNORECASE)
        MongoDBHarvestingWrapper.__init__(self,applicationContext=applicationContext)


    def fixReroDeleteRecord(self):

        sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


        #numberDeleted = sourceCollection.find({"status":"deleted"}).count()
        #numberNewDeleted = sourceCollection.find({"status":"newdeleted"}).count()

        result = sourceCollection.find({"status":"newdeleted"})


        for document in result:
            recordToDeleteCompressed = document["record"]
            docid = document["_id"]
            recordToDelete =  zlib.decompress(recordToDeleteCompressed)

            spReroDeletedRecordsToSubstitutePattern = self.pReroDeleteRecord.search(recordToDelete)
            if spReroDeletedRecordsToSubstitutePattern:
                modifiedRecord= spReroDeletedRecordsToSubstitutePattern.group(1) + "</record>"
                binarymodifiedRecord = Binary( zlib.compress(modifiedRecord,9))
                document["record"] = binarymodifiedRecord
                #attention: save is deprecated - question: is it possible to pass a document object to replace_one method??
                sourceCollection.save(document)
                #sourceCollection.replace_one({"_id": docid}, document)

            else:
                print "record " + recordToDelete + " konnte per regex nicht verarbeitet werden"





        result = sourceCollection.find({"status":"deleted"})

        for document in result:
            recordToDeleteCompressed = document["record"]
            docid = document["_id"]
            recordToDelete =  zlib.decompress(recordToDeleteCompressed)

            spReroDeletedRecordsToSubstitutePattern = self.pReroDeleteRecord.search(recordToDelete)
            if spReroDeletedRecordsToSubstitutePattern:
                modifiedRecord= spReroDeletedRecordsToSubstitutePattern.group(1) + "</record>"
                binarymodifiedRecord = Binary( zlib.compress(modifiedRecord,9))
                document["record"] = binarymodifiedRecord
                #attention: save is deprecated - see comment above
                sourceCollection.save(document)
                # sourceCollection.replace_one({"_id": docid}, document)

            else:
                print "record " + recordToDelete + " konnte per regex nicht verarbeitet werden"



class MongoDBHarvestingWrapperSearch502(MongoDBHarvestingWrapperAdmin):

    def __init__(self,applicationContext=None):
        self.pSearch502 = re.compile("<(marc:)?datafield *?tag=\"502\".*",re.UNICODE | re.DOTALL | re.IGNORECASE)
        MongoDBHarvestingWrapper.__init__(self,applicationContext=applicationContext)



    def read502Records(self,outDir=None,fileSize=None):

        sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

        outDir = self.checkAndCreateOutDir(outDir)
        outfile = self.defineOutPutFile(outDir)

        fileToWrite = open(outfile,"w")
        self.writeHeader(fileToWrite)


        #numberDeleted = sourceCollection.find({"status":"deleted"}).count()
        #numberNewDeleted = sourceCollection.find({"status":"newdeleted"}).count()

        result = sourceCollection.find()


        for document in result:
            recordCompressed = document["record"]
            record =  zlib.decompress(recordCompressed)

            #f = open("/home/swissbib/temp/trash/idsbb502.xml","r")
            #text = f.readlines()
            #f.close()
            #text = "".join(text)
            spSearch502 = self.pSearch502.search(record)

            if spSearch502:

                fileToWrite.write(record + "\n")


                fileToWrite.flush()
                statinfo = os.stat(outfile)
                size = statinfo.st_size

                forCompare = int(fileSize) * 1000000

                if (size > forCompare):
                    self.writeFooter(fileToWrite)
                    fileToWrite.flush()
                    fileToWrite.close()
                    outfile = self.defineOutPutFile(outDir)
                    fileToWrite = None
                    fileToWrite = open(outfile,"w")
                    self.writeHeader(fileToWrite)


        if (fileToWrite is not None):
            self.writeFooter(fileToWrite)
            fileToWrite.close()



class MongoDBHarvestingWrapperSearchDefinedGeneric(MongoDBHarvestingWrapperAdmin):

    def __init__(self,applicationContext=None):
        MongoDBHarvestingWrapper.__init__(self,applicationContext=applicationContext)



    def setRegEx(self,regex = None):

        if not regex is None:
            self.pDefinedRegex = re.compile(regex,re.UNICODE | re.DOTALL | re.IGNORECASE | re.MULTILINE)


    def setdocRecordField(self,docField = None):

        self.docRecordField = docField

    def readMatchingRecords(self,outDir=None,fileSize=None,userDatestamp=None):

        self.userDateStamp = userDatestamp

        if self.pDefinedRegex is None:
            raise  Exception("no Regex defined")


        sourceCollection = self.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

        outDir = self.checkAndCreateOutDir(outDir)
        outfile = self.defineOutPutFile(outDir)

        fileToWrite = open(outfile,"w")
        self.writeHeader(fileToWrite)


        #numberDeleted = sourceCollection.find({"status":"deleted"}).count()
        #numberNewDeleted = sourceCollection.find({"status":"newdeleted"}).count()

        result = sourceCollection.find()


        for document in result:
            if not self.docRecordField is None:
                recordCompressed = document[self.docRecordField]
            else:
                recordCompressed = document["record"]
            record =  zlib.decompress(recordCompressed)

            record1 = ''.join(record.splitlines())

            #f = open("/home/swissbib/temp/trash/idsbb502.xml","r")
            #text = f.readlines()
            #f.close()
            #text = "".join(text)
            spDefinedRegex = self.pDefinedRegex.search(record1)

            if spDefinedRegex:

                fileToWrite.write(self.setCustomDatestamp(record) + "\n")


                fileToWrite.flush()
                statinfo = os.stat(outfile)
                size = statinfo.st_size

                forCompare = int(fileSize) * 1000000

                if (size > forCompare):
                    self.writeFooter(fileToWrite)
                    fileToWrite.flush()
                    fileToWrite.close()
                    outfile = self.defineOutPutFile(outDir)
                    fileToWrite = None
                    fileToWrite = open(outfile,"w")
                    self.writeHeader(fileToWrite)


        if (fileToWrite is not None):
            self.writeFooter(fileToWrite)
            fileToWrite.close()

        os.system("gzip " + outDir + os.sep + "*")


