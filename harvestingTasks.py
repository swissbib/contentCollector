# -*- coding: utf-8 -*-
from lxml import etree
import StringIO

from pymongo.connection import Connection
from swissbibUtilities import ErrorMongoProcessing
import sys
import zlib
#from pymongo.binary import Binary
from bson.binary import Binary
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
        recordTimestamp = taskContext.getRecordTimestamp()

        if not recordTimestamp is None:
            try:
                recordTimestamp = datetime.strptime(recordTimestamp,"%Y-%m-%dT%H:%M:%SZ")
            except:
                recordTimestamp = None


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

                if not recordTimestamp is None:
                    newRecord = {"_id":rid,
                                 "datum":str(datetime.now())[:10],
                                 "record":binary,
                                 "status":status,
                                 "recordTimestamp":recordTimestamp
                    }
                else:
                    newRecord = {"_id": rid,
                                 "datum": str(datetime.now())[:10],
                                 "record": binary,
                                 "status": status,
                                 }

                tCollection.insert(newRecord)

            else:
                if isDeleted:
                    status = "deleted"
                    taskContext.getResultCollector().addRecordsDeleted(1)
                else:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)

                if not recordTimestamp is None:
                    mongoRecord["record"] = binary
                    mongoRecord["status"] = status
                    mongoRecord["datum"] = str(datetime.now())[:10]
                    mongoRecord["recordTimestamp"] = recordTimestamp
                else:
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



class PersistDNBGNDRecordMongo(PersistRecordMongo):

    def __init__(self):
        PersistRecordMongo.__init__(self)
        self.pHasMetastructure = re.compile('<header><identifier>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.pCoreRecord = re.compile('.*?(<record type="Authority".*?</record>).*?</metadata>.*?</record>.*',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def  processRecord(self, taskContext=None ):
        #todo: search for recordID if None -> use HasType
        #if rid is None or dbWrapper is None:
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: id of record must not be None and dbWrapper must not be None")

        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistDNBGNDRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        sMetaStrcuture = self.pHasMetastructure.search(record)
        if sMetaStrcuture:

            sCoreRecord = self.pCoreRecord.search(record)
            if not sCoreRecord is None:
                record = sCoreRecord.group(1)
            else:
                #this should not happen!
                message = ["OAI metastructure was found but was not able to grep the core record\n",
                           "docid: ", rid,
                           "record: ", record]
                raise ErrorMongoProcessing(message)


        isDeleted = taskContext.isDeleted()

        recordTimestamp = taskContext.getRecordTimestamp()

        if not recordTimestamp is None:
            try:
                recordTimestamp = datetime.strptime(recordTimestamp, "%Y-%m-%dT%H:%M:%SZ")
            except:
                recordTimestamp = None

        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

            status = None
            #if re.search("status=\"deleted\"",record,re.UNICODE | re.DOTALL):
            if isDeleted:

                taskContext.getResultCollector().addRecordsDeleted(1)

                deleteStructure = {"_id":rid}
                tCollection.remove(deleteStructure)
                return


            else:
                #cGNDContent = CollectGNDContent()
                cGNDContent = CollectGNDContentNoNamespace()
                xml.sax.parseString("".join(record), cGNDContent)

                selectedGNDFields = cGNDContent.getSelectedValues()
                selectedMACSFields = cGNDContent.getSelectedMACSValues()

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
                    taskContext.getResultCollector().addRecordsToCBSInserted(1)

                if not recordTimestamp is None:

                    newRecord = {"_id":rid,
                                 "datum":str(datetime.now())[:10],
                                 "gndid": gndid,
                                 "dbid" : dbid,
                                 "record":binary,
                                 "gndfields":selectedGNDFields,
                                 "macsfields" : selectedMACSFields,
                                 "status":status,
                                 "recordTimestamp": recordTimestamp
                                }
                else:
                    newRecord = {"_id":rid,
                                 "datum":str(datetime.now())[:10],
                                 "gndid": gndid,
                                 "dbid" : dbid,
                                 "record":binary,
                                 "gndfields":selectedGNDFields,
                                 "macsfields" : selectedMACSFields,
                                 "status":status
                                 }

                tCollection.insert(newRecord)

            else:

                if status is None:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)


                mongoRecord["record"] = binary
                mongoRecord["gndid"] = gndid
                mongoRecord["dbid"] = dbid
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]
                mongoRecord["gndfields"] = selectedGNDFields
                mongoRecord["macsfields"] = selectedMACSFields

                if not recordTimestamp is None:
                    mongoRecord["recordTimestamp"] = recordTimestamp

                tCollection.save(mongoRecord,safe=True)


        except Exception as tException:


            print "fehler in record"
            print str(tException)
            print record

            message = ["error while persisting gnd record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            #raise ErrorMongoProcessing(message)

class PersistNLMongo(PersistRecordMongo):


    def __init__(self):
        self.doctypePattern = re.compile('<!DOCTYPE.*?>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.articleStructure = re.compile('.*?(<article .*?</article>).*',re.UNICODE | re.DOTALL | re.IGNORECASE)
        PersistRecordMongo.__init__(self)

    def  processRecord(self, taskContext=None ):
        record = taskContext.getRecord()
        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()

        doctype = None

        mhasDocType = self.doctypePattern.search(record)
        if mhasDocType:
            doctype = mhasDocType.group(0)
        #this is a bit insecure - are there better ways to fetch only the article structure?
        mArticleStructure = self.articleStructure.search(record)
        articleStructure = None
        if mArticleStructure:
            articleStructure = mArticleStructure.group(1)
        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


            mongoRecord = tCollection.find_one({"_id": rid})
            binary = Binary( zlib.compress(record,9))

            recordTree=etree.fromstring(record)

            # Get year from XML
            xpathGetPYear = "//pub-date[@pub-type='ppub']/year"
            xpathGetEYear = "//pub-date[@pub-type='epub']/year"
            xpathGetYear = "//pub-date/year"
            xpathCopyrightYear= "//copyright-year"

            resultPYear = recordTree.xpath(xpathGetPYear)
            resultEYear = recordTree.xpath(xpathGetEYear)
            resultYear = recordTree.xpath(xpathGetYear)
            resultCopyrightYear = recordTree.xpath(xpathCopyrightYear)

            year=0
            if len(resultPYear) > 0 :
                year=resultPYear[0].text
            elif len(resultEYear) > 0:
                year=resultEYear[0].text
            elif len(resultYear) > 0:
                year=resultYear[0].text
            elif len(resultCopyrightYear) > 0:
                year=resultCopyrightYear[0].text




            newRecord = {"_id":rid,
                         "datum":str(datetime.now())[:10],
                         "year":year,
                         "record":binary,
                        }

            tCollection.insert(newRecord)


        except Exception as tException:
            print tException




class PersistDSV11RecordMongo(PersistRecordMongo):

    def __init__(self):
        PersistRecordMongo.__init__(self)

        self.matchTagCodes = {'100': None, '110': None,'111': None, '130':None,'152':None}
        self.originalTagCodes = {'100': None, '110': None,'111': None, '130':None,'152':None}

        self.regexNoSort = re.compile("<<.*?>>", re.UNICODE)
        self.regexCreateMatch = re.compile("[\W]", re.UNICODE)



    def  processRecord(self, taskContext=None ):

        for key in self.matchTagCodes:
            self.matchTagCodes[key] = None
        for key in self.originalTagCodes:
            self.originalTagCodes[key] = None


        #todo: search for recordID if None -> use HasType

        #Problemsatz
        #{ "_id" : "(DSV11)oai:alephtest.unibas.ch:DSV11-000000020", "status" : "new", "match130" : "targumyerushalmiii",
        # "match151" : null, "match150" : null, "match100" : "echovantonpavloviostrovsachalin", "dbid" : "000000020", "match110" : null, "datum" : "2014-03-11",
        # "additionalvalues" : { "400" : [ "Čechov, Anton Pavlovič", "<<Die>> Insel Sachalin" ] }, "org150" : null, "org151" : null,
        # "org100" : [ "Čechov, Anton Pavlovič", "Ostrov Sachalin" ], "org110" : null, "org130" : [ "Targum Yerushalmi II" ], "record" : BinData(") }
        #das ist jetzt besser durch re.UNICODE

        #Frage
        #ich habe zwei matchkeys aber nicht mehere 400er values - richtig?
        #{ "_id" : "(DSV11)oai:alephtest.unibas.ch:DSV11-000000054", "status" : "new", "match130" : "targumyerushalmiii", "match151" : null, "match150" : null,
        # "match100" : "cioranemilemicheltentationdexister", "dbid" : "000000054", "match110" : null, "datum" : "2014-03-11",
        # "additionalvalues" : { "400" : [ "Cioran, Emile Michel", "Dasein als Versuchung" ] }, "org150" : null, "org151" : null,
        # "org100" : [ "Cioran, Emile Michel", "<<La>> tentation d'exister" ], "org110" : null, "org130" : [ "Targum Yerushalmi II" ], "record" : BinData() }



        #if rid is None or dbWrapper is None:
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: id of record must not be None and dbWrapper must not be None")

        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistDNBGNDRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        isDeleted = taskContext.isDeleted()


        recordTimestamp = taskContext.getRecordTimestamp()

        if not recordTimestamp is None:
            try:
                recordTimestamp = datetime.strptime(recordTimestamp, "%Y-%m-%dT%H:%M:%SZ")
            except:
                recordTimestamp = None

        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

            status = None
            #if re.search("status=\"deleted\"",record,re.UNICODE | re.DOTALL):
            selectedMatchFields = {}
            selectedAdditionalValues = {}
            cDSV11Content = CollectDSV11Content()

            if isDeleted:
                dbid = None
                #selectedAdditionalValues = {}
                status = "deleted"
            else:
                #cGNDContent = CollectDSV11Content()

                xml.sax.parseString("".join(record), cDSV11Content)

                selectedMatchFields = cDSV11Content.getSelectedMatchValues()
                selectedAdditionalValues = cDSV11Content.getSelectedAdditionalValues()

                #tId = result["id"]
                #dbidhas to be deleted in the GNDFieldsValueStructure
                dbid = selectedMatchFields["dbid"]
                selectedMatchFields.pop("dbid")

                #regex = re.compile("[^\\p{L}\\p{M}*\\p{N}]", re.UNICODE | re.DOTALL)
                #regex = re.compile(r"[^\p{L}\p{M}*\p{N}]")
                for key,valueList in selectedMatchFields.items():
                    self.originalTagCodes[key] = valueList
                    self.matchTagCodes[key] = self.buildMatchKey(valueList)

            mongoRecord = tCollection.find_one({"_id": rid})
            binary = Binary( zlib.compress(record,9))


            if not mongoRecord:
                if status is None:
                    status = "new"
                newRecord = {"_id":rid,
                             "datum":str(datetime.now())[:10],
                             "dbid" : dbid,
                             "match100": self.matchTagCodes['100'],
                             "match110": self.matchTagCodes['110'],
                             "match111": self.matchTagCodes['111'],
                             "match130": self.matchTagCodes['130'],
                             "match152": self.matchTagCodes['152'],
                             "org100" : self.originalTagCodes['100'],
                             "org110" : self.originalTagCodes['110'],
                             "org111" : self.originalTagCodes['111'],
                             "org130" : self.originalTagCodes['130'],
                             "org152" : self.originalTagCodes['152'],
                             "record":binary,
                             "additionalvalues":selectedAdditionalValues,
                             "status":status,
                             "recordTimestamp": recordTimestamp
                }

                tCollection.insert(newRecord)

            else:

                if status is None:
                    status = "updated"

                #todo: Suche nach deleted record!
                mongoRecord["record"] = binary
                #mongoRecord["gndid"] = gndid
                mongoRecord["dbid"] = dbid
                mongoRecord["match100"] = self.matchTagCodes['100'],
                mongoRecord["match110"] = self.matchTagCodes['110'],
                mongoRecord["match111"] = self.matchTagCodes['111'],
                mongoRecord["match130"] = self.matchTagCodes['130'],
                mongoRecord["match152"] = self.matchTagCodes['152'],
                mongoRecord["org100"] = self.originalTagCodes['100'],
                mongoRecord["org110"] = self.originalTagCodes['110'],
                mongoRecord["org111"] = self.originalTagCodes['111'],
                mongoRecord["org130"] = self.originalTagCodes['130'],
                mongoRecord["org152"] = self.originalTagCodes['152'],
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]
                mongoRecord["additionalvalues"] = selectedAdditionalValues
                mongoRecord["recordTimestamp"] = recordTimestamp

                tCollection.save(mongoRecord,safe=True)


        except Exception as tException:


            print "fehler in record"
            print str(tException)
            print record

            message = ["error while persisting gnd record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            #raise ErrorMongoProcessing(message)

    def  buildMatchKey(self, valueList ):
        newList = []
        for value in valueList:
            #newValue = regex.sub("",value)
            #newValue = re.sub("[^\\p{L}\\p{M}*\\p{N}]","",value,1000,re.UNICODE | re.DOTALL)
            #value = "test<<der>>" + value + "<<la>>" + "nun das ende"
            #value = self.regexNoSort.sub("",value,10000)
            #test = re.sub("<<.*?>>","",value,10000)
            #newValue = re.sub("[\W]","",value,10000).lower()
            value = self.regexCreateMatch.sub("",value,10000).lower()
            #newValue = newValue.lower()
            #newValue1 = re.sub("[^\p{L}\p{M}*\p{N}]","",value,re.UNICODE )
            newList.append(value)

        return "".join(newList)


class PersistInitialDNBGNDRecordMongo(PersistDNBGNDRecordMongo):
    def __init__(self):
        PersistDNBGNDRecordMongo.__init__(self)

        self.header= "<record>\n<header>\n<identifier>valuerecordid</identifier>\n<datestamp>valuedatestamp</datestamp>\n<setSpec>authorities</setSpec>\n</header>\n<metadata>\n"

    def  processRecord(self, taskContext=None ):


        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistInitialDNBGNDRecordMongo.procesRecord: no valid taskContext")



        #clean up the record
        #for GND we doesn't want to use whole OAI record as we did before

        taskContext.setRecord(re.sub("<record .*?type=.*?>","<record type=\"Authority\" xmlns=\"http://www.loc.gov/MARC21/slim\">",
                                     taskContext.getRecord(),re.UNICODE | re.DOTALL))

        taskContext.setID("(" + taskContext.getConfiguration().getNetworkPrefix() + ")" + taskContext.getID())
        PersistDNBGNDRecordMongo.processRecord(self,taskContext=taskContext)





class RecordDirectToSearchEngine(HarvestingTask):

    def __init__(self,element):
        HarvestingTask.__init__(self)


    def  processRecord(self, taskContext=None):
        pass


class TransformJatsToMods(HarvestingTask):
    def __init__(self):
        HarvestingTask.__init__(self)

        self.doctypePattern = re.compile('<!DOCTYPE.*?>', re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.articleStructure = re.compile('.*?(<article .*?</article>).*', re.UNICODE | re.DOTALL | re.IGNORECASE)

    def processRecord(self, taskContext=None):
        record = taskContext.getRecord()
        #print record
        mArticleStructure = self.articleStructure.search(record)
        articleStructure = None
        if mArticleStructure:
            articleStructure = mArticleStructure.group(1)
            f = StringIO.StringIO(articleStructure)
            xml = etree.parse(f)
            mods = taskContext.appContext.getModsTransformation()(xml)
            taskContext.appContext.getWriteContext().writeItem(etree.tostring(mods))
            #print(etree.tostring(mods, pretty_print=True))

class CollectGNDContent(ContentHandler):

    def __init__(self):
        ContentHandler.__init__(self)
        #TAGS.TO.USE=400_a###400_b###400_c###400_d###400_x###410_a###410_b###411_a###411_b###430_a###450_a###450_x###451_a###451_x
        self.searchedTagCodes = {'400': ['a','b','c','d','x'], '410': ['a','b'], '411': ['a','b'],'430':['a'],'450':['a','x'],'451':['a','x']}
        #self.searchedTagMacCodes = {'750': ['a','b','v','x','y','z','0','2','5']}
        self.searchedTagMacCodes = {'750': ['a']}
        self.foundTagCodesValues ={}
        self.foundMACSTagCodesValues ={}
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

    def getSelectedMACSValues(self):
        return self.foundMACSTagCodesValues



    def startElement(self, name, attrs):

        if name.find('slim:controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('slim:datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes or attrs.get("tag") in self.searchedTagMacCodes:
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

                    if self.lastValidTag in self.searchedTagCodes:
                        if key in self.foundTagCodesValues:
                            self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    elif self.lastValidTag in self.searchedTagMacCodes:
                        if key in self.foundMACSTagCodesValues:
                            self.foundMACSTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundMACSTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    else:
                        print "can't assign last valid to to any searchedTagCodes in endElement"
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
            if self.lastValidTag in self.searchedTagCodes:

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
            elif self.lastValidTag in self.searchedTagMacCodes:
                if self.lastValidSubFieldCode in self.searchedTagMacCodes[self.lastValidTag]:


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
            else:
                print "tag: " + self.lastValidTag + " not part of any search dictionaries (GND or MACS)"

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
            if attrs.get("tag") in self.searchedTagCodes or attrs.get("tag") in self.searchedTagMacCodes:
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

                    if self.lastValidTag in self.searchedTagCodes:
                        if key in self.foundTagCodesValues:
                            self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    elif self.lastValidTag in self.searchedTagMacCodes:
                        if key in self.foundMACSTagCodesValues:
                            self.foundMACSTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundMACSTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    else:
                        print "can't assign last valid to to any searchedTagCodes in endElement"
            self.procContentSubfield = {}
            self.lastValidSubFieldCode = None
        elif name.find('datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None



class CollectDSV11Content(ContentHandler):

    def __init__(self):
        ContentHandler.__init__(self)
        #TAGS.TO.USE=400_a###400_b###400_c###400_d###400_x###410_a###410_b###411_a###411_b###430_a###450_a###450_x###451_a###451_x
        self.searchedTagCodes = {'100': ['a','b','c','d', 'q'],  '110': ['a','b'],'111':['a'], '130': ['a','g','k' ,'m','n' ,'o','p','r','s'],'152':['d']}
        #$a$g$k$m$n$o$p$r$s
        self.additionalAuthorityValue = {'400': ['a','b','c','d','q'], '410': ['a','b'],'411': ['a'], '430': ['a','g','k','m','n','o','p','r','s'], '452':['d'],'500': ['a','b','c','d','q'], '510': ['a','b'],'511': ['a'], '530': ['a','g','k','m','n','o','p','r','s'], '552':['d']}


        #Besonderheiten 130: Oliver sucht nach drei p - Subfields
        #-> Probleme dabei: Reihenfolge / was ist, wenn es nur zwei oder aber vier p - subfields gibt?

        #Besonderheiten 100 / 700:
        # -> c nur das erste subfield -> gibt es nur ein subfield? was wenn mehr?

        #110 verwendet er gar nicht - warum?

        #150 wird nicht verwendet - warum?

        # 151 wird nicht verwendet - warum







        self.foundTagCodesValues ={}
        self.foundTagCodesAuthorityValues ={}
        self.lastValidTag = None
        self.lastValidAuthorityTag = None
        self.lastValidSubFieldCode = None
        self.lastValidAuthoritySubFieldCode = None
        self.tagName = ""

        self.procContentSubfield = {}
        self.procContentAuthoritySubfield = {}
        self.relevantGNDIDdatafield = "035"
        self.relevantGNDIDsubfield = "a"
        self.inGNDIDField = False
        self.inGNDIDsubfield = False

        #self.pGNDIDPattern = re.compile("\(DE-588\)",re.UNICODE | re.DOTALL | re.IGNORECASE)

        #self.


    def getSelectedMatchValues(self):
        return self.foundTagCodesValues

    def getSelectedAdditionalValues(self):
        return self.foundTagCodesAuthorityValues

    def startElement(self, name, attrs):

        if name.find('marc:controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('marc:datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes:
                self.lastValidTag = attrs.get("tag")
            elif attrs.get("tag") in self.additionalAuthorityValue:
                self.lastValidAuthorityTag = attrs.get("tag")
            else:
                self.lastValidTag = None
                self.lastValidAuthorityTag  = None

        elif name.find("marc:subfield") != -1:
            if self.lastValidTag is not None:
                self.lastValidSubFieldCode = attrs.get("code")
            elif self.lastValidAuthorityTag is not None:
                self.lastValidAuthoritySubFieldCode = attrs.get("code")
            else:
                self.lastValidSubFieldCode = None
                self.lastValidAuthoritySubFieldCode = None
            #if self.inGNDIDField and attrs.get("code") == self.relevantGNDIDsubfield:
            #    self.inGNDIDsubfield = True
            #else:
            #    self.inGNDIDsubfield = False


        else:
            self.lastValidTag = None
            self.lastValidSubFieldCode = None
            self.lastValidAuthorityTag = None
            self.lastValidAuthoritySubFieldCode = None

        #if name.find('slim:datafield') != -1:
        #    if attrs.get("tag") == self.relevantGNDIDdatafield:
        #        self.inGNDIDField = True
        #    else:
        #        self.inGNDIDField = False





    def endElement(self, name):
        if name.find("marc:subfield") != -1:
            #t = self.procContentSubfield.items()
            if self.procContentSubfield.__len__() > 0:
                for key in self.procContentSubfield:

                    if key in self.foundTagCodesValues:
                        self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                    else:
                        self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
            elif self.procContentAuthoritySubfield.__len__() > 0:

                for key in self.procContentAuthoritySubfield:

                    if key in self.foundTagCodesAuthorityValues:
                        self.foundTagCodesAuthorityValues[key].append("".join(self.procContentAuthoritySubfield[key]))
                    else:
                        self.foundTagCodesAuthorityValues[key] = ["".join(self.procContentAuthoritySubfield[key])]

            self.procContentSubfield = {}
            self.procContentAuthoritySubfield = {}
            self.lastValidSubFieldCode = None
            self.lastValidAuthoritySubFieldCode = None
        elif name.find('marc:datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None
            self.lastValidAuthorityTag = None
            self.lastValidAuthoritySubFieldCode = None



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


                #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.procContentSubfield:
                if self.lastValidTag in self.procContentSubfield:
                    #self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content.rstrip())
                    self.procContentSubfield[self.lastValidTag].append(content.rstrip())
                else:
                    #self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content.rstrip()]
                    self.procContentSubfield[self.lastValidTag] = [content.rstrip()]
                    #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.foundTagCodesValues:
                    #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                    #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                    #else:
                    #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
                    #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
        elif self.lastValidAuthorityTag is not None and   self.lastValidAuthoritySubFieldCode is not None:
            if self.lastValidAuthoritySubFieldCode in self.additionalAuthorityValue[self.lastValidAuthorityTag]:
                #if self.lastValidAuthorityTag + "_" + self.lastValidAuthoritySubFieldCode in self.procContentAuthoritySubfield:
                if self.lastValidAuthorityTag in self.procContentAuthoritySubfield:
                    #self.procContentAuthoritySubfield[self.lastValidAuthorityTag + "_" + self.lastValidAuthoritySubFieldCode].append(content.rstrip())
                    self.procContentAuthoritySubfield[self.lastValidAuthorityTag].append(content.rstrip())
                else:
                    #self.procContentAuthoritySubfield[self.lastValidAuthorityTag + "_" + self.lastValidAuthoritySubFieldCode] = [content.rstrip()]
                    self.procContentAuthoritySubfield[self.lastValidAuthorityTag] = [content.rstrip()]
        #elif self.inGNDIDsubfield:
        #
        #    if self.pGNDIDPattern.search(content):
        #        self.foundTagCodesValues["gndid"] = content.rstrip()
        #        #self.gndSearchID = content

        #    self.inGNDIDsubfield = False




