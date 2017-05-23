#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting
CONTENTENV_HOME=/home/harvester/envContentCollector
PROCESS_DIR=${CONTENTENV_HOME}/bin
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdir



CONFFILE=$1

cd ${PROCESS_DIR}

python  ${PROCESS_DIR}/nationalLicences.py --config=${CONFDIR}/${CONFFILE}  >> ${RUNDIR}/processFileNLImpl.log 2>&1
