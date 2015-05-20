
__author__ = 'swissbib'

import re
from swissbibHarvestingConfigs import HarvestingConfigs
from swissbibMongoHarvesting import MongoDBHarvestingWrapper
from argparse import ArgumentParser
from harvestingTasks import PersistRecordMongo, PersistInitialDNBGNDRecordMongo
from Context import StoreNativeRecordContext, TaskContext

from swissbibUtilities import ResultCollector

from swissbibMongoHarvesting import MongoDBHarvestingWrapper

from Context import ApplicationContext










if __name__ == '__main__':
    #gndInput =  open("testdata/Tngesamt1210_1mrc21.xml","r" )

    #url reqest Beipiel
    #http://services.dnb.de/oai/repository?set=authorities&verb=ListRecords&from=2012-12-01&metadataPrefix=MARC21-xml
    #Beispiel fuer einen record mit GNDS (docid: 020425325)
    #Beispiel OAI GetRecord
    #http://services.dnb.de/oai/repository?verb=GetRecord&metadataPrefix=MARC21-xml&identifier=oai:d-nb.de/authorities/000158976
    oParser = ArgumentParser()
    oParser.add_argument("-c", "--config", dest="confFile")
    oParser.add_argument("-i", "--input", dest="inputFile")
    args = oParser.parse_args()

    sConfigs = HarvestingConfigs(args.confFile)

    inputFile = args.inputFile

    rCollector = ResultCollector()
    appContext = ApplicationContext()
    appContext.setResultCollector(rCollector)
    appContext.setConfiguration(sConfigs)


    mongoWrapper = MongoDBHarvestingWrapper(applicationContext=appContext)

    appContext.setMongoWrapper(mongoWrapper)


    recordLines = []
    start = False
    for line in open(inputFile,"r"):
        if line.find('<record') != -1:
            recordLines.append(line)
            start = True
        elif start == True and line.find('</record>') == -1:
            recordLines.append(line)
        elif start == True and line.find('</record') != -1:
            recordLines.append(line)
            #print "".join(recordLines)
            record = "".join(recordLines)
            #<controlfield tag="001">100031048</controlfield>
            idPattern = re.compile('<controlfield tag="001">(.*?)</controlfield>',re.UNICODE | re.DOTALL | re.IGNORECASE)
            idT = idPattern.search(record)
            if idT:
                recordId = "oai:dnb.de/authorities/" + idT.group(1)

                if re.search("status=\"deleted\"",record,re.UNICODE | re.DOTALL):
                    recordDeleted = True
                else:
                    recordDeleted = False

                for taskName,task  in  sConfigs.getDedicatedTasks().items():


                    if isinstance(task,PersistRecordMongo) or isinstance(task,PersistInitialDNBGNDRecordMongo):
                        taskContext = StoreNativeRecordContext(appContext=appContext,
                                                                rID=recordId,singleRecord=record,
                                                                deleted=recordDeleted)
                    else:
                        taskContext = TaskContext(appContext=appContext)

                    task.processRecord(taskContext)


            #cGNDContent = CollectGNDContent()
            #xml.sax.parseString("".join(recordLines), cGNDContent)

            #result = cGNDContent.getSelectedValues()
            #print "".join(recordLines)
            #parser =  make_parser()
            #parser.setContentHandler(CollectGNDContent())
            #parser.parseString ("".join(recordLines))

            start = False
            recordLines = []

    mongoWrapper.closeResources()



