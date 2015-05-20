#!/bin/sh


source ~/.bashrc

BASE_BACKUPDIR=/var/swissbib/mongo/backuplocaldbs
BASE_SCRIPTS=/usr/local/swissbib/mongoscripts/scripts


#DEFAULTREPOS="abn alex bgr idsbb idslu idssg1 idssg2 idssg2 nebis posters rero retros sbt sgbn snl zora"

DEFAULTREPOS="abn alex bgr idsbb idslu idssg1 idssg2 idssg2 nebis posters rero retros sbt sgbn snl zora"
#DEFAULTREPOS=idssg2


CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`

function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



LOGFILE=$BASE_SCRIPTS/log/backup.$CURRENT_TIMESTAMP.log


function testOutDir ()
{

    if [ ! -d ${BASE_BACKUPDIR}/$1 ]
    then
        printf "backup directory for repo $1 doesn't exist  - will be created !\n" >> ${LOGFILE}
        mkdir -p ${BASE_BACKUPDIR}/$1
    else
        printf "backup directory for repo $1 already available  - old content wil be deleted !\n" >> ${LOGFILE}
        rm ${BASE_BACKUPDIR}/$1/*
    fi

}





if [ -n "$1" ]; then
  repos=$*
  repo_force=1
else
  repos=${DEFAULTREPOS}
  repo_force=0
fi


for repo in ${repos}; do
    LOCKFILE=${BASE_SCRIPTS}/${repo}.lock

    if [ -e ${LOCKFILE} ]; then
        echo -n "${repo} is locked, probably by another process: "
        cat ${LOCKFILE}
        continue
    else
        echo $$ >${LOCKFILE}
    fi

    testOutDir $repo

    CONFIG=${BASE_SCRIPTS}/config.read/config.readMongo.${repo}.xml

    pythonmongo  ${BASE_SCRIPTS}/backupStoredNativeRecords.py  --config=${CONFIG} --size=1000 --outDir=$BASE_BACKUPDIR/$repo >> ${LOGFILE} 2>&1

    rm ${LOCKFILE}

    printf "backup for repo $repo done  - content in  ${BASE_BACKUPDIR}/$repo ! \n" >> ${LOGFILE}


done
