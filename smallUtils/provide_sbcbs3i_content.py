__author__ = 'swissbib, Guenter Hipler'

import os,re

if __name__ == '__main__':

    archiveDir = "/swissbib/harvesting/archive/"
    #archiveDir = "/home/swissbib/temp/testCpsbcbs3i/archive/"
    resultsDir = "/swissbib/harvesting/results/"
    #resultsDir = "/home/swissbib/temp/testCpsbcbs3i/results/"

    pReroPattern = re.compile("rero-")
    pPostersPattern = re.compile("POSTERS-")
    pRetrosealsPattern = re.compile("retroseals-")

    copyPattern = "scp {0}{1}   harvester@sb-ucoai2.swissbib.unibas.ch:{2}"
    copyPatternPosters = "scp {0}{1}   harvester@sb-ucoai2.swissbib.unibas.ch:{2}{3}"
    sshLinkPattern = "ssh harvester@sb-ucoai2.swissbib.unibas.ch \"cd {0}; ln -s {1}{2} {2} \""
    sshLinkPatternPosters = "ssh harvester@sb-ucoai2.swissbib.unibas.ch \"cd {0}; ln -s {1}{2} {2} \""


    for fname in os.listdir(resultsDir):

        #if not pReroPattern.search(fname):
        wholePath = resultsDir + fname

        if os.path.islink(wholePath) and os.path.lexists(wholePath):

            if pPostersPattern.search(fname):
                fnamePostersTarget = re.sub("POSTERS", "posters",fname)
                cmdCopy = copyPatternPosters.format(resultsDir,fname,archiveDir,fnamePostersTarget )
                cmdLinkOnTarget = sshLinkPatternPosters.format(resultsDir,archiveDir,fnamePostersTarget)
            elif pRetrosealsPattern.search(fname):
                fnamePostersTarget = re.sub("retroseals", "retros",fname)
                cmdCopy = copyPatternPosters.format(resultsDir,fname,archiveDir,fnamePostersTarget )
                cmdLinkOnTarget = sshLinkPatternPosters.format(resultsDir,archiveDir,fnamePostersTarget)
            else:
                cmdCopy = copyPattern.format(resultsDir,fname,archiveDir )
                cmdLinkOnTarget = sshLinkPattern.format(resultsDir,archiveDir,fname)

            print(cmdCopy + os.linesep)
            os.system(cmdCopy)
            print(cmdLinkOnTarget + os.linesep)
            os.system(cmdLinkOnTarget)
            print(os.linesep)


