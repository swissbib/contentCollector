__author__ = 'swissbib, Guenter Hipler'

import os,re

if __name__ == '__main__':

    archiveDirsb_cbs3i = "/swissbib/harvesting/archive/"
    archiveDirsb_cbs4i = "/swissbib/harvesting/sb-cbs4i/archive/"
    #archiveDir = "/home/swissbib/temp/testCpsbcbs3i/archive/"
    resultsDirsb_cbs3i = "/swissbib/harvesting/results/"
    resultsDirsb_cbs4i = "/swissbib/harvesting/sb-cbs4i/results/"

    #resultsDir = "/home/swissbib/temp/testCpsbcbs3i/results/"


    #copyPattern = "scp {0}{1}   harvester@sb-coai2.swissbib.unibas.ch:{2}"
    copyPattern = "cp {0}{1} {2}"
    sshLinkPattern = "ln -s {0}{1} {2}{1} "


    changeDirCommand =  "cd " +  resultsDirsb_cbs4i
    print changeDirCommand
    os.system(changeDirCommand)
    for fname in os.listdir(resultsDirsb_cbs3i):
        print fname
        copyCommand = copyPattern.format(archiveDirsb_cbs3i,fname,archiveDirsb_cbs4i)
        print copyCommand
        os.system(copyCommand)
        sshLinkCommand = sshLinkPattern.format(archiveDirsb_cbs4i,fname,resultsDirsb_cbs4i)
        print sshLinkCommand
        os.system(sshLinkCommand)






