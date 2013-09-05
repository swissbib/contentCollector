#!/bin/sh

PROCESS_DIR=/swissbib/harvesting/bin
RUNDIR=/swissbib/harvesting/rundir

DEFAULTREPOS="rero snl sbt idsbb idslu idssg1 idssg2 POSTERS zora retroseals abn bgr sgbn alex"


if [ -n "$1" ]; then
  repos=$*
  repo_force=1
else
  repos=${DEFAULTREPOS}
  repo_force=0
fi

for repo in ${repos}; do
  LOCKFILE=${HOME}/confdir/${repo}.lock

  if [ -e ${LOCKFILE} ]; then
    echo -n "${repo} is locked, probably by another harvester: "
    cat ${LOCKFILE}
    continue
  else
    echo $$ >${LOCKFILE}
  fi

  CONFIG=${HOME}/confdir/config.${repo}.prod.xml


  python  ${PROCESS_DIR}/swissbibHarvesting.py --config=${CONFIG} >> ${RUNDIR}/process-harvesting-python.log 2>&1

  rm ${LOCKFILE}


done

