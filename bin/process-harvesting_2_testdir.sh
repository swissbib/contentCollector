#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting/sboaitest
CONTENTENV_HOME=/home/harvester/envContentCollector
PROCESS_DIR=${CONTENTENV_HOME}/bintest
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdirtest



#Benutze die Default Repos nicht auf dem Alternativ-host fuer Harvesting
#dieser wird fuer GND, DSV11 und Soezialfälle eingesetzt
#DEFAULTREPOS="libib serval ecod snl sbt idsbb idslu idssg1 idssg2 POSTERS zora retroseals abn bgr sgbn"
DEFAULTREPOS=""


if [ -n "$1" ]; then
  repos=$*
  repo_force=1
else
  repos=${DEFAULTREPOS}
  repo_force=0
fi

for repo in ${repos}; do
  LOCKFILE=${CONFDIR}/${repo}.lock

  if [ -e ${LOCKFILE} ]; then
    echo -n "${repo} is locked, probably by another harvester: "
    cat ${LOCKFILE}
    continue
  else
    echo $$ >${LOCKFILE}
  fi

  CONFIG=${CONFDIR}/config.${repo}.prod.xml

  python  ${PROCESS_DIR}/swissbibHarvesting.py --config=${CONFIG} >> ${RUNDIR}/process-harvesting-python.log 2>&1

  rm ${LOCKFILE}


done

