__author__ = 'swissbib'



import os
from argparse import ArgumentParser
from swissbibHarvestingConfigs import HarvestingReadConfigs
from Context import ApplicationContext
from swissbibMongoHarvesting import MongoDBHarvestingWrapper
import zlib


#Kurzdoku
#Aufruf
#deleteRecords.py --config=localStuff/config.sbudb6/config.readMongo.idsbb.xml --file=[file with IDS] --networkPrefix=IDSBB



class MongoDelete(MongoDBHarvestingWrapper):

    def __init__(self,applicationContext=None):
        MongoDBHarvestingWrapper.__init__(self,applicationContext=applicationContext)
        self.collection = self.dbConnections['nativeSources']['collections']['sourceDB']
        self.numbers = 0

    def deleteId(self, id):
        delete_query = { "_id": id}
        delete_result = self.collection.delete_one(delete_query)
        print(delete_result)


    def readId(self, id):
        document = self.collection.find_one({"_id": id})
        if document:
            self.numbers += 1
            print (zlib.decompress(document["record"]))



if __name__ == '__main__':

    oParser = None
    args = None
    sConfigs = None
    deleteMongo = None


    try:

        oParser = ArgumentParser()
        oParser.add_argument("-c", "--config", dest="confFile", required=True)
        oParser.add_argument("-f", "--file", dest="fileWithIds", required=True)
        oParser.add_argument("-p", "--networkPrefix", dest="prefix", required=True)

        args = oParser.parse_args()
        sConfigs = HarvestingReadConfigs(args.confFile)
        sConfigs.setApplicationDir(os.getcwd())

        appContext = ApplicationContext()
        appContext.setConfiguration(sConfigs)

        deleteMongo = MongoDelete(appContext)

        idFile = open(args.fileWithIds,"r")
        for line in idFile:
            deleteMongo.deleteId("".join(['(',args.prefix,')',line]).strip('\n'))
            #deleteMongo.readId("".join(['(', args.prefix, ')', line]).strip('\n'))



    except Exception as pythonBaseException:
        print str(pythonBaseException)

    finally:
        if not deleteMongo is None:
            deleteMongo.closeResources()
            print("records found: " + str(deleteMongo.numbers))
