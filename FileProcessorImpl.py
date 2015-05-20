import os
import re
import glob
from swissbibUtilities import SwissbibUtilities, ErrorHashProcesing, ResultCollector, ErrorMongoProcessing, AdministrationOperation, ProcessSingleNebisRecord
from pyexpat import ExpatError
from swissbibHash import HashNebisMarcContent
from datetime import datetime, timedelta

from Context import ApplicationContext,HarvestingWriteContext,FileWebdavWriteContext,WriteContext,FilePushWriteContext

from swissbibPreImportProcessor import SwissbibPreImportProcessor
from harvestingTasks import PersistRecordMongo
from Context import StoreNativeRecordContext, TaskContext


import inspect
import time






__author__ = 'swissbib'


class FileProcessor(SwissbibPreImportProcessor):

    def __init__(self,context):

        SwissbibPreImportProcessor.__init__(self,context)



    def lookUpContent(self):
        pass


    def preProcessContent(self):
        pass


    def process(self):
        pass

    def postProcessContent(self):
        pass



    #sollte protected sein -> dafuer muss ich jedoch Module einrichten
    def processFileContent(self,inputResourceContext):
        pass

    def initialize(self):
        pass



    def transformRecordNamespace(self,contentSingleRecord):

        #ich muss hier eine Fehlerbehandlung einbauen, wenn die Transformation nicht funktioniert!

        #at the moment only Primo records have to be transformed into a namespace, which can be processed by later systems in the chain
        #for our cases it's CBS

        #das muss besser getestet werden
        return SwissbibPreImportProcessor.transformRecordNamespace(self,contentSingleRecord)




    def _processFileContent(self,inputResourceContext):

        try:

            for contentSingleRecord in inputResourceContext.createGenerator():

                try:

                    recordId = self.getRecordId(contentSingleRecord)

                except Exception as pythonBaseException:

                     self._writeErrorMessages(self.context.getWriteContext(),pythonBaseException,"Exception afters searching recordID " +
                                                                                                 os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))
                     continue


                recordDeleted = self.isDeleteRecord(contentSingleRecord)
                if recordDeleted:
                    contentSingleRecord = self.prepareDeleteRecord(contentSingleRecord)

                else:

                    try:

                        contentSingleRecord = self.transformRecordNamespace(contentSingleRecord)

                    except Exception as transformException:
                        self._writeErrorMessages(self.context.getWriteContext(),transformException,"Exception while transforming the namespace of the single record  \n"
                                                                                          + contentSingleRecord + "\n" +
                                                                                        os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))
                        continue


                substituteChars = self.context.getConfiguration().getSubstituteCharacters()
                if not substituteChars is None:
                    contentSingleRecord = re.sub(substituteChars," ",contentSingleRecord)


                try:
                    self.parseWellFormed(contentSingleRecord)

                except ExpatError as expatInst:
                    self.context.getResultCollector().addRecordsparseError(1)
                    self._writeErrorMessages(self.context.getWriteContext(),expatInst,"Exception after parsing record for well formed format \n"
                                                                                      + contentSingleRecord + "\n" +
                                                                                    os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))
                    continue


                if self.context.getConfiguration().isSkipRecords():
                    self._processSkipRecord(contentSingleRecord)


                else:

                    self.context.getResultCollector().addRecordsToCBSNoSkip(1)
                    self.context.getWriteContext().writeItem(contentSingleRecord)

                for taskName,task  in  self.context.getConfiguration().getDedicatedTasks().items():

                    try:

                        if isinstance(task,PersistRecordMongo):
                            taskContext = StoreNativeRecordContext(appContext=self.context,
                                                                    rID=recordId,singleRecord=contentSingleRecord,
                                                                    deleted=recordDeleted)
                        else:
                            taskContext = TaskContext(appContext=self.context)
                        task.processRecord(taskContext)
                    except Exception as pythonBaseException:

                        self._writeErrorMessages(self.context.getWriteContext(),pythonBaseException,"Exception while processing task\n"
                                                                                          + contentSingleRecord + "\n" +
                                                                                        os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))

                        continue

        except Exception as pythonBaseException:

            self._writeErrorMessages(self.context.getWriteContext(),pythonBaseException,"Exception in _processFileContent which could not be caught \n" +
                                                                            os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))

            raise pythonBaseException




    def _writeErrorMessages(self,writeContext, exceptionType, exceptionName):
        if not writeContext is None:
            writeContext.writeErrorLog(header=exceptionName,message=[str(exceptionType)])
        else:
            print "no WriteContext after Error: " + exceptionName + " Handler\n"
            print "redirect error message to stdout\n"
            print str(exceptionType) + "\n"





class FilePushProcessor(FileProcessor):

    def __init__(self,context):
        FileProcessor.__init__(self, context)

        #Todo: pruefe ob die configuration vom Typ Nebis config ist


        self.newFileTemplate = re.compile('(.*?)\.' + self.context.getConfiguration().getFileNameSuffix(),re.UNICODE | re.DOTALL | re.IGNORECASE)





    def initialize(self):


        if not os.path.isdir(self.context.getConfiguration().getIncomingDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getIncomingDir())


        if not os.path.isdir(self.context.getConfiguration().getClusteringDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getClusteringDir())
        else:
            os.system("rm -r " + self.context.getConfiguration().getClusteringDir())
            os.system("mkdir -p " + self.context.getConfiguration().getClusteringDir())


        if not os.path.isdir(self.context.getConfiguration().getNebisWorking()):
            os.system("mkdir -p " + self.context.getConfiguration().getNebisWorking())
        else:
            os.system("rm -r " + self.context.getConfiguration().getNebisWorking())
            os.system("mkdir -p " + self.context.getConfiguration().getNebisWorking())

        if not os.path.isdir(self.context.getConfiguration().getCollectedDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getCollectedDir())
        else:
            os.system("rm -r " + self.context.getConfiguration().getCollectedDir())
            os.system("mkdir -p " + self.context.getConfiguration().getCollectedDir())



        if not os.path.isdir(self.context.getConfiguration().getNebisSrcDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getNebisSrcDir())



        SwissbibPreImportProcessor.initialize(self)





    def prepareDeleteRecord(self,recordToDelete):

        #nebis redords marked as deleted contain still a metadata section with a lot of rubbish we can throw away
        #look for an example in: notizen/examples.oai/aleph.nebis/nebis.deleted.indent.xml

        spNebisDeletedRecordsToSubstitutePattern = self.pNebisDeleteRecord.search(recordToDelete)
        if spNebisDeletedRecordsToSubstitutePattern:
            toReturn= spNebisDeletedRecordsToSubstitutePattern.group(1) + spNebisDeletedRecordsToSubstitutePattern.group(2)
        else:
            #todo: write a message
            toReturn = recordToDelete

        return toReturn




    def lookUpContent(self):


        os.chdir(self.context.getConfiguration().getIncomingDir())


        for fileName in os.popen('find . -mmin +2 -name "*.tar.gz"') :
            #remove carriage return characters from file name
            orgFileName = fileName[:-1]
            os.system("mv " + orgFileName + " " + self.context.getConfiguration().getNebisWorking())
            #onlyFile = os.path.basename(orgFileName)


    def process(self):
        os.chdir(self.context.getConfiguration().getNebisWorking())
        #for fileName in os.popen('dir *' + self.harvestingNebisConfigs.getFileNameSuffix()) :

        #it's really important to process the files in sorted alphabetic order!
        #otherwise we store the history of records in the wrong order in our datastore
        #-> not the really last version of a record is stored and the datastore is used to create the initial CBS database
        #sorted(glob.glob('*' + self.context.getConfiguration().getFileNameSuffix()), key=os.path.getmtime) // sort by time
        #sorted(glob.glob('*' + self.context.getConfiguration().getFileNameSuffix()), key=os.path.getsize) // sort by size

        for fileName in sorted(glob.glob('*' + self.context.getConfiguration().getFileNameSuffix())):

            #change filename
            #aleph.PRIMO-FULL.20120323.121009.1.tar.gz -> nebis-20120323.121009.1.xml(.gz)
            tfileName =  re.sub("aleph\.PRIMO-FULL\.","nebis-",fileName)

            compoundOutputFile =  self.newFileTemplate.search(tfileName).group(1) + ".xml"



            os.system("cp " + fileName + " " + self.context.getConfiguration().getClusteringDir())

            try:

                wC = FilePushWriteContext(self.context)

                wC.setOutFileName(self.context.getConfiguration().getCollectedDir() + os.sep +  compoundOutputFile)
                self.context.setWriteContext(wC)

                sfC = PushFileProvider(self.context)
                sfC.setFileName(fileName)

                self.processFileContent(sfC)

                wC.closeWriteContext()

                self.context.getResultCollector().addProcessedFile(fileName)

                os.chdir(self.context.getConfiguration().getNebisWorking())
                os.system("mv " + fileName + " " + self.context.getConfiguration().getNebisSrcDir())

            except Exception as pythonBasicException:

                #die alephfiles sollen nochmals verarbeitet werden
                os.chdir(self.context.getConfiguration().getNebisWorking())
                os.system("mv *.gz " + self.context.getConfiguration().getIncomingDir())
                raise pythonBasicException
            finally:
                #cleanup the cluster directory for the next file which has to be processed
                os.system("rm -r " + self.context.getConfiguration().getClusteringDir())
                os.system("mkdir -p " + self.context.getConfiguration().getClusteringDir())


    def processFileContent(self,inputResourceContext):

        self._processFileContent(inputResourceContext)





    def _processSkipRecord(self,inputResourceContext):
        raise Exception("FilePushProcessor doesn't implement skipRecord Functionality at the moment")






class FileWebDavProcessor(FileProcessor):




    def __init__(self,context):
        FileProcessor.__init__(self,context)

        self.pReroDeleteRecord = re.compile("(<record>.*?</header>).*",re.UNICODE | re.DOTALL | re.IGNORECASE)

        self.pIncomingPattern = re.compile("(.*?)##(.*?)##$")
        self.pIncomingPatternFromUntil = re.compile("^(.*?)UNTIL(.*?)$")
        self.pStoreProcPattern = re.compile("^LATEST_PROCESSING$",re.UNICODE | re.DOTALL | re.IGNORECASE)


    def initialize(self):


        if not os.path.isdir(self.context.getConfiguration().getReroWorkingDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getReroWorkingDir())
        else:
            os.system("rm -r " + self.context.getConfiguration().getReroWorkingDir())
            os.system("mkdir -p " + self.context.getConfiguration().getReroWorkingDir())

        if not os.path.isdir(self.context.getConfiguration().getDumpDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getDumpDir())
        else:
            os.system("rm -r " + self.context.getConfiguration().getDumpDir())
            os.system("mkdir -p " + self.context.getConfiguration().getDumpDir())

        if not os.path.isdir(self.context.getConfiguration().getDumpDirSkipped()):
            os.system("mkdir -p " + self.context.getConfiguration().getDumpDirSkipped())
        else:
            os.system("rm -r " + self.context.getConfiguration().getDumpDirSkipped())
            os.system("mkdir -p " + self.context.getConfiguration().getDumpDirSkipped())

        if not os.path.isdir(self.context.getConfiguration().getArchiveDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getArchiveDir())

        if not os.path.isdir(self.context.getConfiguration().getResultDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getResultDir())

        if not os.path.isdir(self.context.getConfiguration().getErrorLogDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getErrorLogDir())

        if not os.path.isdir(self.context.getConfiguration().getProcessLogDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getProcessLogDir())

        if not os.path.isdir(self.context.getConfiguration().getReroSrcDir()):
            os.system("mkdir -p " + self.context.getConfiguration().getReroSrcDir())






    def lookUpContent(self):


        inDirConfigured = self.context.getConfiguration().getIncomingDir()

        print "configured directory: " + inDirConfigured + "\n"

        mStoreLatestProc =  self.pStoreProcPattern.search(inDirConfigured)


        # first) we are searchin g for the pattern which indicates: the last day processed is stored in a file
        #-> I guess this will be the norml case
        if mStoreLatestProc:

            #fileLatestProcessing = self.context.getConfiguration().getStoreLatestProc()
            #tfile = open(fileLatestProcessing,"r")
            #sDateLastProc =  tfile.read()
            #tfile.close()
            sDateLastProc = self.context.getConfiguration().getStoreLatestProc().strip()

            #newFile.flush()
            #pythonDate = datetime.strptime(datum,"%d/%b/%Y")
            #pythonDateShort = datetime.strptime(pythonDate,"%Y-%m-%d")
            dateProc = datetime.strptime(sDateLastProc,"%Y_%m_%d")
            dateProc = dateProc + timedelta(days=1)

            #dateProc += dateProc.timedelta(days=1)

            stringCurrentDate = datetime.now().strftime("%Y_%m_%d")
            stringDateProc = dateProc.strftime("%Y_%m_%d")
            dirsNoTAvailable = []

            while (stringDateProc <= stringCurrentDate):
                inDir = self.context.getConfiguration().getBasedirwebdav() + os.sep + stringDateProc

                print "looking for files in dir: " + inDir

                try:
                    fileList = []
                    for fname in sorted(os.listdir(inDir)):
                        fileList.append(fname)

                    self._createLocalFile(inDir,fileList)

                    #now store the subdirectory where we have found content. This directory plus 1 day will be the starting point for the next job
                    self.context.getConfiguration().setStoreLatestProc(stringDateProc)

                except Exception as pythonBasicException:

                    dirsNoTAvailable.append(stringDateProc)


                    #write exception
                    #to raise an exception isn't necessary in this moment because files are not available
                    #todo: more testing and experience is necessary
                    self._writeErrorMessages(self.context.getWriteContext(),pythonBasicException,"Exception while searching for files in incoming directory " +
                                                                                                 os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))

                finally:

                    #now write the subdir - name of Basedirwebdav we tried to read content files
                    #this will be the starting point plus 1 day for the next process

                    #It might happen that the script starts during the day but the content for this day has not been filed so far
                    #if this happens the next starting point for the script should be today - 1 day so we have another chance not to miss the content for the current

                    #if (stringDateProc != stringCurrentDate) or (stringDateProc == stringCurrentDate and stringCurrentDate not in dirsNoTAvailable) :
                    #    self.context.getConfiguration().setStoreLatestProc(stringDateProc)
                    #else:
                    #    dateYesterday = (datetime.now() + timedelta(days=-1)).strftime("%Y_%m_%d")
                    #    self.context.getConfiguration().setStoreLatestProc(dateYesterday)




                    #tfile = open(fileLatestProcessing,"w")
                    #tfile.write(stringDateProc)
                    #tfile.flush()
                    #tfile.close()
                    #we don't need this because we just store the name of the last subdir processed
                    pass

                dateProc = datetime.strptime(stringDateProc,"%Y_%m_%d")
                dateProc = dateProc + timedelta(days=1)

                stringDateProc = dateProc.strftime("%Y_%m_%d")

        else:

            # first hasn't matched

            mIncomingPattern =  self.pIncomingPattern.search(inDirConfigured)

            if mIncomingPattern:
                baseDir = mIncomingPattern.group(1)
                dayPattern = mIncomingPattern.group(2)
                if dayPattern == "0":
                    inDir = baseDir + '{:%Y_%m_%d}'.format(datetime.now() )
                    # we are looking for a directory with current day

                    print "looking for files in dir: " + inDir

                    try:
                        fileList = []
                        for fname in sorted(os.listdir(inDir)):
                            fileList.append(fname)

                        self._createLocalFile(inDir,fileList)

                    except Exception as pythonBasicException:


                        #write exception
                        #to raise an exception isn't necessary in this moment because files are not available
                        #todo: more testing and experience is necessary
                        self._writeErrorMessages(self.context.getWriteContext(),pythonBasicException,"Exception while searching for files in incoming directory " +
                                                                                                     os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))



                        #print str(pythonBasicException)

                else:
                    mUntilPattern =  self.pIncomingPatternFromUntil.search(dayPattern)
                    if mUntilPattern:

                        print "looking for files with from - until pattern for directories \n"

                        #there is from - until range in the past
                        #like ##-5UNTIL-3##
                        #attention: first value has to be smaller

                        fromDate = mUntilPattern.group(1)
                        untilDate = mUntilPattern.group(2)
                        iFromDate = int(fromDate)
                        iUntilDate = int(untilDate)
                        while iFromDate <= iUntilDate:
                            dateDir = datetime(datetime.today().year,datetime.today().month,datetime.today().day) + timedelta(iFromDate)
                            inDir = baseDir + '{:%Y_%m_%d}'.format(dateDir)

                            print "looking for files in directory: " + inDir + "\n"

                            try:
                                fileList = []
                                for fname in sorted(os.listdir(inDir)):
                                    fileList.append(fname)

                                self._createLocalFile(inDir,fileList)

                            except Exception as pythonBasicException:
                                #write exception
                                #print str(pythonBasicException)
                                self._writeErrorMessages(self.context.getWriteContext(),pythonBasicException,"Exception while searching for files with from until mode " +
                                                                                                             os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))

                            finally:
                                iFromDate += 1


                    else:
                        #there is only a single date in the past
                        #like ##-5##
                        tDate = datetime(datetime.today().year,datetime.today().month,datetime.today().day) + timedelta(int(dayPattern))
                        inDir = baseDir + '{:%Y_%m_%d}'.format(tDate)
                        print "looking for files in directory: " + inDir + "\n"

                        try:

                            fileList = []
                            for fname in sorted(os.listdir(inDir)):
                                fileList.append(fname)

                            self._createLocalFile(inDir,fileList)


                        except Exception as pythonBasicException:
                            #write exception
                            #print str(pythonBasicException)
                            self._writeErrorMessages(self.context.getWriteContext(),pythonBasicException,"Exception while searching for files in the past mode " +
                                                                                                         os.path.basename(__file__) + " line + " + str(inspect.currentframe().f_back.f_lineno))


            else:

                #we assume it is a single directory
                try:
                    inDir = self.context.getConfiguration().getIncomingDir()

                    print "looking for files in incoming directory with no date: " + inDir + "\n"


                    fileList = []
                    for fname in sorted(os.listdir(inDir)):
                        fileList.append(fname)

                    self._createLocalFile(inDir,fileList)


                except Exception as pythonBasicException:
                    #write exception
                    print str(pythonBasicException)



    def _createLocalFile(self,inDir, fileList):


        #we have to ensure files with deletes are always processed after updates!

        pDeletePattern = re.compile("delete",re.UNICODE | re.DOTALL)

        fileWithDelets = []
        fileNoDeletes = []
        for  fname in fileList:
            bFileWithDelets = pDeletePattern.search(fname)
            if bFileWithDelets:
                fileWithDelets.append(fname)
            else:
                fileNoDeletes.append(fname)

        for fname in fileNoDeletes:

            newFileName = "".join(['{:%Y%m%d%H%M%S}'.format(datetime.now()),"-",fname])
            os.system("cp " + inDir + os.sep +  fname + " " + self.context.getConfiguration().getReroWorkingDir() + os.sep + newFileName )
            os.system("gunzip " + self.context.getConfiguration().getReroWorkingDir() + os.sep + newFileName)

            time.sleep(5)


        for fname in fileWithDelets:

            newFileName = "".join(['{:%Y%m%d%H%M%S}'.format(datetime.now()),"-",fname])
            os.system("cp " + inDir + os.sep +  fname + " " + self.context.getConfiguration().getReroWorkingDir() + os.sep + newFileName )
            os.system("gunzip " + self.context.getConfiguration().getReroWorkingDir() + os.sep + newFileName)

            time.sleep(5)




    def process(self):

        try:

            for fname in sorted(os.listdir(self.context.getConfiguration().getReroWorkingDir())):


                compoundOutputFileName = "".join([str(self.context.getConfiguration().getPrefixSummaryFile()),"-",fname])

                #compoundOutputFileName = self._createCompoundFileName(fname)

                wC = FileWebdavWriteContext(self.context)
                self.context.setWriteContext(wC)

                wC.setOutFileName(compoundOutputFileName)
                sfC = WebDavFileProvider(self.context, fname)
                self.processFileContent(sfC)

                self.context.getResultCollector().addProcessedFile(fname)

                wC.closeWriteContext()



        except Exception as pythonBasicException:

            raise pythonBasicException


    def processFileContent(self,inputResourceContext):

        self._processFileContent(inputResourceContext)




    def _processSkipRecord(self,inputResourceContext):
        raise Exception("FileWebDavProcessor doesn't implement skipRecord Functionality at the moment")



    def postProcessContent(self):

        os.chdir(self.context.getConfiguration().getReroWorkingDir())


        for fname in glob.glob('*.xml'):
            os.system("mv " + fname + " " +
                      self.context.getConfiguration().getReroSrcDir())
        os.chdir(self.context.getConfiguration().getReroSrcDir() )
        for fname in glob.glob('*.xml'):
            os.system("gzip " + fname )



    def _createCompoundFileName(self, rawFileName):

        compoundOutputFileName = None

        #example for update file name: rero_primo_20130714_240_update_standard_0001.xml.gz
        pFilePattern = re.compile("rero_primo(_.*?_)update_(.*$)",re.UNICODE | re.DOTALL)
        searchedName = pFilePattern.search(rawFileName)
        if searchedName:
            #pfilename rero_primo_20130313_1_update_0238.xml
            #cbs expects a hyphen
            compoundOutputFileName = "".join([str(self.context.getConfiguration().getPrefixSummaryFile()),
                                            "-",
                                            '{:%Y%m%d%H%M%S}'.format(datetime.now()),
                                            '_update',
                                            searchedName.group(1),
                                            searchedName.group(2)
                                         ])

        if compoundOutputFileName is None:
            #example for delte masked: rero_primo_20130714_240_delete_masked_object_0001.xml.gz
            pFilePattern = re.compile("rero_primo(_.*?_)delete_masked_object_(.*$)",re.UNICODE | re.DOTALL)
            searchedName = pFilePattern.search(rawFileName)
            if searchedName:
                #pfilename rero_primo_20130313_1_update_0238.xml
                #cbs expects a hyphen
                compoundOutputFileName = "".join([str(self.context.getConfiguration().getPrefixSummaryFile()),
                                                "-",
                                                '{:%Y%m%d%H%M%S}'.format(datetime.now()),
                                                '_delete_masked',
                                                searchedName.group(1),
                                                searchedName.group(2)
                                             ])

        if compoundOutputFileName is None:
            #example for delete standard: rero_primo_20130714_240_delete_standard_0001.xml.gz
            pFilePattern = re.compile("rero_primo(_.*?_)delete_standard_(.*$)",re.UNICODE | re.DOTALL)
            searchedName = pFilePattern.search(rawFileName)
            if searchedName:
                #pfilename rero_primo_20130313_1_update_0238.xml
                #cbs expects a hyphen
                compoundOutputFileName = "".join([str(self.context.getConfiguration().getPrefixSummaryFile()),
                                                "-",
                                                '{:%Y%m%d%H%M%S}'.format(datetime.now()),
                                                '_delete_standard',
                                                searchedName.group(1),
                                                searchedName.group(2)
                                             ])
        if compoundOutputFileName is None:
            compoundOutputFileName = self.context.getConfiguration().getPrefixSummaryFile() + "-" + rawFileName


        return compoundOutputFileName


    def prepareDeleteRecord(self,recordToDelete):

        #nebis redords marked as deleted contain still a metadata section with a lot of rubbish we can throw away
        #look for an example in: notizen/examples.oai/aleph.nebis/nebis.deleted.indent.xml

        spReroDeletedRecordsToSubstitutePattern = self.pReroDeleteRecord.search(recordToDelete)
        if spReroDeletedRecordsToSubstitutePattern:
            toReturn= spReroDeletedRecordsToSubstitutePattern.group(1) + "</record>"
        else:
            #todo: write a message
            toReturn = recordToDelete

        return toReturn




class SingleImportFileProvider:

    def __init__(self,context):
        self.context = context


    def setFileName(self,fileName):
        self.fileName = fileName

    def getFileName(self):
        return self.fileName


    def createGenerator(self):
        emptyList = range(0)
        for i in emptyList:
            yield i



class PushFileProvider(SingleImportFileProvider):

    def __init__(self,context):
        SingleImportFileProvider.__init__(self,context)
        self.pCompleteNebisRecord =  re.compile('<ListRecords>(.*?)</ListRecords>',re.UNICODE | re.DOTALL)


    def setFileName(self,fileName):
        self.fileName = fileName

    def getFileName(self):
        return self.fileName

    def createGenerator(self):
        if self.fileName is None or len(self.fileName) == 0:
            yield SingleImportFileProvider.createGenerator(self)
        else:
            cPath = os.getcwd()

            os.chdir(self.context.getConfiguration().getClusteringDir())
            os.system("tar zxf " + " " + self.fileName)
            os.system("rm " + " " + self.fileName)

            os.chdir(cPath)

            for singleFile in glob.glob(self.context.getConfiguration().getClusteringDir() + os.sep + '*.xml'):

                tfile = open(singleFile,"r")
                contentSingleFile = "".join(tfile.readlines())
                nebisCompleteRecord = self.pCompleteNebisRecord.search(contentSingleFile)
                tfile.close()
                os.system("rm " + " " + singleFile)
                if nebisCompleteRecord:
                    yield nebisCompleteRecord.group(1)
                else:
                    raise Exception("push generator pattern didn't match the file in process")


class WebDavFileProvider(SingleImportFileProvider):

    def __init__(self,context,inputFileName):
        SingleImportFileProvider.__init__(self,context)
        #self.pIterSingleRecord = re.compile('<record><header .*?>.*?</metadata></record>',re.UNICODE | re.DOTALL | re.IGNORECASE | re.MULTILINE)
        self.pIterSingleRecord = re.compile('<record><header.*?>.*?</metadata></record>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.inputFileName = inputFileName


    def setFileName(self,fileName):
        self.fileName = fileName

    def getFileName(self):
        return self.fileName

    def createGenerator(self):


        workingDir = self.context.getConfiguration().getReroWorkingDir()
        tfile = open(workingDir + os.sep + self.inputFileName ,"r")
        contentSingleFile = "".join(tfile.readlines())
        tfile.close()
        iterator = self.pIterSingleRecord.finditer(contentSingleFile)

        numberOfRecords = 0

        for matchRecord in iterator:

            contentSingleRecord = matchRecord.group()
            numberOfRecords += 1

            yield contentSingleRecord

        if numberOfRecords == 0:
            raise Exception("WebdavGeerator didn't match any record")








if __name__ == '__main__':

    import os
    from swissbibMongoHarvesting import MongoDBHarvestingWrapper
    from swissbibHarvestingConfigs import HarvestingFilesConfigs
    from argparse import ArgumentParser


    __author__ = 'swissbib - UB Basel, Switzerland, Guenter Hipler'
    __copyright__ = "Copyright 2012, swissbib project"
    __credits__ = ["Tobias Viegener for co-developing the principal idea and requirements"]
    __license__ = "??"
    __version__ = "0.1"
    __maintainer__ = "Guenter Hipler"
    __email__ = "guenter.hipler@unibas.ch"
    __status__ = "in development"
    __description__ = """ bibliographic records pushed by ETH Zuerich should be analyzed
                        if there were already sent earlier and weren't changed in the meantime
                        ETH doesn't distinguish between records where the 'bibliographic edition' changed and records only
                        pushed because the availability status has changed. The last one aren't of any interest for swissbib
                        and should be filtered out so processing of these records by CBS  isn't necessary

                        additional values:
                         - better overview about the whole harvesting process. The status of single records
                         (when pushed, skipped because only availability status, send to CBS, ... is recorded as history)
                         requests are selected very quickly because the 'history-record' is stored. No big piles of single log files anymore
                         - in general ability to create statistics about the harvesting process
                         - single records could be analyzed for well-formed XML. If not well-formed they can be filtered out
                         - consolidation of used development tools. No mixture of larger shell scripts and Perl.
                          Perl should be replaced by Python which is a modern and widely used script language
                          (in the application as well as in the administration environment) not only appreciated
                          by older colleagues...
                         - collect experience with a document-NoSQL DB -> we have chosen MongoDB for the beginning
                        """


    oParser = None
    args = None
    sConfigs = None
    mongoWrapper = None
    rCollector = None
    startTime = None
    nebisClient = None

    try:


        #print sys.version_info
        oParser = ArgumentParser()
        oParser.add_argument("-c", "--config", dest="confFile")
        args = oParser.parse_args()


        sConfigs = HarvestingFilesConfigs(args.confFile)
        sConfigs.setApplicationDir(os.getcwd())


        rCollector = ResultCollector()

        startTime = datetime.now()

        appContext = ApplicationContext()
        appContext.setConfiguration(sConfigs)
        appContext.setResultCollector(rCollector)
        mongoWrapper = MongoDBHarvestingWrapper(applicationContext=appContext)

        appContext.setMongoWrapper(mongoWrapper)

        client = globals()[sConfigs.getFileProcessorType()](appContext)

        client.initialize()
        client.lookUpContent()

        client.preProcessContent()
        client.process()
        client.postProcessContent()


    except Exception as exception:

        if not appContext is None and  not appContext.getWriteContext() is None:
            appContext.getWriteContext().handleOperationAfterError(exType=exception,
                                                        message="Exception in FileProcessorImpl.py" )
        elif not appContext is None and  not appContext.getConfiguration() is None:

            logfile = open(appContext.getConfiguration().getErrorLogDir() + os.sep + appContext.getConfiguration().getErrorLogFile(),"a")
            message = ["no WriteContext after Error: Exception Handler",
                       str(exception)]
            logfile.write("\n".join(message))
            logfile.flush()
            logfile.close()
        else:

            print "no WriteContext after Error and Configuration is None: Exception Handler"
            print str(exception) + "\n"



    else:

        if not appContext.getWriteContext() is None:

            appContext.getWriteContext().setAndWriteConfigAfterSuccess()



            procMess = ["start time: " +  str( startTime),
                        "end time: " + str(datetime.now()),
                        "Nebis file(s) processed: " + "##".join(rCollector.getProcessedFile()),
                        "logged skipped records (if true): " + sConfigs.getSummaryContentFileSkipped(),
                        "records deleted: " + str(rCollector.getRecordsDeleted()) ,
                        "records skipped: " + str(rCollector.getRecordsSkipped()) ,
                        "records parse error: " + str(rCollector.getRecordsparseError()) ,
                        "records to cbs inserted: " + str(rCollector.getRecordsToCBSInserted()) ,
                        "records to cbs updated: " + str(rCollector.getRecordsToCBSUpdated()) ,
                        "records to cbs (without skip mechanism - configuration!): " + str(rCollector.getRecordsToCBSNoSkip()),
                        "\n"]



            appContext.getWriteContext().writeLog(header="Import file (push or webdav) summary",message=procMess )

        elif not appContext is None and  not appContext.getConfiguration() is None:


            procMess = ["WriteContext is None - after process finished regularly",
            "start time: " +  str( startTime),
            "end time: " + str(datetime.now()),
            "Nebis file(s) processed: " + "##".join(rCollector.getProcessedFile()),
            "logged skipped records (if true): " + sConfigs.getSummaryContentFileSkipped(),
            "records deleted: " + str(rCollector.getRecordsDeleted()) ,
            "records skipped: " + str(rCollector.getRecordsSkipped()) ,
            "records parse error: " + str(rCollector.getRecordsparseError()) ,
            "records to cbs inserted: " + str(rCollector.getRecordsToCBSInserted()) ,
            "records to cbs updated: " + str(rCollector.getRecordsToCBSUpdated()) ,
            "records to cbs (without skip mechanism - configuration!): " + str(rCollector.getRecordsToCBSNoSkip()),
            "\n"]

            logfile = open(appContext.getConfiguration().getProcessLogDir() + os.sep + appContext.getConfiguration().getProcessLogFile(),"a")
            logfile.write("\n".join(procMess))
            logfile.flush()
            logfile.close()

        else:
            procMess = ["WriteContext is None and Configuration is None after process finished regularly",
            "going cto use logfile channel directly",
            "start time: " +  str( startTime),
            "end time: " + str(datetime.now()),
            "Nebis file(s) processed: " + "##".join(rCollector.getProcessedFile()),
            "logged skipped records (if true): " + sConfigs.getSummaryContentFileSkipped(),
            "records deleted: " + str(rCollector.getRecordsDeleted()) ,
            "records skipped: " + str(rCollector.getRecordsSkipped()) ,
            "records parse error: " + str(rCollector.getRecordsparseError()) ,
            "records to cbs inserted: " + str(rCollector.getRecordsToCBSInserted()) ,
            "records to cbs updated: " + str(rCollector.getRecordsToCBSUpdated()) ,
            "records to cbs (without skip mechanism - configuration!): " + str(rCollector.getRecordsToCBSNoSkip()),
            "\n"]

            print "\n".join(procMess)


            #appContext.getWriteContext().writeErrorLog(message= "ResultCollector was None - Why?")
            #appContext.getWriteContext().writeLog(message= "ResultCollector was None - Why?")


    if not mongoWrapper is None:
        mongoWrapper.closeResources()


