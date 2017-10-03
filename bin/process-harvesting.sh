#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting
CONTENTENV_HOME=/home/harvester/envContentCollector
PROCESS_DIR=${CONTENTENV_HOME}/bin
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdir


DEFAULTREPOS="boris libib serval ecod snl sbt idsbb idslu idssg1 POSTERS zora retroseals abn bgr sgbn alex vaud_lib vaud_school hemu edoc"


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

