#!/bin/sh

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

IFS='.' read -r -a arrayOfFileName <<< "$fileNameOnly"

prefixLockfile="${arrayOfFileName[1]}"
LOCKFILE=${CONFDIR}/${prefixLockfile}.lock

if [ -e ${LOCKFILE} ]; then
    echo -n "${arrayOfFileName[1]} is locked, probably by another process: "
    cat ${LOCKFILE}
    exit 1
else
    cd ${PROCESS_DIR}
    echo $$ >${LOCKFILE}
    python  ${PROCESS_DIR}/FileProcessorImpl.py --config=${CONFDIR}/${CONFFILE}  >> ${RUNDIR}/processFileImpl.log 2>&1
    rm $LOCKFILE
fi




