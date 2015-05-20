__author__ = 'swissbib'



import os
from argparse import ArgumentParser
from swissbibHarvestingConfigs import HarvestingReadConfigs
from swissbibMongoHarvesting import MongoDBHarvestingWrapperAdmin, MongoDBHarvestingWrapperSearch502
from Context import ApplicationContext





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




    args = oParser.parse_args()
    sConfigs = HarvestingReadConfigs(args.confFile)
    sConfigs.setApplicationDir(os.getcwd())

    appContext = ApplicationContext()

    appContext.setConfiguration(sConfigs)


    search502Wrapper = MongoDBHarvestingWrapperSearch502(applicationContext=appContext)


    search502Wrapper.read502Records(outDir=args.outDir,fileSize=args.fileSize)



except Exception as pythonBaseException:
    print str(pythonBaseException)

finally:
    print "process fixRecords has finished - look for possible errors"
