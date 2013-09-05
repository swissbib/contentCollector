from lxml import etree
from pymongo.connection import Connection
from swissbibUtilities import ErrorMongoProcessing
import sys
import zlib
from pymongo.binary import Binary
from datetime import datetime

from xml.sax.handler import ContentHandler
import xml.sax
import re
import xml.dom.minidom
from Context import ApplicationContext, StoreNativeRecordContext

__author__ = 'swissbib'



class HarvestingTask():

    def __init__(self):
        pass


    def  processRecord(self, taskContext=None):
        pass


    def finalize(self):
        pass
        #are there destructors in python??



class PersistRecordMongo(HarvestingTask):

    def __init__(self):
        HarvestingTask.__init__(self)
        #HarvestingTask.__init__(self,configs)


        #self.hashType = None
        #for child in element:
        #    if child.tag == "persistHost":
        #        self.persistHost = child.text
        #    elif child.tag == "persistPort":
        #        self.persistPort = child.text
        #    elif child.tag == "persistDB":
        #        self.persistDB = child.text
        #    elif child.tag == "persistCollection":
        #        self.persistCollection = child.text

        #self.connection = Connection(self.persistHost)
        #self.db = self.connection[self.persistDB]
        #if not self.persistCollection is None:
        #    self.collectionRecords = self.db[self.persistCollection]



    #def  processRecord(self, record, rid = None ,configs = None, dbWrapper = None ):
    def  processRecord(self,taskContext=None ):
        #todo: search for recordID if None -> use HasType

        #double check isn't necessary as long these plugins are only used by myself
        #if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        isDeleted = taskContext.isDeleted()


        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


            mongoRecord = tCollection.find_one({"_id": rid})

            binary = Binary( zlib.compress(record,9))

            if not mongoRecord:

                #newdeleted are records which were sent from the repository marked as deleted but weren't fetched by swissbib before (so not in the nativeSourcesDB)
                #normally this shouldn't happen but might be possible and a hint to ask for the background
                if isDeleted:
                    taskContext.getResultCollector().addRecordsDeleted(1)
                    status = "newdeleted"
                else:
                    status = "new"
                    taskContext.getResultCollector().addRecordsToCBSInserted(1)


                newRecord = {"_id":rid,
                             "datum":str(datetime.now())[:10],
                             "record":binary,
                             "status":status
                }

                tCollection.insert(newRecord)

            else:
                if isDeleted:
                    status = "deleted"
                    taskContext.getResultCollector().addRecordsDeleted(1)
                else:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)


                mongoRecord["record"] = binary
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]

                tCollection.save(mongoRecord,safe=True)


        except:
            message = ["error while persisting record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            raise ErrorMongoProcessing(message)


    def beispielLesenEinesRecord(self):

    #test = self.collectionRecords.find()

    #for document in test:
    #    r = document["record"]
    #    lesbar = zlib.decompress(r)
    #    print dict(r)
        pass



class PersistDNBGNDRecordMongo(HarvestingTask):

    def __init__(self):
        HarvestingTask.__init__(self)

    def  processRecord(self, taskContext=None ):
        #todo: search for recordID if None -> use HasType
        #if rid is None or dbWrapper is None:
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: id of record must not be None and dbWrapper must not be None")

        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistDNBGNDRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        isDeleted = taskContext.isDeleted()


        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

            status = None
            #if re.search("status=\"deleted\"",record,re.UNICODE | re.DOTALL):
            if isDeleted:

                gndid = None
                dbid = None
                selectedGNDFields = {}
                status = "deleted"
            else:
                cGNDContent = CollectGNDContent()
                #cGNDContent = CollectGNDContentNoNamespace()
                xml.sax.parseString("".join(record), cGNDContent)

                selectedGNDFields = cGNDContent.getSelectedValues()

                #tId = result["id"]
                #dbid and gndid has to be deleted in the GNDFieldsValueStructure
                dbid = selectedGNDFields["dbid"]
                gndid = selectedGNDFields["gndid"]

                selectedGNDFields.pop("dbid")
                selectedGNDFields.pop("gndid")

            mongoRecord = tCollection.find_one({"_id": rid})
            binary = Binary( zlib.compress(record,9))

            if not mongoRecord:
                if status is None:
                    status = "new"
                newRecord = {"_id":rid,
                             "datum":str(datetime.now())[:10],
                             "gndid": gndid,
                             "dbid" : dbid,
                             "record":binary,
                             "gndfields":selectedGNDFields,
                             "status":status
                }

                tCollection.insert(newRecord)

            else:

                if status is None:
                    status = "updated"

                #todo: Suche nach deleted record!
                mongoRecord["record"] = binary
                mongoRecord["gndid"] = gndid
                mongoRecord["dbid"] = dbid
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]
                mongoRecord["gndfields"] = selectedGNDFields

                tCollection.save(mongoRecord,safe=True)


        except Exception as tException:


            print "fehler in record"
            print str(tException)
            print record

            message = ["error while persisting gnd record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            #raise ErrorMongoProcessing(message)



class PersistInitialDNBGNDRecordMongo(PersistDNBGNDRecordMongo):
    def __init__(self):
        PersistDNBGNDRecordMongo.__init__(self)

        self.header= "<record>\n<header>\n<identifier>valuerecordid</identifier>\n<datestamp>valuedatestamp</datestamp>\n<setSpec>authorities</setSpec>\n</header>\n<metadata>\n"

    def  processRecord(self, taskContext=None ):


        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistInitialDNBGNDRecordMongo.procesRecord: no valid taskContext")

        rid = taskContext.getID()
        record = taskContext.getRecord()



        #clean up the record

        #pattern = re.compile("188519149")
        #if pattern.search(record):
        #    print "gefunden"

        #sometimes there is a namespace witjout prefix in the source record
        #this confuses the replace mechanism
        record = re.sub("<record .*?type=.*?>","<record type=\"Authority\">",record,re.UNICODE | re.DOTALL)


        recordNS = re.sub("<record type=\"Authority\">","<slim:record type=\"Authority\" xmlns:slim=\"http://www.loc.gov/MARC21/slim\">",record,re.UNICODE | re.DOTALL)
        recordNSCtrl = re.sub("<controlfield","<slim:controlfield",recordNS,1000, re.UNICODE | re.DOTALL)
        recordNSCtrlData = re.sub("<datafield","<slim:datafield",recordNSCtrl,2000, re.UNICODE | re.DOTALL)
        recordNSCtrlDataSub = re.sub("<subfield","<slim:subfield",recordNSCtrlData,2000,re.UNICODE | re.DOTALL )
        recordNSCtrlDataSubLeader = re.sub("<leader>","<slim:leader>",recordNSCtrlDataSub,re.UNICODE | re.DOTALL)

        recordNSE = re.sub("</record>","</slim:record>",recordNSCtrlDataSubLeader,re.UNICODE | re.DOTALL)
        recordNSCtrlE = re.sub("</controlfield>","</slim:controlfield>",recordNSE,1000, re.UNICODE | re.DOTALL)
        recordNSCtrlDataE = re.sub("</datafield>","</slim:datafield>",recordNSCtrlE,2000, re.UNICODE | re.DOTALL)
        recordNSCtrlDataSubE = re.sub("</subfield>","</slim:subfield>",recordNSCtrlDataE,2000,re.UNICODE | re.DOTALL)
        recordNSCtrlDataSubLeaderE = re.sub("</leader>","</slim:leader>",recordNSCtrlDataSubE,re.UNICODE | re.DOTALL)

        headerID =  re.sub("valuerecordid",rid,self.header,re.UNICODE | re.DOTALL)
        headerIDDate = re.sub("valuedatestamp",'{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.now()),headerID,re.UNICODE | re.DOTALL)

        wholeRecord = headerIDDate + recordNSCtrlDataSubLeaderE + "</metadata>\n</record>"

        #<record><header><identifier>valuerecordid</identifier><datestamp>valuedatestamp</datestamp><setSpec>authorities</setSpec></header><metadata>
        #'{%Y-%m-%dT%H:%M:%SZ}'.format(datetime.now())

        tId = "(" + taskContext.getConfiguration().getNetworkPrefix() + ")" + rid
        #todo necessary?
        taskContext.setID(tId)
        PersistDNBGNDRecordMongo.processRecord(self,taskContext=taskContext)





class RecordDirectToSearchEngine(HarvestingTask):

    def __init__(self,element):
        HarvestingTask.__init__(self)


    def  processRecord(self, taskContext=None):
        pass


class CollectGNDContent(ContentHandler):

    def __init__(self):
        ContentHandler.__init__(self)
        #TAGS.TO.USE=400_a###400_b###400_c###400_d###400_x###410_a###410_b###411_a###411_b###430_a###450_a###450_x###451_a###451_x
        self.searchedTagCodes = {'400': ['a','b','c','d','x'], '410': ['a','b'], '411': ['a','b'],'430':['a'],'450':['a','x'],'451':['a','x']}
        self.foundTagCodesValues ={}
        self.lastValidTag = None
        self.lastValidSubFieldCode = None
        self.tagName = ""

        self.procContentSubfield = {}
        self.relevantGNDIDdatafield = "035"
        self.relevantGNDIDsubfield = "a"
        self.inGNDIDField = False
        self.inGNDIDsubfield = False

        self.pGNDIDPattern = re.compile("\(DE-588\)",re.UNICODE | re.DOTALL | re.IGNORECASE)

        #self.


    def getSelectedValues(self):
        return self.foundTagCodesValues

    def startElement(self, name, attrs):

        if name.find('slim:controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('slim:datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes:
                self.lastValidTag = attrs.get("tag")
            else:
                self.lastValidTag = None
        elif name.find("slim:subfield") != -1:
            if self.lastValidTag is not None:
                self.lastValidSubFieldCode = attrs.get("code")
            else:
                self.lastValidSubFieldCode = None
            if self.inGNDIDField and attrs.get("code") == self.relevantGNDIDsubfield:
                self.inGNDIDsubfield = True
            else:
                self.inGNDIDsubfield = False


        else:
            self.lastValidTag = None
            self.lastValidSubFieldCode = None
        if name.find('slim:datafield') != -1:
            if attrs.get("tag") == self.relevantGNDIDdatafield:
                self.inGNDIDField = True
            else:
                self.inGNDIDField = False





    def endElement(self, name):
        if name.find("slim:subfield") != -1:
            t = self.procContentSubfield.items()
            if self.procContentSubfield.__len__() > 0:
                for key in self.procContentSubfield:

                    if key in self.foundTagCodesValues:
                        self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                    else:
                        self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
            self.procContentSubfield = {}
            self.lastValidSubFieldCode = None
        elif name.find('slim:datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None



    def characters(self, content):
        if self.tagName == "controlfield_001":
            self.foundTagCodesValues["dbid"] = content.rstrip()
            self.tagName = ""
        if self.lastValidTag is not None and   self.lastValidSubFieldCode is not None:
            if self.lastValidSubFieldCode in self.searchedTagCodes[self.lastValidTag]:

                #Warum dieser "Zwischenspeicher" self.procContentSubfield
                #{u'400_a': [u'Cresse\u0301, Auguste J. ', u'\x98', u'de', u'\x9c']}
                #{u'400_a': [u'Cresse\u0301, Auguste J. \x98de\x9c']}
                #Es gibt Werte von tags wie der gezeigte, fuer die der character handler des Sax Parsers mehrfach aufgerufen wird,
                #ohne dass zuvor der endElement Handler fuer das subfield aufgerufen wuerde
                #schriebe man den Wert von content dann direkt nach self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode]
                #werden die Elemente im Beipiel als einzelne items der Liste gesetzt und als mehrfache Werte des Codes 400_a behandelt


                if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.procContentSubfield:
                    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content.rstrip())
                else:
                    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content.rstrip()]
                    #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.foundTagCodesValues:
                    #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                    #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                    #else:
                    #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
                    #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
        elif self.inGNDIDsubfield:

            if self.pGNDIDPattern.search(content):
                self.foundTagCodesValues["gndid"] = content.rstrip()
                #self.gndSearchID = content

            self.inGNDIDsubfield = False





class CollectGNDContentNoNamespace(CollectGNDContent):
    def __init__(self):
        CollectGNDContent.__init__(self)

    def startElement(self, name, attrs):

        if name.find('controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes:
                self.lastValidTag = attrs.get("tag")
            else:
                self.lastValidTag = None
        elif name.find("subfield") != -1:
            if self.lastValidTag is not None:
                self.lastValidSubFieldCode = attrs.get("code")
            else:
                self.lastValidSubFieldCode = None
            if self.inGNDIDField and attrs.get("code") == self.relevantGNDIDsubfield:
                self.inGNDIDsubfield = True
            else:
                self.inGNDIDsubfield = False


        else:
            self.lastValidTag = None
            self.lastValidSubFieldCode = None
        if name.find('datafield') != -1:
            if attrs.get("tag") == self.relevantGNDIDdatafield:
                self.inGNDIDField = True
            else:
                self.inGNDIDField = False





    def endElement(self, name):
        if name.find("subfield") != -1:
            t = self.procContentSubfield.items()
            if self.procContentSubfield.__len__() > 0:
                for key in self.procContentSubfield:

                    if key in self.foundTagCodesValues:
                        self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                    else:
                        self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
            self.procContentSubfield = {}
            self.lastValidSubFieldCode = None
        elif name.find('datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None




