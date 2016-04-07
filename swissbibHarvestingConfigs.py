from datetime import datetime
import os
import re

from harvestingTasks import HarvestingTask, PersistRecordMongo, RecordDirectToSearchEngine, PersistDNBGNDRecordMongo, PersistInitialDNBGNDRecordMongo, PersistDSV11RecordMongo
from swissbibUtilities import MongoHostDefinition


from lxml import etree


__author__ = 'swissbib'


class HarvestingConfigs():

    def __init__(self,filename):

        self.applicationDir = os.getcwd()



        self.validTags = ['baseDir','source',
                          'actionFinished','completeListSize',
                          'cursor','dumpDir',
                          'granularity', 'identifier',
                          'manualUntil','metadataPrefix',
                          'resumptionToken','setDescription',
                          'setName','setSpec',
                          'stoppageTime','timestampUTC',
                          'url', 'networkPrefix',
                          'baseDir','errorLogDir',
                          'processLogDir','errorLogFile',
                          'processLogFile','mongoHosts',
                          #'mongoPort','mongoCollection',
                          #'mongoDB','mongoCollectionSummary',
                          'archiveDir','resultDir',
                          'confdir', 'hashRenderer',
                          'dumpDirSkipped','skipRecords',
                          'logSkippedRecords','dataTagExcludedFromHash',
                          'substituteCharacters','prefixSummaryFile',
                          'tasks','oaiIdentifierSysNumber','httpproxy',
                          'writeHarvestedFiles', 'debugging',
                          'resumptionTokenLogDir','resumptionTokenLogFile',
                          'writeResumptionToken','encodeUnicodeAsUTF8',
                          'iteratorOAIStructure','transformExLibrisNStructureForCBS',
                          'oaiDeleteDir', 'maxDocuments',
                          'archiveNotSent','blocked',
                          'eMailNotifification','mailServer',
                          'addRecordTimeStamp']

        self.configFileName = filename
        self.tree = etree.parse(self.configFileName)

        self.summaryFile = None
        self.summaryContentFileSkipped = None
        self.dataTagsExcluded = None
        self.substituteCharacters = None

        #xml.etree.ElementTree.dump(tree)
        self.tagsDict = {}
        self.lastResumptionToken = None
        self.tasksDict = {}
        self.hostsDict = {}

        for tag in self.validTags:
            try:
                searchResult = self.tree.find(".//" + tag)
                if not searchResult is None:

                    self.tagsDict[tag] = self.tree.find(".//" + tag).text
                    if tag == "tasks":
                        tasksCollection = self.tree.find(".//" + tag)
                        for element in tasksCollection.iter(tag="task"):
                            taskName =  element.get("name")
                            taskObject = globals()[taskName]()
                            self.tasksDict[taskName] = taskObject

                    elif tag == "mongoHosts":
                        mongoHosts = self.tree.find(".//" + tag)
                        for element in mongoHosts.iter(tag="mongoHost"):
                            host = MongoHostDefinition(element)
                            self.hostsDict[element.get("name")] = host


                    if not self.tagsDict[tag] is None :
                        if re.search("\{basedir\}",self.tagsDict[tag]):
                            self.tagsDict[tag] =  re.sub("\{basedir\}",self.tagsDict['baseDir'],self.tagsDict[tag])
                else:
                    self.tagsDict[tag] = None


            except AttributeError as aErr:
                print (aErr)

    #Erweiterungen: s. config.abn.xml



    def getMailServer(self):
        return self.tagsDict['mailServer']

    def setMailServer(self,value):
        self._setLXMLTreeNodeValue("mailServer", value)
        self.tagsDict['mailServer'] = value

    def getEMailNotifification(self):
        return self.tagsDict['eMailNotifification']

    def setEMailNotifification(self,value):
        self._setLXMLTreeNodeValue("eMailNotifification", value)
        self.tagsDict['eMailNotifification'] = value


    def getBlocked(self):
        if not self.tagsDict['blocked'] is None:
            return  not (self.tagsDict['blocked']).strip().lower() in ['false','f','n','0','']
        else:
            return False


    def setBlocked(self,value):
        self._setLXMLTreeNodeValue("blocked", value)
        self.tagsDict['blocked'] = value



    def getArchiveNotSent(self):
        return self.tagsDict['archiveNotSent']

    def setArchiveNotSent(self,value):
        self._setLXMLTreeNodeValue("archiveNotSent", value)
        self.tagsDict['archiveNotSent'] = value


    def getMaxDocuments(self):
        return self.tagsDict['maxDocuments']

    def setMaxDocuments(self,value):
        self._setLXMLTreeNodeValue("maxDocuments", value)
        self.tagsDict['maxDocuments'] = value



    def getDedicatedTasks(self):
        return self.tasksDict


    def getActionFinished(self):
        return self.tagsDict['actionFinished']

    def setActionFinished(self,value):
        #self.tree.find(".//actionFinished").text = value
        self._setLXMLTreeNodeValue("actionFinished", value)

        self.tagsDict['actionFinished'] = value



    def getResumptionTokenLogDir(self):
        return self.tagsDict['resumptionTokenLogDir']

    def setResumptionTokenLogDir(self,value):
        #self.tree.find(".//actionFinished").text = value
        self._setLXMLTreeNodeValue("resumptionTokenLogDir", value)

        self.tagsDict['resumptionTokenLogDir'] = value


    def getResumptionTokenLogFile(self):
        return self.tagsDict['resumptionTokenLogFile']

    def setResumptionTokenLogFile(self,value):
        #self.tree.find(".//actionFinished").text = value
        self._setLXMLTreeNodeValue("resumptionTokenLogFile", value)

        self.tagsDict['resumptionTokenLogFile'] = value

    def getEncodeUnicodeAsUTF8(self):
        if not self.tagsDict['encodeUnicodeAsUTF8'] is None:

            return  not (self.tagsDict['encodeUnicodeAsUTF8']).strip().lower() in ['false','f','n','0','']
        else:
            return False


    def setEncodeUnicodeAsUTF8(self,value):
        self._setLXMLTreeNodeValue("encodeUnicodeAsUTF8", value)
        self.tagsDict['encodeUnicodeAsUTF8'] = value

    def setAddRecordTimeStamp(self,value):
        self._setLXMLTreeNodeValue("addRecordTimeStamp", value)
        self.tagsDict['addRecordTimeStamp'] = value


    def getAddRecordTimeStamp(self):
        if not self.tagsDict['addRecordTimeStamp'] is None:

            return not (self.tagsDict['addRecordTimeStamp']).strip().lower() in ['false', 'f', 'n', '0', '']
        else:
            return False


    def isWriteResumptionToken(self):
        if not self.tagsDict['writeResumptionToken'] is None:

            return  not (self.tagsDict['writeResumptionToken']).strip().lower() in ['false','f','n','0','']
        else:
            return False





    def getProxy(self):
        return self.tagsDict['httpproxy']

    def setProxy(self,value):
        #self.tree.find(".//httpproxy").text = value
        self._setLXMLTreeNodeValue("httpproxy", value)
        self.tagsDict['httpproxy'] = value

    def getWriteHarvestedFiles(self):
        if not self.tagsDict['writeHarvestedFiles'] is None:

            return  not (self.tagsDict['writeHarvestedFiles']).strip().lower() in ['false','f','n','0','']
        else:
            return False

    def setWriteHarvestedFiles(self,value):
        #self.tree.find(".//writeHarvestedFiles").text = value
        self._setLXMLTreeNodeValue("writeHarvestedFiles", value)
        self.tagsDict['writeHarvestedFiles'] = value


    def getDebugging(self):
        if not self.tagsDict['debugging'] is None:

            return  not (self.tagsDict['debugging']).strip().lower() in ['false','f','n','0','']
        else:
            return False

    def setDebugging(self,value):
        #self.tree.find(".//writeHarvestedFiles").text = value
        self._setLXMLTreeNodeValue("debugging", value)
        self.tagsDict['debugging'] = value



    def getDataTagExcludedFromHash(self):

        if not self.tagsDict['dataTagExcludedFromHash'] is None:
            # self.dataTagsExcluded is used as a helper property so values defined in the configuration structure are
            #processed only once to create a list structure returned to the client requesting this value
            if self.dataTagsExcluded is None:
                self.dataTagsExcluded = self.tagsDict['dataTagExcludedFromHash'].split("#")
            return self.dataTagsExcluded
        else:
            return None

    def setDataTagExcludedFromHash(self,value):
        #self.tree.find(".//dataTagExcludedFromHash").text = value
        self._setLXMLTreeNodeValue("dataTagExcludedFromHash", value)

        self.tagsDict['dataTagExcludedFromHash'] = value


    def getSubstituteCharacters(self):

        if not self.tagsDict['substituteCharacters'] is None:
            # self.substituteCharacters is used as a helper property so values defined in the configuration structure has
            #to be compiled as a regex pattern only once
            if self.substituteCharacters is None:
                self.substituteCharacters =  re.compile(self.tagsDict['substituteCharacters'], re.MULTILINE)
            return self.substituteCharacters
        else:
            return None

    def setSubstituteCharacters(self,value):
        #self.tree.find(".//substituteCharacters").text = value
        self._setLXMLTreeNodeValue("substituteCharacters", value)
        self.tagsDict['substituteCharacters'] = value



    def getDumpDirSkipped(self):

        return self.tagsDict['dumpDirSkipped']

    def setDumpDirSkipped(self,value):
        #self.tree.find(".//dumpDirSkipped").text = value
        self._setLXMLTreeNodeValue("dumpDirSkipped", value)
        self.tagsDict['dumpDirSkipped'] = value

    def getIteratorOAIStructure(self):

        return self.tagsDict['iteratorOAIStructure']

    def setIteratorOAIStructure(self,value):
        #self.tree.find(".//dumpDirSkipped").text = value
        self._setLXMLTreeNodeValue("iteratorOAIStructure", value)
        self.tagsDict['iteratorOAIStructure'] = value


    def isTransformExLibrisNStructureForCBS(self):
        if not self.tagsDict['transformExLibrisNStructureForCBS'] is None:
            return  not (self.tagsDict['transformExLibrisNStructureForCBS']).strip().lower() in ['false','f','n','0','']
        else:
            return False

    def setTransformExLibrisNStructureForCBS(self,value):
        self._setLXMLTreeNodeValue("transformExLibrisNStructureForCBS", value)
        self.tagsDict['transformExLibrisNStructureForCBS'] = value



    def getOaiIdentifierSysNumber(self):

        return self.tagsDict['oaiIdentifierSysNumber']

    def setOaiIdentifierSysNumber(self,value):
        #self.tree.find(".//oaiIdentifierSysNumber").text = value
        self._setLXMLTreeNodeValue("oaiIdentifierSysNumber", value)
        self.tagsDict['oaiIdentifierSysNumber'] = value



    def getCompleteListSize(self):
        return self.tagsDict['completeListSize']

    def setCompleteListSize(self,value):
        #self.tree.find(".//completeListSize").text = value
        self._setLXMLTreeNodeValue("completeListSize", value)
        self.tagsDict['completeListSize'] = value

    def isSkipRecords(self):


        if not self.tagsDict['skipRecords'] is None:

            return  not (self.tagsDict['skipRecords']).strip().lower() in ['false','f','n','0','']
        else:
            return False

    def setIsSkipRecords(self,value):
        #self.tree.find(".//skipRecords").text = value
        self._setLXMLTreeNodeValue("skipRecords", value)
        self.tagsDict['skipRecords'] = value



    def getLogSkippedRecords(self):

        if not self.tagsDict['logSkippedRecords'] is None:

            return  not (self.tagsDict['logSkippedRecords']).strip().lower() in ['false','f','n','0','']
        else:
            return False

    def setLogSkippedRecords(self,value):
        #self.tree.find(".//logSkippedRecords").text = value
        self._setLXMLTreeNodeValue("logSkippedRecords", value)
        self.tagsDict['logSkippedRecords'] = value



    def getCursor(self):
        return self.tagsDict['cursor']

    def setCursor(self,value):
        #self.tree.find(".//cursor").text = value
        self._setLXMLTreeNodeValue("cursor", value)
        self.tagsDict['cursor'] = value

    def getHashRenderer(self):
        return self.tagsDict['hashRenderer']

    def setHashRenderer(self,value):
        #self.tree.find(".//hashRenderer").text = value
        self._setLXMLTreeNodeValue("hashRenderer", value)
        self.tagsDict['hashRenderer'] = value


    def getDumpDir(self):
        return self.tagsDict['dumpDir']

    def setDumpDir(self,value):
        #self.tree.find(".//dumpDir").text = value
        self._setLXMLTreeNodeValue("dumpDir", value)
        self.tagsDict['dumpDir'] = value

    def getGranularity(self):
        return self.tagsDict['granularity']

    def setGranularity(self,value):
        #self.tree.find(".//granularity").text = value
        self._setLXMLTreeNodeValue("granularity", value)
        self.tagsDict['granularity'] = value

    def getIdentifier(self):
        return self.tagsDict['identifier']

    def setIdentifier(self,value):
        #self.tree.find(".//identifier").text = value
        self._setLXMLTreeNodeValue("identifier", value)
        self.tagsDict['identifier'] = value

    def getManualUntil(self):
        return self.tagsDict['manualUntil']

    def setManualUntil(self,value):
        #self.tree.find(".//manualUntil").text = value
        self._setLXMLTreeNodeValue("manualUntil", value)
        self.tagsDict['manualUntil'] = value

    def getMetadataPrefix(self):
        return self.tagsDict['metadataPrefix']

    def setMetadataPrefix(self,value):
        #self.tree.find(".//metadataPrefix").text = value
        self._setLXMLTreeNodeValue("metadataPrefix", value)
        self.tagsDict['metadataPrefix'] = value


    def getResumptionToken(self):
        return self.tagsDict['resumptionToken']

    def setResumptionToken(self,value):
        #self.tree.find(".//resumptionToken").text = value
        self._setLXMLTreeNodeValue("resumptionToken", value)
        self.tagsDict['resumptionToken'] = value

    def getSetDescription(self):
        return self.tagsDict['setDescription']

    def setSetDescription(self,value):
        #self.tree.find(".//setDescription").text = value
        self._setLXMLTreeNodeValue("setDescription", value)
        self.tagsDict['setDescription'] = value


    def getSetName(self):
        if not self.tagsDict['setName'] is None:
            return self.tagsDict['setName']
        else:
            return ""

    def setSetName(self,value):
        #self.tree.find(".//setName").text = value
        self._setLXMLTreeNodeValue("setName", value)
        self.tagsDict['setName'] = value

    def getSetSpec(self):
        if not self.tagsDict['setSpec'] is None:
            return self.tagsDict['setSpec']
        else:
            return None

    def setSetSpec(self,value):
        #self.tree.find(".//setSpec").text = value
        self._setLXMLTreeNodeValue("setSpec", value)
        self.tagsDict['setSpec'] = value

    def getStoppageTime(self):
        return self.tagsDict['stoppageTime']

    def setStoppageTime(self,value):
        #self.tree.find(".//stoppageTime").text = value
        self._setLXMLTreeNodeValue("stoppageTime", value)
        self.tagsDict['stoppageTime'] = value

    def getTimestampUTC(self):
        return self.tagsDict['timestampUTC']

    def setTimestampUTC(self,value):

        self._setLXMLTreeNodeValue("timestampUTC", value)

        #self.tree.find(".//timestampUTC").text = value
        self.tagsDict['timestampUTC'] = value

    def getUrl(self):
        return self.tagsDict['url']

    def setUrl(self,value):
        #self.tree.find(".//url").text = value
        self._setLXMLTreeNodeValue("url", value)
        self.tagsDict['url'] = value

    def getNetworkPrefix(self):
        return self.tagsDict['networkPrefix']

    def setNetworkPrefix(self,value):
        #self.tree.find(".//networkPrefix").text = value
        self._setLXMLTreeNodeValue("networkPrefix", value)
        self.tagsDict['networkPrefix'] = value


    def getBaseDir(self):
        return self.tagsDict['baseDir']

    def setBaseDir(self,value):
        #self.tree.find(".//baseDir").text = value
        self._setLXMLTreeNodeValue("baseDir", value)
        self.tagsDict['baseDir'] = value


    def getErrorLogDir(self):
        return self.tagsDict['errorLogDir']

    def setErrorLogDir(self,value):
        #self.tree.find(".//errorLogDir").text = value
        self._setLXMLTreeNodeValue("errorLogDir", value)
        self.tagsDict['errorLogDir'] = value

    def getArchiveDir(self):
        return self.tagsDict['archiveDir']

    def setArchiveDir(self,value):
        #self.tree.find(".//archiveDir").text = value
        self._setLXMLTreeNodeValue("archiveDir", value)
        self.tagsDict['archiveDir'] = value

    def getConfdir(self):
        return self.tagsDict['confdir']

    def setConfdir(self,value):
        #self.tree.find(".//confdir").text = value
        self._setLXMLTreeNodeValue("confdir", value)
        self.tagsDict['confdir'] = value


    def getResultDir(self):
        return self.tagsDict['resultDir']

    def setResultDir(self,value):
        #self.tree.find(".//resultDir").text = value
        self._setLXMLTreeNodeValue("resultDir", value)
        self.tagsDict['resultDir'] = value

    def getOaiDeleteDir(self):
        return self.tagsDict['oaiDeleteDir']

    def setOaiDeleteDir(self,value):
        #self.tree.find(".//resultDir").text = value
        self._setLXMLTreeNodeValue("oaiDeleteDir", value)
        self.tagsDict['oaiDeleteDir'] = value



    def getProcessLogDir(self):
        return self.tagsDict['processLogDir']

    def setProcessLogDir(self,value):
        #self.tree.find(".//processLogDir").text = value
        self._setLXMLTreeNodeValue("processLogDir", value)
        self.tagsDict['processLogDir'] = value


    def getErrorLogFile(self):
        return self.tagsDict['errorLogFile']

    def setErrorLogFile(self,value):
        #self.tree.find(".//errorLogFile").text = value
        self._setLXMLTreeNodeValue("errorLogFile", value)
        self.tagsDict['errorLogFile'] = value


    def getProcessLogFile(self):
        return self.tagsDict['processLogFile']

    def setProcessLogFile(self,value):
        #self.tree.find(".//processLogFile").text = value
        self._setLXMLTreeNodeValue("processLogFile", value)
        self.tagsDict['processLogFile'] = value


    def getMongoHosts(self):
        #return self.tagsDict['mongoHosts']
        return self.hostsDict

    def setMongoHosts(self,value):
        self.hostsDict = value


    #def getMongoHost(self):
    #    return self.tagsDict['mongoHost']

    #def setMongoHost(self,value):
    #    self.tree.find(".//mongoHost").text = value
    #    self.tagsDict['mongoHost'] = value

    #def getMongoPort(self):
    #    return self.tagsDict['mongoPort']

    #def setMongoPort(self,value):
    #    self.tree.find(".//mongoPort").text = value
    #    self.tagsDict['mongoPort'] = value

    #def getMongoCollection(self):
    #    return self.tagsDict['mongoCollection']

    #def setMongoCollection(self,value):
    #    self.tree.find(".//mongoCollection").text = value
    #    self.tagsDict['mongoCollection'] = value

    #def getMongoDB(self):
    #    return self.tagsDict['mongoDB']

    #def setMongoDB(self,value):
    #    self.tree.find(".//mongoDB").text = value
    #    self.tagsDict['mongoDB'] = value


    #We need this only for the rero repository
    def getSource(self):
        return self.tagsDict['source']

    def setSource(self,value):

        if not self.tagsDict['source'] is None:
            #self.tree.find(".//source").text = value
            self._setLXMLTreeNodeValue("source", value)
            self.tagsDict['source'] = value

    def getMongoCollectionSummary(self):
        return self.tagsDict['mongoCollectionSummary']

    def setMongoCollectionSummary(self,value):

        #self.tree.find(".//mongoCollectionSummary").text = value
        self._setLXMLTreeNodeValue("mongoCollectionSummary", value)
        self.tagsDict['mongoCollectionSummary'] = value

    def getPrefixSummaryFile(self):
        return self.tagsDict['prefixSummaryFile']

    def setPrefixSummaryFile(self,value):

        #self.tree.find(".//prefixSummaryFile").text = value
        self._setLXMLTreeNodeValue("prefixSummaryFile", value)
        self.tagsDict['prefixSummaryFile'] = value


    def getSummaryContentFile(self):
        if self.summaryFile is None:
            self.summaryFile = "".join([str(self.getPrefixSummaryFile()),
                                        "-",
                                        '{:%Y%m%d%H%M%S}'.format(datetime.now()),
                                       ".xml"])
        return  self.summaryFile




    def getSummaryContentFileSkipped(self):
        if self.summaryContentFileSkipped is None:
            self.summaryContentFileSkipped = "".join([str(self.getNetworkPrefix()),
                                        "-",
                                        '{:%Y%m%d%H%M%S}'.format(datetime.now()),
                                        "-skipped"
                                        ".txt"])
        return  self.summaryContentFileSkipped


    def getXMLasString(self):


        return  etree.tostring(self.tree.getroot())


    def getLastResumptionToken(self):
        return self.lastResumptionToken


    def setLastResumptionToken(self, resumptionToken):
        self.lastResumptionToken = resumptionToken


    def setApplicationDir (self, appDir):
        self.applicationDir  = appDir

    def getApplicationDir (self):
        return self.applicationDir



    def getConfigFilename (self):
        return self.configFileName


    def _setLXMLTreeNodeValue(self,nodeName, value):

        searchedNode = self.tree.find(".//" + nodeName)
        if not searchedNode is None:
            searchedNode.text = value




class HarvestingFilesConfigs(HarvestingConfigs):

    def __init__(self,filename):

        HarvestingConfigs.__init__(self,filename)

        self.validTagsNebis = [ 'basedirwebdav',
                                'incomingDir','fileNameSuffix',
                               'nebisSrcDir','clusteringDir',
                               'collectedDir','nebisWorking',
                               'reroWorking','reroSrcDir',
                               'fileProcessorType','storeLatestProc'
                               ]

        for tag in self.validTagsNebis:
            try:
                searchResult = self.tree.find(".//" + tag)
                if not searchResult is None:
                    self.tagsDict[tag] = self.tree.find(".//" + tag).text

                    if not self.tagsDict[tag] is None :
                        if re.search("\{basedir\}",self.tagsDict[tag]):
                            self.tagsDict[tag] =  re.sub("\{basedir\}",self.tagsDict['baseDir'],self.tagsDict[tag])
                        else:
                            if re.search("\{basedirwebdav\}",self.tagsDict[tag]):
                                self.tagsDict[tag] =  re.sub("\{basedirwebdav\}",self.tagsDict['basedirwebdav'],self.tagsDict[tag])


            except AttributeError as aErr:
                print (aErr)



    def getFileProcessorType(self):
        return self.tagsDict['fileProcessorType']

    def setFileProcessorType(self,value):
        #self.tree.find(".//fileProcessorType").text = value
        self._setLXMLTreeNodeValue("fileProcessorType", value)
        self.tagsDict['fileProcessorType'] = value




    def getReroWorkingDir(self):
        return self.tagsDict['reroWorking']

    def setReroWorkingDir(self,value):
        #self.tree.find(".//reroWorking").text = value
        self._setLXMLTreeNodeValue("reroWorking", value)
        self.tagsDict['reroWorking'] = value


    def getReroSrcDir(self):
        return self.tagsDict['reroSrcDir']

    def setReroSrcDir(self,value):
        #self.tree.find(".//reroSrcDir").text = value
        self._setLXMLTreeNodeValue("reroSrcDir", value)
        self.tagsDict['reroSrcDir'] = value



    def getIncomingDir(self):
        return self.tagsDict['incomingDir']

    def setIncomingDir(self,value):
        #self.tree.find(".//incomingDir").text = value
        self._setLXMLTreeNodeValue("incomingDir", value)
        self.tagsDict['incomingDir'] = value


    def getFileNameSuffix(self):
        return self.tagsDict['fileNameSuffix']

    def setFileNameSuffix(self,value):
        #self.tree.find(".//fileNameSuffix").text = value
        self._setLXMLTreeNodeValue("fileNameSuffix", value)
        self.tagsDict['fileNameSuffix'] = value


    def getNebisSrcDir(self):
        return self.tagsDict['nebisSrcDir']

    def setNebisSrcDir(self,value):
        #self.tree.find(".//nebisSrcDir").text = value
        self._setLXMLTreeNodeValue("nebisSrcDir", value)
        self.tagsDict['nebisSrcDir'] = value


    def getClusteringDir(self):
        return self.tagsDict['clusteringDir']

    def setClusteringDir(self,value):
        #self.tree.find(".//clusteringDir").text = value
        self._setLXMLTreeNodeValue("clusteringDir", value)
        self.tagsDict['clusteringDir'] = value

    def getCollectedDir(self):
        return self.tagsDict['collectedDir']

    def setCollectedDir(self,value):
        #self.tree.find(".//collectedDir").text = value
        self._setLXMLTreeNodeValue("collectedDir", value)
        self.tagsDict['collectedDir'] = value

    def getNebisWorking(self):
        return self.tagsDict['nebisWorking']

    def setNebisWorking(self,value):
        #self.tree.find(".//nebisWorking").text = value
        self._setLXMLTreeNodeValue("nebisWorking", value)
        self.tagsDict['nebisWorking'] = value

    def getStoreLatestProc(self):
        return self.tagsDict['storeLatestProc']

    def setStoreLatestProc(self,value):
        #self.tree.find(".//nebisWorking").text = value
        self._setLXMLTreeNodeValue("storeLatestProc", value)
        self.tagsDict['storeLatestProc'] = value



    def getBasedirwebdav(self):
        return self.tagsDict['basedirwebdav']

    def setBasedirwebdav(self,value):
        #self.tree.find(".//nebisWorking").text = value
        self._setLXMLTreeNodeValue("basedirwebdav", value)
        self.tagsDict['basedirwebdav'] = value




class HarvestingReadConfigs(HarvestingConfigs):

    def __init__(self,filename):

        HarvestingConfigs.__init__(self,filename)


        self.validTagsReadMongo = ['roottag','sourcePrefixMapping',
                                   'sourceOAIExtension']

        for tag in self.validTagsReadMongo:
            try:
                #we need the tags in validTagsReadMongo only for the export of multiple networks at the same time
                if not self.tree.find(".//" + tag) is None:
                    self.tagsDict[tag] = self.tree.find(".//" + tag).text

            except AttributeError as aErr:
                print (aErr)


    def getRoottag(self):
        return self.tagsDict['roottag']

    def setRoottag(self,value):
        #self.tree.find(".//roottag").text = value
        self._setLXMLTreeNodeValue("roottag", value)
        self.tagsDict['roottag'] = value

    def getSourcePrefixMapping(self):
        return self.tagsDict['sourcePrefixMapping']

    def setSourcePrefixMapping(self,value):
        #self.tree.find(".//roottag").text = value
        self._setLXMLTreeNodeValue("sourcePrefixMapping", value)
        self.tagsDict['sourcePrefixMapping'] = value

    def getSourceOAIExtension(self):
        return self.tagsDict['sourceOAIExtension']

    def setSourceOAIExtension(self,value):
        #self.tree.find(".//roottag").text = value
        self._setLXMLTreeNodeValue("sourceOAIExtension", value)
        self.tagsDict['sourceOAIExtension'] = value




