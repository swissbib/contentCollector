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


import requests







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
            httpsHandler = urllib2.HTTPSHandler()

            opener = urllib2.build_opener()
            urllib2.install_opener(opener)

            #f = urllib2.urlopen(request)
            urlConcatenated = request.get_full_url() + "?" + request.get_data()
            f = urllib2.urlopen(urlConcatenated)
            text = f.read().encode('utf-8')

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



def retrieveFromUrlWaitingRequests(wait_max=WAIT_MAX, wait_default=WAIT_DEFAULT, baseURL=None, params = None, context = None):

    numberOfRequests = 1
    for i in range(wait_max):
        try:

            if not context is None and context.getConfiguration().getProxy() is not None:
                proxies = {
                  "http": context.getConfiguration().getProxy(),
                  "https": context.getConfiguration().getProxy(),
                }
                result  = requests.get(baseURL,params=params,proxies=proxies)
            else:
                #siehe auch hier
                #http://docs.python-requests.org/en/latest/user/advanced/
                #ich brauche noch die Unterstützung von Proxies
                result  = requests.get(baseURL,params=params)
                #result.encoding = 'ISO-8859-1'


            #Background handling requests library https://media.readthedocs.org/pdf/requests/v2.0-0/requests.pdf see encodings
            #excerpt encoding chapter:
            #When you receive a response, Requests makes a guess at the encoding to use for decoding the response when you call
            #the Response.text method. Requests will first check for an encoding in the HTTP header, and if none is present, will use
            #charade to attempt to guess the encoding. The only time Requests will not do this is if no explicit charset is present in the HTTP headers
            #and the Content-Type header contains text. In this situation, RFC 2616 specifies that the default charset must be ISO-8859-1 . Requests follows the specification in this case. If you require a different encoding,
            # you can manually set the Response.encoding property, or use the raw Response.content

            #headers = result.headers
            #e = result.encoding
            #text = result.text
            text = result.content
            #test = result.encoding

            #mytype = type(contentSingleRecord)
            #why do we have to do this with Alma content because content from Aleph is signed as unicode too!
            #but it works!
            # Encode unicode data as utf-8 if configured.
            #ab Version 2.3 requests wird scheins ein automatisches encoding angenommen - was da genau passiert muss ich mir noch ansehen
            if not context is None and  context.getConfiguration().getEncodeUnicodeAsUTF8():
                text = text.encode('utf-8')



            break

        except requests.ConnectionError, ex:
            if not context is None:
                context.getWriteContext().writeErrorLog(header=["error while trying to connect to remote system (ConnectionError) (total number of requests {0}".format(numberOfRequests)],message=[str(ex)])
            numberOfRequests += 1
            continue
        except requests.Timeout, timeEx:
            if not context is None:
                context.getWriteContext().writeErrorLog(header=["error while trying to connect to remote system (TimeOutError) (total number of requests {0}".format(numberOfRequests)],message=[str(ex)])
            numberOfRequests += 1
            continue
        except Exception,ex:
            if not context is None:
                context.getWriteContext().writeErrorLog(header=["error while trying to connect to remote system (BaseError) (total number of requests {0}".format(numberOfRequests)],message=[str(ex)])
            numberOfRequests += 1
            continue

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

        #was ist hier anders als bei Aleph!
        if not self.context.getConfiguration().getIteratorOAIStructure() is None:
            self.pIterSingleRecord = re.compile(self.context.getConfiguration().getIteratorOAIStructure(),re.UNICODE | re.DOTALL | re.IGNORECASE)
        else:
            self.pIterSingleRecord = re.compile('<record>.*?</record>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        #GH: 16.10.2015 this works for Nebis because we are looking for the outer 'shell' of all <record>...</record> not qualified with additional namespaces.
        #we can use this for deleted as well as for full records. Compare example in exampleContentStructures/alma/deletedAndUpdatedRecords.xml
        #with Aleph this isn't as easy..  .
        #self.pIterSingleRecordNebis = re.compile('<record>.*?</record>',re.UNICODE | re.DOTALL | re.IGNORECASE)


        self.pResumptionToken = re.compile('<resumptionToken.*?>(.{1,}?)</resumptionToken>',re.UNICODE | re.DOTALL |re.IGNORECASE)
        self.harvestingErrorPattern = re.compile('(<error.*?>.*?</error>|<html>.*?HTTP.*?Status.*?4\d\d)',re.UNICODE | re.DOTALL |re.IGNORECASE)



        #self.utilities = SwissbibUtilities()



    def makeRequest(self, **kw):
        paramDic = copy.deepcopy(kw)
        #paramDic["baseURL"] = self._base_url


        if kw.get('resumptionToken',None) is None:
            self.context.getResultCollector().setHarvestingParameter(paramDic)



        headers = {'User-Agent': 'swissbib-oaiclient'}
        headers['Content-Type'] = 'text/xml'
        if self._credentials is not None:
            headers['Authorization'] = 'Basic ' + self._credentials.strip()


        #request = urllib2.Request(
        #    self._base_url, data=urlencode(kw))
        #return retrieveFromUrlWaiting(request,config=self.context.getConfiguration())
        #we switch to the requests module
        return retrieveFromUrlWaitingRequests(baseURL=self._base_url,params=paramDic,context=self.context)


    def makeRequestErrorHandling(self, **kw):

        #later we only want to store the first OAI request - not all the subsequent requests with resumptionToken
        if kw.get('resumptionToken',None) is None:
            self.context.getResultCollector().setHarvestingParameter(kw)

        response = self.makeRequest(**kw)

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

            #Unicode (short): http://www.carlosble.com/2010/12/understanding-python-and-unicode/

            if self.context.getConfiguration().getDebugging():
                self.context.getWriteContext().writeLog(header=["Debugging harvested Records:"],message=[response])



            iterator = self.pIterSingleRecord.finditer(response)

            for matchRecord in iterator:

                contentSingleRecord = matchRecord.group()


                #already in requests - otherwise parsing of errors isn't possible
                #mytype = type(contentSingleRecord)
                #why do we have to do this with Alma content because content from Aleph is signed as unicode too!
                #but it works!
                # Encode unicode data as utf-8 if configured.
                #if self.context.getConfiguration().getEncodeUnicodeAsUTF8():
                #    contentSingleRecord = contentSingleRecord.encode('utf-8')

                recordDeleted = self.isDeleteRecord(contentSingleRecord)
                if self.context.getConfiguration().isTransformExLibrisNStructureForCBS() and not recordDeleted:
                    try:
                        contentSingleRecord = self.transformRecordNamespace(contentSingleRecord)

                    except Exception as transformException:
                        self.context.getWriteContext().writeErrorLog(header=["error while transforming the namespace structure of record"],message=[str(transformException), contentSingleRecord])
                        continue


                #http://stackoverflow.com/questions/3375238/typeerror-writelines-argument-must-be-a-sequence-of-strings (kann ein bisschen helfen)
                #http://stackoverflow.com/questions/5141559/unicodeencodeerror-ascii-codec-cant-encode-character-u-xef-in-position-0
                #http://nedbatchelder.com/text/unipain.html Videos anschauen!
                #http://stackoverflow.com/questions/19833440/unicodeencodeerror-ascii-codec-cant-encode-character-u-xe9-in-position-7 (Hinweise zu Tutoril)
                #Alma link
                #https://eu.alma.exlibrisgroup.com/view/oai/41BIG_INST/OAI-script?verb=ListRecords&metadataPrefix=marc21&set=BIG_Test&from=1999-01-01T00:00:00Z

                #http://www.pythoncentral.io/python-unicode-encode-decode-strings-python-2x/


                #gute slides
                #http://farmdev.com/talks/unicode/
                #http://blog.etianen.com/blog/2013/10/05/python-unicode-streams/



                #contentSingleRecord = getTestRecord()
                recordId = self.getRecordId(contentSingleRecord)


                if recordDeleted:
                    contentSingleRecord = self.prepareDeleteRecord(contentSingleRecord)

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
                    #attention: we use the file.writelines function which needs Strings - no unicode!
                    self.context.getWriteContext().writeItem(contentSingleRecord)


                self.context.getResultCollector().setIncrementProcessedRecordNoFurtherDetails()
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



def getTestRecord ():
    return """
    <record>
        <header>
            <identifier>oai:aleph.unibas.ch:DSV11-000084670</identifier>
            <datestamp>2013-11-29T00:19:05Z</datestamp>
            <setSpec>SWISSBIB-DSV11-OAI</setSpec>
        </header>
        <metadata>
            <marc:record xmlns:marc="http://www.loc.gov/MARC21/slim"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://www.loc.gov/MARC21/slim
http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
                <marc:leader>00370nz a2200097n 4500</marc:leader>
                <marc:controlfield tag="FMT">AU</marc:controlfield>
                <marc:controlfield tag="LDR">00370nz a2200097n 4500</marc:controlfield>
                <marc:controlfield tag="008">990909 az ab n </marc:controlfield>
                <marc:datafield tag="040" ind1=" " ind2=" ">
                    <marc:subfield code="a">SzZuIDS BS/BE</marc:subfield>
                    <marc:subfield code="b">ger</marc:subfield>
                </marc:datafield>
                <marc:datafield tag="090" ind1=" " ind2=" ">
                    <marc:subfield code="a">2638813</marc:subfield>
                    <marc:subfield code="b">DSV</marc:subfield>
                </marc:datafield>
                <marc:datafield tag="110" ind1=" " ind2=" ">
                    <marc:subfield code="a">Johannes Kepler-Universität (Linz)</marc:subfield>
                    <marc:subfield code="b">Abteilung für politische soziologie und
                        Entwicklungsforschung</marc:subfield>
                </marc:datafield>
                <marc:datafield tag="667" ind1=" " ind2=" ">
                    <marc:subfield code="a">Autoritätsaufnahme per Programm erstellt (aus SIBIL
                        0455425).</marc:subfield>
                    <marc:subfield code="5">09.09.1999/BED</marc:subfield>
                </marc:datafield>
                <marc:controlfield tag="001">000084670</marc:controlfield>
            </marc:record>
        </metadata>
    </record>
    """