#!/bin/sh

DATA_BASE_DIR=/swissbib/harvesting
CONTENTENV_HOME=/home/harvester/envContentCollector
VIRTUAL_PYTHON_ENV=${CONTENTENV_HOME}/env
PROCESS_DIR=${CONTENTENV_HOME}/bin
RUNDIR=${DATA_BASE_DIR}/rundir
CONFDIR=${CONTENTENV_HOME}/confdir




#DEFAULTREPOS="snl"
DEFAULTREPOS="snl ecod"



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
  ${VIRTUAL_PYTHON_ENV}/bin/python  ${PROCESS_DIR}/createOAIDeletes.py --config=${CONFIG} >> ${RUNDIR}/process-create-deletes.log 2>&1

  rm ${LOCKFILE}

done

