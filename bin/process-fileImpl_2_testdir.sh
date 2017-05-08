#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting/sboaitest
CONTENTENV_HOME=/home/harvester/envContentCollector
PROCESS_DIR=${CONTENTENV_HOME}/bintest
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdirtest



CONFFILE=$1

cd ${PROCESS_DIR}

python  ${PROCESS_DIR}/FileProcessorImpl.py --config=${CONFDIR}/${CONFFILE}  >> ${RUNDIR}/processFileImpl.log 2>&1
