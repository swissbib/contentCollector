#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting
CONTENTENV_HOME=/home/harvester/envContentCollector
VIRTUAL_PYTHON_ENV=${CONTENTENV_HOME}/env
PROCESS_DIR=${CONTENTENV_HOME}/bin
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdir

INITIAL_GND_LOAD_DIR=/swissbib/harvesting/Staff/gh/gnd.2014-05-15

   for loadFile in `ls ${INITIAL_GND_LOAD_DIR}`
    do

          CONFIG=${CONFDIR}/config.dnbgnd.prod.xml
          ${VIRTUAL_PYTHON_ENV}/bin/python  ${PROCESS_DIR}/readInitialGND.py --config=${CONFIG} --input=${INITIAL_GND_LOAD_DIR}/${loadFile} >> ${RUNDIR}/initial-gnd-load.log 2>&1

    done

