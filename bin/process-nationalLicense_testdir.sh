#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting/sboaitest
CONTENTENV_HOME=/home/harvester/envContentCollector
VIRTUAL_PYTHON_ENV=${CONTENTENV_HOME}/env
PROCESS_DIR=${CONTENTENV_HOME}/bintest
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdirtest



CONFFILE=$1

cd ${PROCESS_DIR}

${VIRTUAL_PYTHON_ENV}/bin/python  ${PROCESS_DIR}/nationalLicences.py --config=${CONFDIR}/${CONFFILE}  >> ${RUNDIR}/processFileImpl.log 2>&1
