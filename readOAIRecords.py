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

#new: 2013-09-11
#pythonmongo readOAIRecords.py --config=config.read/config.readMongo.idsbb.xml --condition='$gt#2013-08-05' --size=1000 --outDir=/var/swissbib/mongo/exportlocaldbs/idsbb
#pythonmongo readOAIRecords.py --config=config.read/config.readMongo.idsbb.xml  --number=2000 --condition='year#$lte#2013-08-05' --size=2 --outDir=/var/swissbib/mongo/exportlocaldbs/idsbb


#example fix records
#pythonmongo fixRecords.py --config=config.read/config.readMongo.rero.xml

#example
#--config=config.read/config.readMongo.nebis.xml --id=(NEBIS)aleph-publish:003065805



oParser = None
args = None
sConfigs = None
readWrapper = None


try:

    oParser = ArgumentParser()
    oParser.add_argument("-c", "--config", dest="confFile")
    oParser.add_argument("-i", "--id", dest="idToRead",default=None)
    oParser.add_argument("-n", "--number", dest="countToRead",default=None)
    oParser.add_argument("-s", "--size", dest="fileSize",default=None)
    oParser.add_argument("-o", "--outDir", dest="outDir",default=None)
    oParser.add_argument("-k", "--condition", dest="condition", default=None)
    oParser.add_argument("-f", "--inputFile", dest="inputFile", default=None)
    oParser.add_argument("-t", "--timestamp", dest="userDatestamp", default=None)
    oParser.add_argument("-r", "--readTimestamps", dest="queriedTimeStamps", default=None)
    oParser.add_argument("-d", "--docRecordField", dest="docRecordField", default=None );


    args = oParser.parse_args()
    sConfigs = HarvestingReadConfigs(args.confFile)
    sConfigs.setApplicationDir(os.getcwd())

    appContext = ApplicationContext()

    appContext.setConfiguration(sConfigs)


    readWrapper = MongoDBHarvestingWrapperAdmin(appContext)

    if not args.queriedTimeStamps is None:

        outDir =  args.outDir if not args.outDir is None else "/var/swissbib/mongo/exportlocaldbs"
        #we expect something like this
        #--readTimeStamps=2016-02-01T22:03:17Z###2016-02-02T22:03:17Z
        searchedTimestamps = args.queriedTimeStamps
        countToRead = 100000 if args.countToRead == None else args.countToRead
        if searchedTimestamps.find('###') != -1:
            dateParts = searchedTimestamps.split("###")
            #start and end is available
            readWrapper.readRecordsWithTimeStamp(startDate=dateParts[0],endDate=dateParts[1],
                                                 outDir=outDir, fileSize=args.fileSize,
                                                 countToRead=countToRead)
        elif searchedTimestamps.find('#') != -1:
            #only one timestamp - should be either start or end
            dateParts = searchedTimestamps.split("#")
            #we expect two parts index[0] should be either start or end
            if dateParts[0].lower() == "start":
                readWrapper.readRecordsWithTimeStamp(startDate=dateParts[1], endDate=None,
                                                     outDir=outDir, fileSize=args.fileSize,
                                                     countToRead=countToRead)
            elif dateParts[0].lower() == "end":
                readWrapper.readRecordsWithTimeStamp(startDate=None, endDate=dateParts[1],
                                                     outDir=outDir, fileSize=args.fileSize,
                                                     countToRead=countToRead)
        else:
            print "no date parameters are matching as start and/or end date - nothing is done"



    else:
        readWrapper.readRecords(rId=args.idToRead,countToRead=args.countToRead,
                                    fileSize=args.fileSize, outDir=args.outDir,condition=args.condition,
                                    inputFile=args.inputFile,
                                    userDatestamp=args.userDatestamp,
                                    docRecordField=args.docRecordField
                                )


except Exception as pythonBaseException:
    print str(pythonBaseException)

finally:
    if not readWrapper is None:
        readWrapper.closeResources()
    #print "process readOAIRecords has finished - look for possible errors"
