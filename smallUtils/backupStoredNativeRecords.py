

__author__ = 'swissbib'

import os
from argparse import ArgumentParser
from swissbibHarvestingConfigs import HarvestingReadConfigs
from swissbibMongoHarvesting import MongoDBHarvestingWrapperAdmin
from Context import ApplicationContext



oParser = None
args = None
sConfigs = None
cwd = None
mongoWrapper = None


try:

    oParser = ArgumentParser()
    oParser.add_argument("-c", "--config", dest="confFile")
    oParser.add_argument("-s", "--size", dest="fileSize")
    oParser.add_argument("-o", "--outDir", dest="outDir")


    args = oParser.parse_args()
    sConfigs = HarvestingReadConfigs(args.confFile)
    sConfigs.setApplicationDir(os.getcwd())

    appContext = ApplicationContext()
    appContext.setConfiguration(sConfigs)
    backupWrapper = MongoDBHarvestingWrapperAdmin(appContext)


    backupWrapper.writeBackupRecords(fileSize=args.fileSize,  outDir=args.outDir)

    backupWrapper.closeResources()

except Exception as pythonBaseException:
    print str(pythonBaseException)

finally:

    print "writeBackupRecords has finshed - look for possible errors"





