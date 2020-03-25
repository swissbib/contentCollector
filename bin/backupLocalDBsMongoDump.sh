#!/bin/bash


BASEDIR=/swissbib_index

MONGODB_BASEDIR=$BASEDIR/mongo

SB_BASEDIR=$MONGODB_BASEDIR/scripts


DUMP_DIR=$MONGODB_BASEDIR/dump
#DUMP_NAS=/var/swissbib/dbbu/mongo/dump
#DUMP_NAS=/var/swissbib/dbbu/mongo
LOG_DIR=$SB_BASEDIR/scriptlog
CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
LOGFILE=$LOG_DIR/backup.$CURRENT_TIMESTAMP.log

CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
#DBPATH=/home/swissbib/environment/data/mongo/db
DBPATH=$MONGODB_BASEDIR/localdbs

# Alle Mongohosts brauchen das Passwort des DB admin-users im Klartext mod 600 swissbib hier:

if [ -f $MONGODB_BASEDIR/pw ]; then

setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



initialize()
{
    printf "clear dump dir ....\n\n" >> $LOGFILE 2>&1

    if [ ! -d "$DUMP_DIR" ]; then
        mkdir -p $DUMP_DIR

    fi

    if [ "$(ls -A $DUMP_DIR)" ]; then
     printf "Start deleting previous DB dump at $CURRENT_TIMESTAMP\n\n" >> $LOGFILE 2>&1
     rm -rf $DUMP_DIR/*
#     printf "Finished deleting previous DB dump at $CURRENT_TIMESTAMP\n\n" >> $LOGFILE 2>&1
    fi
}





#if [ "$UID" -eq 0   ]; then


    printf "start mongodump at: $CURRENT_TIMESTAMP ...\n\n" >> $LOGFILE

    initialize

    mongodump --host "$(hostname -a)":29017 -u admin -p "$(cat $MONGODB_BASEDIR/pw)" --out $DUMP_DIR >> $LOGFILE 2>&1

    setTimestamp
    printf "dump of localdbs has been finished succesfully at $CURRENT_TIMESTAMP ....\n\n" >> $LOGFILE


#    sudo systemctl start mongod.service >> $LOGFILE 2>&1

##    printf "Copying dump to NAS using a dedicated python script.\n\n" >> $LOGFILE

##    cd $SB_BASEDIR/bin
    python $SB_BASEDIR/bin/copyDumpedMongoCollections.py >> $LOGFILE
    #rsync -aq --delete $DUMP_DIR/localdbs $DUMP_NAS >> $LOGFILE 2>&1

    setTimestamp
    printf "All done at $CURRENT_TIMESTAMP !\n\n" >> $LOGFILE
    gzip $LOGFILE

else
#    echo "you have to be root to start this script ...\n"
    echo "no dbpw found at $MONGODB_BASEDIR/pw ...\n"
    exit 1
fi



