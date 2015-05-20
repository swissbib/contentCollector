#!/bin/bash


BASE_DIR=/var/swissbib/mongo
DUMP_DIR=$BASE_DIR/dump
LOG_DIR=$BASE_DIR/scriptlog
DATA_DIR=$BASE_DIR/localdbs
CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
LOGFILE=$LOG_DIR/restore.$CURRENT_TIMESTAMP.log

CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`

function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



function initialize()
{
    printf "clear data dir ....\n\n" >> $LOGFILE
    #once we have enough space it should be mv
    mv  $DATA_DIR $BASE_DIR/localdbs.copy
    #rm -rf $DATA_DIR

    mkdir -p $DATA_DIR
    chown mongod:mongod $DATA_DIR

}


if [ "$UID"  -eq 0 ]; then


    printf "start mongorestore at: $CURRENT_TIMESTAMP ...\n\n" >> $LOGFILE

    #mongod -f /etc/mongod2.conf --shutdown
    /etc/init.d/mongod2 stop >> $LOGFILE
    printf "mongod instance on port 29017 is now down....\n\n" >> $LOGFILE



    initialize

    su -c "mongorestore --dbpath /var/swissbib/mongo/localdbs --journal /var/swissbib/mongo/dump/localdbs" mongod >> $LOGFILE

    setTimestamp
    printf "restore of localdbs has been finished succesfully at $CURRENT_TIMESTAMP ....\n\n" >> $LOGFILE

    printf "now going to restart mongod instance on port 29017 ....\n\n" >> $LOGFILE
    /etc/init.d/mongod2 start >> $LOGFILE

    printf "mongod instance on port 29017 is again up and running - Congratulations....\n\n" >> $LOGFILE



else
    echo "you have to be root to start this script ...\n"
    exit 1
fi



