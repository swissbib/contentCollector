#!/bin/sh


source ~/.bashrc

BASE_EXPORTCBSDIR=/var/swissbib/mongo/exportlocaldbs
BASE_SCRIPTS=/usr/local/swissbib/mongoscripts/scripts


#DEFAULTREPOS="abn alex bgr idsbb idslu idssg1 idssg2 idssg2 nebis posters rero retros sbt sgbn snl zora"

DEFAULTREPOS="abn alex bgr idsbb idslu idssg1 idssg2 idssg2 nebis posters rero retros sbt sgbn snl zora"
#DEFAULTREPOS=idssg2


CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`

function setTimestamp()
{
    CURRENT_TIMESTAMP=`date +%Y%m%d%H%M%S`
}



LOGFILE=$BASE_SCRIPTS/log/export.$CURRENT_TIMESTAMP.log


function testOutDir ()
{

    if [ ! -d ${BASE_EXPORTCBSDIR}/$1 ]
    then
        printf "backup directory for repo $1 doesn't exist  - will be created !\n" >> ${LOGFILE}
        mkdir -p ${BASE_EXPORTCBSDIR}/$1
    else
        printf "backup directory for repo $1 already available  - old content wil be deleted !\n" >> ${LOGFILE}
        rm ${BASE_EXPORTCBSDIR}/$1/*
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

    setTimestamp

    printf "start reading content of repo $repo at $CURRENT_TIMESTAMP !\n" >> ${LOGFILE}


    CONFIG=${BASE_SCRIPTS}/config.read/config.readMongo.${repo}.xml

    pythonmongo  ${BASE_SCRIPTS}/readOAIRecords.py  --config=${CONFIG} --size=1000 --outDir=$BASE_EXPORTCBSDIR/$repo >> ${LOGFILE} 2>&1

    rm ${LOCKFILE}

    setTimestamp
    printf "export to CBS  for repo $repo done  at $CURRENT_TIMESTAMP - content in  ${BASE_EXPORTCBSDIR}/$repo !\n" >> ${LOGFILE}

    gzip $BASE_EXPORTCBSDIR/$repo/*.xml


done
