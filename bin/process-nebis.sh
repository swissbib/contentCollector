#!/bin/sh


PROCESS_DIR=/swissbib/harvesting/bin
RUNDIR=/swissbib/harvesting/rundir

cd ${PROCESS_DIR}

python swissbibNebisClient.py --config=${HOME}/confdir/config.nebis.prod.xml >> ${RUNDIR}/process-nebis-python.log 2>&1
