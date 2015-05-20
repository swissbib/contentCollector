__author__ = 'swissbib, Guenter Hipler'

import os,re

if __name__ == '__main__':

    incomingDir = "/swissbib/harvesting/incoming/"
    incomingDirCopied = "/swissbib/harvesting/incomingcopied/"

    pNebisPattern = re.compile("aleph.PRIMO")

    copyPattern = "scp {0}  harvester@sb-coai2.swissbib.unibas.ch:{1}"
    mvPattern = "mv {0} {1}"


    for fname in os.listdir(incomingDir):

        if pNebisPattern.search(fname):
            wholePath = incomingDir + fname
            cpCommand = copyPattern.format(wholePath, incomingDir)
            mvCommand = mvPattern.format(wholePath,incomingDirCopied)

            os.system(cpCommand)
            os.system(mvCommand)


