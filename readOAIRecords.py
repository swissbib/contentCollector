__author__ = 'swissbib'



import os
from argparse import ArgumentParser
from swissbibHarvestingConfigs import HarvestingReadConfigs
from swissbibMongoHarvesting import MongoDBHarvestingWrapperAdmin
from Context import ApplicationContext
import re



#call: --config=config/read/config.readMongo.nebis.xml --id= [--number=10]

#Beipiel Aufruf
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.abn.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/abn &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.alex.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/alex &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.bgr.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/bgr &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.idsbb.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/idsbb &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.nebis.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/nebis &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.idslu.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/idslu &

#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.idssg1.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/idssg1 &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.idssg2.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/idssg2 &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.idsuzh.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/idsuzh &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.posters.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/posters &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.rero.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/rero &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.retros.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/retros &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.sbt.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/sbt &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.sgbn.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/sgbn &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.snl.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/snl &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.zora.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/zora &
#pythonmongo  readOAIRecords.py  --config=config.read/config.readMongo.gnd.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/dnbgnd &


#example read with condition
#pythonmongo readOAIRecords.py  --config=config.read/config.readMongo.rero.xml  --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/rerodeleted --condition='status:newdeleted'


#example fix records
#pythonmongo fixRecords.py --config=config.read/config.readMongo.rero.xml

#example
#--config=config.read/config.readMongo.nebis.xml --id=(NEBIS)aleph-publish:003065805



oParser = None
args = None
sConfigs = None
mongoWrapper = None


try:

    oParser = ArgumentParser()
    oParser.add_argument("-c", "--config", dest="confFile")
    oParser.add_argument("-i", "--id", dest="idToRead",default=None)
    oParser.add_argument("-n", "--number", dest="countToRead",default=None)
    oParser.add_argument("-s", "--size", dest="fileSize",default=None)
    oParser.add_argument("-o", "--outDir", dest="outDir",default=None)
    oParser.add_argument("-k", "--condition", dest="condition", default=None)
    oParser.add_argument("-f", "--inputFile", dest="inputFile", default=None)




    args = oParser.parse_args()
    sConfigs = HarvestingReadConfigs(args.confFile)
    sConfigs.setApplicationDir(os.getcwd())

    appContext = ApplicationContext()

    appContext.setConfiguration(sConfigs)


    readWrapper = MongoDBHarvestingWrapperAdmin(appContext)


    readWrapper.readRecords(rId=args.idToRead,countToRead=args.countToRead,
                                fileSize=args.fileSize, outDir=args.outDir,condition=args.condition,
                                inputFile=args.inputFile,

                            )


except Exception as pythonBaseException:
    print str(pythonBaseException)

finally:
    print "process readOAIRecords has finished - look for possible errors"
