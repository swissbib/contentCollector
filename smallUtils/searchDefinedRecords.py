__author__ = 'swissbib'



import os
from argparse import ArgumentParser
from swissbibHarvestingConfigs import HarvestingReadConfigs
from swissbibMongoHarvesting import MongoDBHarvestingWrapperAdmin, MongoDBHarvestingWrapperSearchDefinedGeneric
from Context import ApplicationContext
import re





#pythonmongo  search502Records.py --config=config.read/config.readMongo.nebis.xml --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/nebis502

oParser = None
args = None
sConfigs = None
mongoWrapper = None


try:



    oParser = ArgumentParser()
    oParser.add_argument("-c", "--config", dest="confFile")
    oParser.add_argument("-s", "--size", dest="fileSize",default=None)
    oParser.add_argument("-o", "--outDir", dest="outDir",default=None)
    oParser.add_argument("-r", "--regex", dest="regex",default=None)





    args = oParser.parse_args()
    sConfigs = HarvestingReadConfigs(args.confFile)
    sConfigs.setApplicationDir(os.getcwd())

    appContext = ApplicationContext()

    appContext.setConfiguration(sConfigs)


    searchDefinedGeneric = MongoDBHarvestingWrapperSearchDefinedGeneric(applicationContext=appContext)

    #regex = "<datafield tag=\"909\".*?zbzmix.*?</datafield>"
    #print args.regex

    searchDefinedGeneric.setRegEx(args.regex)

    searchDefinedGeneric.readMatchingRecords(outDir=args.outDir,fileSize=args.fileSize)



except Exception as pythonBaseException:
    print str(pythonBaseException)

finally:
    print "process fixRecords has finished - look for possible errors"
