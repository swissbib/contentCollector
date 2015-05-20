#!/bin/sh


source ~/.bashrc

BASE_BACKUPDIR=/home/swissbib/Downloads/mongo/backup
BASE_SCRIPTS=/home/swissbib/environment/code/tools/python/oaiclient
BASE_MONGO=/home/swissbib/Downloads/mongo


#DEFAULTREPOS="abn alex bgr idsbb idslu idssg1 idssg2 idssg2 nebis posters rero retros sbt sgbn snl zora"

DEFAULTREPOS="abn alex bgr idsbb idslu idssg1 idssg2 idssg2 nebis posters rero retros sbt sgbn snl zora"
#DEFAULTREPOS=idssg2


CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`

function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



LOGFILE=$BASE_MONGO/log/backup.$CURRENT_TIMESTAMP.log







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


    if [ -d ${BASE_BACKUPDIR}/$1 ]
    then

         printf "starting to restore content for repo $repo! \n" >> ${LOGFILE}


        CONFIG=${BASE_SCRIPTS}/config.read.no.auth/config.readMongo.${repo}.xml

        mypython27  ${BASE_SCRIPTS}/restoreStoredNativeRecords.py  --config=${CONFIG} --outDir=$BASE_BACKUPDIR/$repo >> ${LOGFILE} 2>&1


    else
        print0f "backup directory for repo $repo doesn't exist  - $repo will be skipped !\n" >> ${LOGFILE}
    fi




    rm ${LOCKFILE}

    printf "backup for repo $repo done  - content in  ${BASE_BACKUPDIR}/$repo ! \n" >> ${LOGFILE}


done
