__author__ = 'swissbib - UB Basel, Switzerland, Guenter Hipler'
__copyright__ = "Copyright 2014, swissbib project"
__license__ = "??"
__version__ = "0.1"
__maintainer__ = "Guenter Hipler"
__email__ = "guenter.hipler@unibas.ch"
__status__ = "in development"
__description__ = """
                copy dumped Mongo collections to NAS storage
                use single directories for every day of a week
                (compare Perl Script AvA - mybu.pl - used for backup of MySQL DBs)
                """


import re, os, shutil
from datetime import datetime

formatTimestamp = '%Y-%m-%d %H:%M:%S %Z'

print "now start of rsync mechanism with Python - script at " + datetime.now().strftime(formatTimestamp)


BASE_DIR="/var/swissbib/mongo"
#BASE_DIR= os.sep + "home" + os.sep + "swissbib" + os.sep + "temp" + os.sep + "testBackupMongo"
DUMP_DIR=BASE_DIR + os.sep + "dump"

#DUMP_NAS=/var/swissbib/dbbu/mongo/dump
#Test
DUMP_NAS="/var/swissbib/dbbu/mongo/swissbibRawDataMongo"
#DUMP_NAS=BASE_DIR + os.sep +  "swissbibRawDataMongo"
#LOG_DIR=BASE_DIR  + "/scriptlog"
LOG_DIR=BASE_DIR  + os.sep + "scriptlog"

wochentag = ['sonntag', 'montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag', 'samstag']

tag = wochentag[(datetime.today().weekday() + 1)%7]

if not os.path.exists(DUMP_NAS):
    try:
        os.system("mkdir -p " +  DUMP_NAS)
    except Exception as argsError:
        print "error while trying to create backupdir at: " + datetime.now().strftime(formatTimestamp)
        exit("error trying to create backupdir: " + DUMP_NAS)

tagesVerzeichnis = DUMP_NAS + os.sep + "backup-" + tag + "-" + datetime.now().strftime("%Y%m%d")

dirEntries =  os.listdir(DUMP_NAS)
pattern = re.compile("backup-" + tag + ".*")

for entry in dirEntries:
    fullEntry = DUMP_NAS + os.sep + entry
    if os.path.isdir(fullEntry):
        if pattern.search(fullEntry):
            print "now going to delete old directory:  " + fullEntry
            shutil.rmtree(fullEntry)
            #os.removedirs(fullEntry)


if not os.path.exists(tagesVerzeichnis):
    try:
        os.system("mkdir -p " +  tagesVerzeichnis)
    except Exception as argsError:
        print "daily directory " + tagesVerzeichnis + " couldn't be created"
        exit("error trying to create tagesverzeichnis: " + tagesVerzeichnis)


#cmd = "rsync -aq --delete " + DUMP_DIR + os.sep + "localdbs " +  tagesVerzeichnis
cmd = "rsync -aq --delete " + DUMP_DIR + " " +  tagesVerzeichnis
os.system(cmd)

print "rsync mechanism with Python - script finished at " + datetime.now().strftime(formatTimestamp)

















