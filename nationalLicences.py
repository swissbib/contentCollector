# -*- coding: utf-8 -*-

from swissbibMongoHarvesting import MongoDBHarvestingWrapper
from swissbibHarvestingConfigs import HarvestingFilesConfigs
from argparse import ArgumentParser
from Context import ApplicationContext
from swissbibUtilities import ResultCollector, SwissbibUtilities
import os
from datetime import datetime, timedelta
from harvestingTasks import PersistNLMongo
from FileProcessorImpl import FileProcessor, SingleImportFileProvider

import re
import glob




class NLFileProvider(SingleImportFileProvider):

    def __init__(self,context):
        SingleImportFileProvider.__init__(self,context)


    def createGenerator(self):
        yield "here I am!"


class NationalLicencesProcessor(FileProcessor):

    def process(self):

        nlFileProvider = NLFileProvider(self.context)
        self._processFileContent(nlFileProvider)


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

        appContext = ApplicationContext()
        appContext.setConfiguration(sConfigs)
        appContext.setResultCollector(rCollector)
        mongoWrapper = MongoDBHarvestingWrapper(applicationContext=appContext)

        appContext.setMongoWrapper(mongoWrapper)

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
