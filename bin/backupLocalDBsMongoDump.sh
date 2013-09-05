#!/bin/bash


BASE_DIR=/var/swissbib/mongo
DUMP_DIR=$BASE_DIR/dump
LOG_DIR=$BASE_DIR/scriptlog
CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
LOGFILE=$LOG_DIR/backup.$CURRENT_TIMESTAMP.log

CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`

function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



function initialize()
{
    printf "clear dump dir ....\n\n" >> $LOGFILE 2>&1
    rm -rf $DUMP_DIR/*
}


if [ "$UID"  -eq 0 ]; then


    printf "start mongodump at: $CURRENT_TIMESTAMP ...\n\n" >> $LOGFILE

    #mongod -f /etc/mongod2.conf --shutdown
    /etc/init.d/mongod2 stop >> $LOGFILE 2>&1
    printf "mongod instance on port 29017 is now down....\n\n" >> $LOGFILE



    initialize

    su -c "mongodump --dbpath $BASE_DIR/localdbs --out $BASE_DIR/dump/localdbs" mongod >> $LOGFILE 2>&1

    setTimestamp
    printf "dump of localdbs has been finished succesfully at $CURRENT_TIMESTAMP ....\n\n" >> $LOGFILE

    printf "now going to restart mongod instance on port 29017 ....\n\n" >> $LOGFILE
    /etc/init.d/mongod2 start >> $LOGFILE 2>&1

    printf "mongod instance on port 29017 is again up and running - Congratulations....\n\n" >> $LOGFILE



else
    echo "you have to be root to start this script ...\n"
    exit 1
fi



