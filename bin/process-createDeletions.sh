#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting
CONTENTENV_HOME=/home/harvester/envContentCollector
PROCESS_DIR=${CONTENTENV_HOME}/bin
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdir




#DEFAULTREPOS="snl"
DEFAULTREPOS="snl ecod sersol idsbb"



if [ -n "$1" ]; then
  repos=$*
  repo_force=1
else
  repos=${DEFAULTREPOS}
  repo_force=0
fi

for repo in ${repos}; do
  LOCKFILE=${CONFDIR}/${repo}.createDeletes.lock

  if [ -e ${LOCKFILE} ]; then
    echo -n "${repo} is locked, probably by another create deletes process: "
    cat ${LOCKFILE}
    continue
  else
    echo $$ >${LOCKFILE}
  fi

  CONFIG=${CONFDIR}/config.${repo}.prod.xml
  python  ${PROCESS_DIR}/createOAIDeletes.py --config=${CONFIG} >> ${RUNDIR}/process-create-deletes.log 2>&1

  rm ${LOCKFILE}

done

