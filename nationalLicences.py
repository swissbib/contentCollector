# -*- coding: utf-8 -*-

import os
import uuid

from swissbibMongoHarvesting import MongoDBHarvestingWrapper
from swissbibHarvestingConfigs import HarvestingFilesConfigs
from argparse import ArgumentParser
from Context import ApplicationContext, NLApplicationContext
from swissbibUtilities import ResultCollector, SwissbibUtilities
from datetime import datetime, timedelta
from harvestingTasks import PersistNLMongo
from FileProcessorImpl import FileProcessor, SingleImportFileProvider,FileWebdavWriteContext
from harvestingTasks import PersistRecordMongo, PersistNLMongo, WriteModsForCBS
from Context import TaskContext, StoreNativeRecordContext, StoreNativeNLRecordContext
from lxml import etree

import re
import StringIO



class NLFileProvider(SingleImportFileProvider):

    def __init__(self,context):
        SingleImportFileProvider.__init__(self,context)

    def getFileContent(self, path, filename):
        fileHandle =  open("".join([path,'/',filename]),"r")
        content = fileHandle.read()
        return content


    def createGenerator(self):
        processedDataDir = self.context.getConfiguration().getNlProcessedDataDir()

        for root, dirs, files in os.walk(processedDataDir):
            for file in files:
                if file.lower().endswith('.xml') or file.lower().endswith('.xml.meta'):
                    yield [self.getFileContent(root, file), root+'/'+file]



class NationalLicencesProcessor(FileProcessor):


    def __init__(self,context):

        FileProcessor.__init__(self,context)


    def _getRecordIdFromMods(self, modsRecord):
        recordTree = etree.fromstring(modsRecord)

        # Get id from XML
        xpathGetIdentifier = "//ns:identifier[@type='swissbib']"
        result = recordTree.xpath(xpathGetIdentifier, namespaces={'ns': 'http://www.loc.gov/mods/v3'})



        if len(result) > 0:
            id = result[0].text
        else:  # almost never the case, but just to make sure
            id = str(uuid.uuid4())

        return id

    def _getModsStructure(self, sourceRecord, filename):

        f = StringIO.StringIO(sourceRecord)
        xml = etree.parse(f)

        plain_string_filename = etree.XSLT.strparam(filename)

        #filename is passed as a stylesheet parameter
        mods = self.context.getModsTransformation()(xml, filename=plain_string_filename)
        return etree.tostring(mods)


    def lookUpContent(self):
        #lookup raw content deliverd by publisher
        #FTP lookup ? not done by now
        #actually we have to put the raw content manually at the rightt place
        pass


    def preProcessContent(self):
        pass
        #start xslt transformation process created by Lionel
        #launch shell scripts (lionel)


    def initialize(self):
        pass
        #do we have to do some kind of initialization
        #e.g. creation or deletion of directories??

    def postProcessContent(self):
        pass
        #move the collected content (which should be aggregated into one single file)
        #into the proper directory for CBS
        #perhaps we can use at least part of the implementations available for other pipes


    def process(self):

        nlFileProvider = NLFileProvider(self.context)

        try:

            for recordAndFilename in nlFileProvider.createGenerator():
                contentSingleRecord = recordAndFilename[0]
                filename = recordAndFilename[1]

                try:

                    mods = self._getModsStructure(contentSingleRecord, filename)
                    recordId = self._getRecordIdFromMods(mods)
                    #print contentSingleRecord
                    for taskName, task in self.context.getConfiguration().getDedicatedTasks().items():
                        #write record into file which is going to be sent to CBS later
                        #open question: what do we do with DTD?
                        try:
                            #do we have to do any additional validation of the record?
                            if isinstance(task, PersistNLMongo) or isinstance(task, WriteModsForCBS) :
                                #extract id from swissbib-jats
                                #extract year from swissbib-jats (pyear, eyear or others)



                                taskContext = StoreNativeNLRecordContext(appContext=self.context,
                                                                       rID=recordId,  jatsRecord=contentSingleRecord,
                                                                       deleted=False,modsRecord=mods)
                            else:
                                taskContext = TaskContext(appContext=self.context)
                            task.processRecord(taskContext)
                        except Exception as pythonBaseException:

                            #write Exception into log
                            continue
                except Exception as BaseException:
                    #make some kind of error handling
                    continue
        except Exception as processExcepion:
            print processExcepion

if __name__ == '__main__':



    __author__ = 'swissbib - UB Basel, Switzerland, Guenter Hipler'
    __copyright__ = "Copyright 2016, swissbib project"
    __license__ = "??"
    __version__ = "0.1"
    __maintainer__ = "Guenter Hipler"
    __email__ = "guenter.hipler@unibas.ch"
    __status__ = "in development"
    __description__ = """
                        """


    oParser = None
    args = None
    sConfigs = None
    mongoWrapper = None
    rCollector = None
    startTime = None
    nebisClient = None
    appContext = None

    try:


        #print sys.version_info
        oParser = ArgumentParser()
        oParser.add_argument("-c", "--config", dest="confFile")
        args = oParser.parse_args()


        sConfigs = HarvestingFilesConfigs(args.confFile)
        sConfigs.setApplicationDir(os.getcwd())


        rCollector = ResultCollector()

        startTime = datetime.now()

        appContext = NLApplicationContext()
        appContext.setConfiguration(sConfigs)
        appContext.setResultCollector(rCollector)
        data = open(sConfigs.getJats2modsxsl(),'r')
        xslt_content = data.read()
        data.close()
        xslt_root = etree.XML(xslt_content)
        transform = etree.XSLT(xslt_root)
        appContext.setModsTransformation(transform)

        mongoWrapper = MongoDBHarvestingWrapper(applicationContext=appContext)

        appContext.setMongoWrapper(mongoWrapper)

        aggregatonFile = "".join([str(appContext.getConfiguration().getPrefixSummaryFile()),'-','{:%Y%m%d%H%M%S}'.format(datetime.now()), "-", 'nl.all.xml'])
        wC = FileWebdavWriteContext(appContext)
        appContext.setWriteContext(wC)

        wC.setOutFileName(aggregatonFile)

        client = globals()[sConfigs.getFileProcessorType()](appContext)

        client.initialize()
        client.lookUpContent()

        client.preProcessContent()
        client.process()
        client.postProcessContent()


    except Exception as exception:

        if  not appContext is None and  not appContext.getWriteContext() is None:
            procMess=["Exception in FileProcessorImpl.py"]

            if not appContext.getConfiguration() is None:
                procMess = SwissbibUtilities.addBlockedMessageToLogSummary(procMess,appContext.getConfiguration())

            appContext.getWriteContext().handleOperationAfterError(exType=exception,
                                                        message="\n".join(procMess) )
        elif not appContext is None and  not appContext.getConfiguration() is None:

            logfile = open(appContext.getConfiguration().getErrorLogDir() + os.sep + appContext.getConfiguration().getErrorLogFile(),"a")
            message = ["no WriteContext after Error: Exception Handler",
                       str(exception)]
            message = SwissbibUtilities.addBlockedMessageToLogSummary(message,appContext.getConfiguration())
            logfile.write("\n".join(message))
            logfile.flush()
            logfile.close()
        else:

            print "no WriteContext after Error and Configuration is None: Exception Handler"
            print str(exception) + "\n"



    else:

        if not appContext.getWriteContext() is None:

            appContext.getWriteContext().setAndWriteConfigAfterSuccess()



            procMess = ["start time: " +  str( startTime),
                        "end time: " + str(datetime.now()),
                        "Nebis file(s) processed: " + "##".join(rCollector.getProcessedFile()),
                        "logged skipped records (if true): " + sConfigs.getSummaryContentFileSkipped(),
                        "records deleted: " + str(rCollector.getRecordsDeleted()) ,
                        "records skipped: " + str(rCollector.getRecordsSkipped()) ,
                        "records parse error: " + str(rCollector.getRecordsparseError()) ,
                        "records to cbs inserted: " + str(rCollector.getRecordsToCBSInserted()) ,
                        "records to cbs updated: " + str(rCollector.getRecordsToCBSUpdated()) ,
                        "records to cbs (without skip mechanism - configuration!): " + str(rCollector.getRecordsToCBSNoSkip()),
                        "\n"]
            if not appContext.getConfiguration() is None:
                procMess = SwissbibUtilities.addBlockedMessageToLogSummary(procMess,appContext.getConfiguration())


            appContext.getWriteContext().writeLog(header="Import file (push or webdav) summary",message=procMess )

        elif not appContext is None and  not appContext.getConfiguration() is None:


            procMess = ["WriteContext is None - after process finished regularly",
            "start time: " +  str( startTime),
            "end time: " + str(datetime.now()),
            "Nebis file(s) processed: " + "##".join(rCollector.getProcessedFile()),
            "logged skipped records (if true): " + sConfigs.getSummaryContentFileSkipped(),
            "records deleted: " + str(rCollector.getRecordsDeleted()) ,
            "records skipped: " + str(rCollector.getRecordsSkipped()) ,
            "records parse error: " + str(rCollector.getRecordsparseError()) ,
            "records to cbs inserted: " + str(rCollector.getRecordsToCBSInserted()) ,
            "records to cbs updated: " + str(rCollector.getRecordsToCBSUpdated()) ,
            "records to cbs (without skip mechanism - configuration!): " + str(rCollector.getRecordsToCBSNoSkip()),
            "\n"]
            if not appContext.getConfiguration() is None:
                procMess = SwissbibUtilities.addBlockedMessageToLogSummary(procMess,appContext.getConfiguration())

            logfile = open(appContext.getConfiguration().getProcessLogDir() + os.sep + appContext.getConfiguration().getProcessLogFile(),"a")
            logfile.write("\n".join(procMess))
            logfile.flush()
            logfile.close()

        else:
            procMess = ["WriteContext is None and Configuration is None after process finished regularly",
            "going cto use logfile channel directly",
            "start time: " +  str( startTime),
            "end time: " + str(datetime.now()),
            "Nebis file(s) processed: " + "##".join(rCollector.getProcessedFile()),
            "logged skipped records (if true): " + sConfigs.getSummaryContentFileSkipped(),
            "records deleted: " + str(rCollector.getRecordsDeleted()) ,
            "records skipped: " + str(rCollector.getRecordsSkipped()) ,
            "records parse error: " + str(rCollector.getRecordsparseError()) ,
            "records to cbs inserted: " + str(rCollector.getRecordsToCBSInserted()) ,
            "records to cbs updated: " + str(rCollector.getRecordsToCBSUpdated()) ,
            "records to cbs (without skip mechanism - configuration!): " + str(rCollector.getRecordsToCBSNoSkip()),
            "\n"]

            print "\n".join(procMess)


            #appContext.getWriteContext().writeErrorLog(message= "ResultCollector was None - Why?")
            #appContext.getWriteContext().writeLog(message= "ResultCollector was None - Why?")


    if not mongoWrapper is None:
        mongoWrapper.closeResources()
