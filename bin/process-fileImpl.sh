#!/bin/sh


PROCESS_DIR=/swissbib/harvesting/bin
RUNDIR=/swissbib/harvesting/rundir


CONFFILE=$1

cd ${PROCESS_DIR}

python FileProcessorImpl.py --config=${HOME}/confdir/$CONFFILE >> ${RUNDIR}/processFileImpl.log 2>&1
