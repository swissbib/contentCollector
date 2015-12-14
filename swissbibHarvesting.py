from datetime import datetime
import os

from urllib2 import HTTPError, URLError
from oaipmh.error import NoRecordsMatchError, ErrorBase, BadVerbError
from argparse import ArgumentParser

from swissbibHarvestingConfigs import HarvestingConfigs
from swissbibOAIClient import SwissbibOAIClient,ReadError
from swissbibUtilities import SwissBibMetaDataRegistry, ErrorHashProcesing, ResultCollector, SwissbibUtilities

from swissbibMongoHarvesting import MongoDBHarvestingWrapper

from Context import ApplicationContext, HarvestingWriteContext







__author__ = 'swissbib'

oParser = None
args = None
sConfigs = None
cwd = None
startTime = None
sU = None
#nextTimestampUTC = None
rCollector = None
fromDate = None
resumptionToken = None
untilDate = None
mongoWrapper = None
registry = None
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

    #nextTimestampUTC =  sU.getNextTimestamp(sConfigs)
    rCollector = ResultCollector()




    if not sConfigs.getResumptionToken() is None:
        resumptionToken = sConfigs.getResumptionToken()
    else:
        fromDate = sU.getFromFormat(sConfigs.getTimestampUTC(),sConfigs)
        if  not sConfigs.getManualUntil() is None:
            untilDate = sU.getUntilDate(sConfigs.getManualUntil(),sConfigs)


    appContext = ApplicationContext()
    appContext.setResultCollector(rCollector)
    appContext.setConfiguration(sConfigs)


    mongoWrapper = MongoDBHarvestingWrapper(applicationContext=appContext)

    appContext.setMongoWrapper(mongoWrapper)


    #registry = SwissBibMetaDataRegistry(sConfigs,mongoWrapper,rCollector)
    registry = SwissBibMetaDataRegistry()

    writeContext = HarvestingWriteContext(appContext)

    #Todo: SwissbibUtilities sollten Teil des Contexts werden??

    appContext.setWriteContext(writeContext)

    client = SwissbibOAIClient(base_url=sConfigs.getUrl(),
                               metadata_registry=registry,
                               applicationContext=appContext,
                               dayGranularity=sU.isDayGranularity(sConfigs)
                                )

    # from_ und until_ mit Unterstrich da das Datumsformat aufgrund der granularity spaeter nochmals formatiert wird
    #sind die anderen Parameter None, wird der vor Aufruf des ersten requests gegen das repository aus der parameterliste
    #entfernt -> s. Dazu swissbibOAIClient.SwissbibOAIClient.handleVerb
    #diese Methode musste sowieso wegen des speziellen rero source parameters ueberschrieben werden
    if resumptionToken is None:
        recs = client.listRecords(metadataPrefix= sConfigs.getMetadataPrefix(),
            from_= fromDate, until_=untilDate ,source= sConfigs.getSource(),
            set= sConfigs.getSetSpec())
    else:
        recs = client.listRecords(resumptionToken = resumptionToken)



    for rec in recs:

        #if sConfigs.getWriteHarvestedFiles() is None or  (sConfigs.getWriteHarvestedFiles() is not None and sConfigs.getWriteHarvestedFiles()):
        #nextfile = open("".join([sConfigs.getDumpDir(),os.sep, sConfigs.getSummaryContentFile()]),"a" )
        #nextfile.write(rec)
        #nextfile.close()
        writeContext.flushContent()

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
        writeContext.setAndWriteConfigAfterSuccess()


        usedOAIParameters = ""
        if not  appContext.getResultCollector().getHarvestingParameter() is None:
            usedOAIParameters = '\n'.join(['%s:: %s' % (key, value) for (key, value) in appContext.getResultCollector().getHarvestingParameter().items()])

            procMess = ["start time: ",  str( startTime) , "used OAI Parameters: ",
                        usedOAIParameters,  "end time: " + str(datetime.now()),
                        "outputfile: " + appContext.getConfiguration().getSummaryContentFile(),
                        "logged skipped records (if true): " + appContext.getConfiguration().getSummaryContentFileSkipped(),
                        "records deleted: " + str(appContext.getResultCollector().getRecordsDeleted()),
                        "records skipped " + str(appContext.getResultCollector().getRecordsSkipped()),
                        "records parse error: " + str(appContext.getResultCollector().getRecordsparseError()),
                        "records to cbs inserted: " + str(appContext.getResultCollector().getRecordsToCBSInserted()),
                        "records to cbs updated: " + str(appContext.getResultCollector().getRecordsToCBSUpdated()),
                        "records to cbs (without skip mechanism - configuration!): " + str(appContext.getResultCollector().getRecordsToCBSNoSkip()),
                        "\n"]

            if not appContext.getConfiguration() is None:
                procMess = SwissbibUtilities.addBlockedMessageToLogSummary(procMess,appContext.getConfiguration())


            writeContext.writeLog(header="oai harvesting summary",message=procMess )

        else:
            procMess = ["ResultCollector was None - Why?"]
            if not appContext.getConfiguration() is None:
                procMess = SwissbibUtilities.addBlockedMessageToLogSummary(procMess,appContext.getConfiguration())
            writeContext.writeErrorLog(message= "\n".join(procMess))
            writeContext.writeLog(message= "\n".join(procMess))

    #At the moment I don't want to use the advanced Harvesting Functionality like
    # - analyze Hash so records with no interest for the import process will be skipped
    # -> then I can deactivate the Mongo charged with storing this content. To deactivate the instance the storing of Summary results has to be skipped too because it uses the same process
    #mongoWrapper.storeResultOfProcessing(rCollector,sConfigs)


if not mongoWrapper is None:
    mongoWrapper.closeResources()

os.chdir(appContext.getConfiguration().getApplicationDir())


