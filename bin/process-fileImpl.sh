#!/bin/bash

DATA_BASE_DIR=/swissbib/harvesting
CONTENTENV_HOME=/home/harvester/envContentCollector
PROCESS_DIR=${CONTENTENV_HOME}/bin
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdir
#PROCESS_DIR=/home/harvester/envContentCollector/bin

#GH, 7.4.2016
#we need a blocking mechanism if another process with the same repository is already running

CONFFILE=$1

fileNameOnly=$(basename "$CONFFILE")

#we can't use the old (RedHat) mechanism to read a part of the filename anymore
 #this isn't a good solution because it expects a filename with a special name
 #don't have the time to make it more generic at the moment...
prefixLockfile=`echo $fileNameOnly  | sed 's/config\.\(.*\)\.prod\.xml/\1/'`

LOCKFILE=${CONFDIR}/${prefixLockfile}.lock

if [ -e ${LOCKFILE} ]; then
    echo -n "${prefixLockfile} is locked, probably by another process: "
    cat ${LOCKFILE}
    exit 1
else
    cd ${PROCESS_DIR}
    echo $$ >${LOCKFILE}
    python  ${PROCESS_DIR}/FileProcessorImpl.py --config=${CONFDIR}/${CONFFILE}  >> ${RUNDIR}/processFileImpl.log 2>&1
    rm $LOCKFILE
fi




