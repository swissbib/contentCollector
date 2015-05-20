#!/bin/bash


BASE_DIR=/var/swissbib/mongo
#BASE_DIR=/home/swissbib/temp/testBackupMongo

MONGODB_BASEDIR=/usr/local/swissbib/mongodb

DUMP_DIR=$BASE_DIR/dump
#DUMP_NAS=/var/swissbib/dbbu/mongo/dump
#DUMP_NAS=/var/swissbib/dbbu/mongo
LOG_DIR=$BASE_DIR/scriptlog
CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
LOGFILE=$LOG_DIR/backup.$CURRENT_TIMESTAMP.log

CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
#DBPATH=/home/swissbib/environment/data/mongo/db
DBPATH=/var/swissbib/mongo/localdbs

function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



function initialize()
{
    printf "clear dump dir ....\n\n" >> $LOGFILE 2>&1

    if [ ! -d "$DUMP_DIR" ]; then
        mkdir -p $DUMP_DIR

    fi

    if [ "$(ls -A $DUMP_DIR)" ]; then
#     setTimestamp
     printf "Start deleting previous DB dump at $CURRENT_TIMESTAMP\n\n" >> $LOGFILE 2>&1
     rm -rf $DUMP_DIR/*
#     setTimestamp
#     printf "Finished deleting previous DB dump at $CURRENT_TIMESTAMP\n\n" >> $LOGFILE 2>&1
    fi
}





#if [ "$UID" -eq 0   ]; then


    printf "start mongodump at: $CURRENT_TIMESTAMP ...\n\n" >> $LOGFILE

    initialize

    $MONGODB_BASEDIR/bin/stop.mongo.sh >> $LOGFILE 2>&1
    #stop.mongo.sh >> $LOGFILE 2>&1


    printf "mongod instance on port 29017 is now down....\n\n" >> $LOGFILE

    #mongodump --dbpath $DBPATH --out $DUMP_DIR/localdbs >> $LOGFILE 2>&1
    mongodump --dbpath $DBPATH --out $DUMP_DIR >> $LOGFILE 2>&1


    #initialize

    #su -c "mongodump --dbpath $BASE_DIR/localdbs --out $DUMP_DIR/localdbs" swissbib >> $LOGFILE 2>&1

    setTimestamp
    printf "dump of localdbs has been finished succesfully at $CURRENT_TIMESTAMP ....\n\n" >> $LOGFILE

    printf "now going to restart mongod instance on port 29017 ....\n\n" >> $LOGFILE

    $MONGODB_BASEDIR/bin/start.mongo.sh >> $LOGFILE 2>&1
    #start.mongo.sh >> $LOGFILE 2>&1

    printf "mongod instance on port 29017 is again up and running - Congratulations....\n\n" >> $LOGFILE

    printf "Copying dump to NAS using a dedicated python script.\n\n" >> $LOGFILE

    cd $BASE_DIR/bin
    python $BASE_DIR/bin/copyDumpedMongoCollections.py >> $LOGFILE
    #rsync -aq --delete $DUMP_DIR/localdbs $DUMP_NAS >> $LOGFILE 2>&1

    setTimestamp
    printf "All done at $CURRENT_TIMESTAMP !\n\n" >> $LOGFILE
    gzip $LOGFILE

#else
#    echo "you have to be root to start this script ...\n"
#    exit 1
#fi



