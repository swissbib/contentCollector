# -*- coding: utf-8 -*-


import copy

import hashlib
#import re
import os
import re
import xml
from oaipmh.client import Client, WAIT_MAX, WAIT_DEFAULT, Error, ResumptionListGenerator
from pyexpat import ExpatError
from oaipmh.datestamp import datetime_to_datestamp
import time
from swissbibHash import HashMarcContent, HashSwissBibMarcContent, HashDcContent, HashReroMarcContent
import xml.parsers.expat
from xml.parsers.expat import ParserCreate
from swissbibUtilities import ReadError, ErrorHashProcesing, SwissbibUtilities, ErrorMongoProcessing, AdministrationOperation
import swissbibUtilities
from datetime import datetime
import urllib2
from urllib import urlencode
from FileProcessorImpl import  ApplicationContext
from swissbibPreImportProcessor import SwissbibPreImportProcessor
from harvestingTasks import PersistRecordMongo,PersistDNBGNDRecordMongo
from Context import StoreNativeRecordContext, TaskContext

from testing import TestContent







__author__ = 'swissbib - GH, 2012-03 / 2012-04'



def retrieveFromUrlWaiting(request,
                           wait_max=WAIT_MAX, wait_default=WAIT_DEFAULT, config = None):
    """Get text from URL, handling 503 Retry-After.
    """
    for i in range(wait_max):
        try:

            #exclude any ProxHandler. seems that Python is looking for any ProxyConfiguration on the server
            #although there is a configuration in the proxy network settings of the host that no proxy should be used for the specific host of rero

            if config is not None and config.getProxy() is not None:
                proxy_handler = urllib2.ProxyHandler({'http':config.getProxy()})
            else:
                proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)
            urllib2.install_opener(opener)

            #f = urllib2.urlopen(request)
            urlConcatenated = request.get_full_url() + "?" + request.get_data()
            f = urllib2.urlopen(urlConcatenated)
            text = f.read()

            #errorLog = open("/swissbib/harvesting/ghrero/rerofile.xml","a")
            #errorLog.write(text)
            #errorLog.close()


            f.close()
            # we successfully opened without having to wait
            break
        except urllib2.HTTPError, e:
            if e.code == 503:
                try:
                    retryAfter = int(e.hdrs.get('Retry-After'))
                except TypeError:
                    retryAfter = None
                if retryAfter is None:
                    time.sleep(wait_default)
                else:
                    time.sleep(retryAfter)
            else:
                # reraise any other HTTP error
                raise
    else:
        raise Error, "Waited too often (more than %s times)" % wait_max
    return text



class SwissbibOAIClient(Client, SwissbibPreImportProcessor):

    def __init__(
            self, base_url, metadata_registry=None, applicationContext=None, dayGranularity=False, credentials=None):
        Client.__init__(self, base_url, metadata_registry, credentials)
        SwissbibPreImportProcessor.__init__(self,applicationContext)

        self._day_granularity = dayGranularity
        #self.writeContext = writeContext

        self.pIterSingleRecord = re.compile('<record>.*?</record>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.pResumptionToken = re.compile('<resumptionToken.*?>(.{1,}?)</resumptionToken>',re.UNICODE | re.DOTALL |re.IGNORECASE)
        self.harvestingErrorPattern = re.compile('<error .*?>.*?</error>',re.UNICODE | re.DOTALL |re.IGNORECASE)



        #self.utilities = SwissbibUtilities()



    def makeRequest(self, **kw):
        """Actually retrieve XML from the server.
        """
        # XXX include From header?

        paramDic = copy.deepcopy(kw)
        paramDic["baseURL"] = self._base_url


        if kw.get('resumptionToken',None) is None:
            self.context.getResultCollector().setHarvestingParameter(paramDic)



        headers = {'User-Agent': 'swissbib-oaiclient'}
        headers['Content-Type'] = 'text/xml'
        if self._credentials is not None:
            headers['Authorization'] = 'Basic ' + self._credentials.strip()

        request = urllib2.Request(
            self._base_url, data=urlencode(kw))
        return retrieveFromUrlWaiting(request,config=self.context.getConfiguration())


    def makeRequestErrorHandling(self, **kw):

        #later we only want to store the first OAI request - not all the subsequent requests with resumptionToken
        if kw.get('resumptionToken',None) is None:
            self.context.getResultCollector().setHarvestingParameter(kw)

        response = self.makeRequest(**kw)
        #operation = swissbibUtilities.AdministrationOperation()
        #response = operation.getTestRecord()



        #errorP = re.compile('<error .*?>.*?</error>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        #self.utilities.getHarvestingErrorPattern()

        errorInResonse = self.harvestingErrorPattern.search(response)


        if errorInResonse:

            operation = swissbibUtilities.AdministrationOperation()
            errMess = operation.formatException(exceptionType=None,
                message="response in 'makeRequestErrorHandling' contains error",
                additionalText=response)

            operation.writeErrorLogHarvesting( configsHarvesting=self.context.getConfiguration(),
                                                resultCollector=None,
                                                message= "".join(errMess))
            operation = None

            raise ReadError(errorInResonse.group())

        return response




    def buildRecords(self,
                     metadata_prefix, namespaces, metadata_registry, response):


        #recordList = []

        try:


            if self.context.getConfiguration().getDebugging():
                self.context.getWriteContext().writeLog(header=["Debugging harvested Records:"],message=[response])


            iterator = self.pIterSingleRecord.finditer(response)

            for matchRecord in iterator:

                contentSingleRecord = matchRecord.group()
                recordId = self.getRecordId(contentSingleRecord)

                recordDeleted = self.isDeleteRecord(contentSingleRecord)
                if recordDeleted:
                    contentSingleRecord = self.prepareDeleteRecord(contentSingleRecord)

                #todo: muss ich hier eine Transformation des namespaces bei einigen sourcen einbauen?

                substituteChars = self.context.getConfiguration().getSubstituteCharacters()
                if not substituteChars is None:
                    contentSingleRecord = re.sub(substituteChars," ",contentSingleRecord)

                try:
                    self.parseWellFormed(contentSingleRecord)
                except ExpatError as expatInst:
                    self.context.getWriteContext().writeErrorLog(header=["not well formed record"],message=[str(expatInst), contentSingleRecord])
                    self.context.getResultCollector().addRecordsparseError(1)
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

                        self.context.getWriteContext().writeErrorLog(header=["error while processing a task"],message=[str(pythonBaseException), contentSingleRecord])
                        continue




        except Exception as pythonBaseException:
            raise pythonBaseException

        #finally:

        searchedToken = self.pResumptionToken.search(response)
        resumptionToken = None
        if searchedToken:
            resumptionToken = searchedToken.group(1)
            if self.context.getConfiguration().isWriteResumptionToken():
                resumptionLog = open(self.context.getConfiguration().getResumptionTokenLogDir() + os.sep +  self.context.getConfiguration().getResumptionTokenLogFile(),"a")
                resumptionLog.write('{:%Y%m%d%H%M%S}'.format(datetime.now()) + " resumptionToken: " +  resumptionToken + "\n")
                resumptionLog.close()


        #singleStringAsList = ["".join(recordList)]
        #GH: in the first versions single records were collected
        singleStringAsList = [""]

        #raise Exception("omly a test")
        return singleStringAsList,resumptionToken







    def handleVerb(self, verb, kw):
        # validate kw first

        #ich musste handleverb ueberschreiben, da ich die Validation mit einer speziellen Spezifikation fuer rero aufrufen muss
        #source=uc in ListRecords
        swissbibUtilities.validateArguments(verb, kw)
        # encode datetimes as datestamps
        from_ = kw.get('from_')
        if from_ is not None:
            # turn it into 'from', not 'from_' before doing actual request
            kw['from'] = datetime_to_datestamp(from_,
                self._day_granularity)
        if 'from_' in kw:
            # always remove it from the kw, no matter whether it be None or not
            del kw['from_']

        until = kw.get('until_')
        if until is not None:
            kw['until'] = datetime_to_datestamp(until,
                self._day_granularity)
        if 'until_' in kw:
            # until is None but is explicitly in kw, remove it
            del kw['until_']

        if 'source' in kw and  kw.get('source') is None:
            del kw['source']
        if 'resumptionToken' in kw and kw.get('resumptionToken') is None:
            del kw['resumptionToken']
        if 'set' in kw and kw.get('set') is None:
            del kw['set']





        # now call underlying implementation
        method_name = verb + '_impl'
        return getattr(self, method_name)(
            kw, self.makeRequestErrorHandling(verb=verb, **kw))


    def ListRecords_impl(self, args, tree):
        namespaces = self.getNamespaces()

        if 'metadataPrefix' in args:
            metadata_prefix = args['metadataPrefix']
        else:
            metadata_prefix = None
        #metadata_prefix = args['metadataPrefix']
        metadata_registry = self._metadata_registry
        def firstBatch():
            return self.buildRecords(
                metadata_prefix, namespaces,
                metadata_registry, tree)
        def nextBatch(token):

            self.context.getConfiguration().setLastResumptionToken(token)
            #metadata_registry.getHarvestingConfigs().setLastResumptionToken(token)

            if not self.context.getConfiguration().getSource() is None:
            #if not metadata_registry.getHarvestingConfigs().getSource() is None:

                tree = self.makeRequestErrorHandling(
                    verb='ListRecords',
                    resumptionToken=token,
                    source=self.context.getConfiguration().getSource())

            else:
                tree = self.makeRequestErrorHandling(
                    verb='ListRecords',
                    resumptionToken=token)

            return self.buildRecords(
                metadata_prefix, namespaces,
                metadata_registry, tree)

        return ResumptionListGenerator(firstBatch, nextBatch)

