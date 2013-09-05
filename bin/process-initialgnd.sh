#!/bin/sh

BASEDIR=/swissbib/harvesting
PROCESS_DIR=${BASEDIR}/bin
RUNDIR=${BASEDIR}/rundir
LOGFILE=${RUNDIR}/process-initialgnd-python.log
CONFDIR=${HOME}/confdir
DATADIR=${BASEDIR}/Staff/gh/gnd/run
CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`



function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}

printf "starting initial loading of gnd data at  <%s> ...\n" ${CURRENT_TIMESTAMP}  >> $LOGFILE

for inputfile in ${DATADIR}/*.xml
do
    setTimestamp
    printf "inputfile <%s> ...\n" ${inputfile}   >> $LOGFILE
    printf "at  <%s> ...\n" ${CURRENT_TIMESTAMP}  >> $LOGFILE

    python ${PROCESS_DIR}/readInitialGND.py --config=${CONFDIR}/config.dnbgnd.prod.xml --input=${inputfile} >> ${LOGFILE} 2>&1

done

setTimestamp
printf "finished loading of gnd data at  <%s> ...\n" ${CURRENT_TIMESTAMP}  >> $LOGFILE
