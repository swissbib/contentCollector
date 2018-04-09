# -*- coding: utf-8 -*-
from lxml import etree
import StringIO

from swissbibUtilities import ErrorMongoProcessing
import sys
import zlib
#from pymongo.binary import Binary
from bson.binary import Binary
from datetime import datetime

from xml.sax.handler import ContentHandler
import xml.sax
import re
import xml.dom.minidom
from Context import ApplicationContext, StoreNativeRecordContext

__author__ = 'swissbib'



class HarvestingTask():

    def __init__(self):
        pass


    def  processRecord(self, taskContext=None):
        pass


    def finalize(self):
        pass
        #are there destructors in python??



class CleanUpServal(HarvestingTask):

    def __init__(self):
        self.substituteChars = '<record xmlns="http://www.openarchives.org/OAI/2.0/">\s*<header>'
        #self.substituteChars = '<record xmlns="http://www.openarchives.org/OAI/2.0/"><header>'
        HarvestingTask.__init__(self)
    def  processRecord(self,taskContext=None ):
        sR = taskContext.defaultRecord
        taskContext.defaultRecord = re.sub(self.substituteChars, '<record><header>', sR)


class CleanUpHemu(HarvestingTask):

    def __init__(self):
        self.subCollectionAttribute = '<collection xmlns='
        self.subRecordOpen = '<record>\s*<leader>'
        self.subRecordClose = '</datafield>\s*</record>'


        #self.substituteChars = '<re    cord xmlns="http://www.openarchives.org/OAI/2.0/"><header>'
        HarvestingTask.__init__(self)
    def  processRecord(self,taskContext=None ):
        sR = taskContext.defaultRecord
        newRecord1 = re.sub(self.subCollectionAttribute, '<collection xmlns:marc=', sR)
        newRecord2 = re.sub(self.subRecordOpen, '<marc:record><leader>', newRecord1)
        taskContext.defaultRecord = re.sub(self.subRecordClose, '</datafield></marc:record>', newRecord2)



class PersistRecordMongo(HarvestingTask) :

    def __init__(self):
        HarvestingTask.__init__(self)
        #HarvestingTask.__init__(self,configs)


        #self.hashType = None
        #for child in element:
        #    if child.tag == "persistHost":
        #        self.persistHost = child.text
        #    elif child.tag == "persistPort":
        #        self.persistPort = child.text
        #    elif child.tag == "persistDB":
        #        self.persistDB = child.text
        #    elif child.tag == "persistCollection":
        #        self.persistCollection = child.text

        #self.connection = Connection(self.persistHost)
        #self.db = self.connection[self.persistDB]
        #if not self.persistCollection is None:
        #    self.collectionRecords = self.db[self.persistCollection]



    #def  processRecord(self, record, rid = None ,configs = None, dbWrapper = None ):
    def  processRecord(self,taskContext=None ):
        #todo: search for recordID if None -> use HasType

        #double check isn't necessary as long these plugins are only used by myself
        #if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        isDeleted = taskContext.isDeleted()
        recordTimestamp = taskContext.getRecordTimestamp()

        if not recordTimestamp is None:
            try:
                recordTimestamp = datetime.strptime(recordTimestamp,"%Y-%m-%dT%H:%M:%SZ")
            except:
                recordTimestamp = None


        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


            mongoRecord = tCollection.find_one({"_id": rid})

            binary = Binary( zlib.compress(record,9))

            if not mongoRecord:

                #newdeleted are records which were sent from the repository marked as deleted but weren't fetched by swissbib before (so not in the nativeSourcesDB)
                #normally this shouldn't happen but might be possible and a hint to ask for the background
                if isDeleted:
                    taskContext.getResultCollector().addRecordsDeleted(1)
                    status = "newdeleted"
                else:
                    status = "new"
                    taskContext.getResultCollector().addRecordsToCBSInserted(1)

                if not recordTimestamp is None:
                    newRecord = {"_id":rid,
                                 "datum":str(datetime.now())[:10],
                                 "record":binary,
                                 "status":status,
                                 "recordTimestamp":recordTimestamp
                    }
                else:
                    newRecord = {"_id": rid,
                                 "datum": str(datetime.now())[:10],
                                 "record": binary,
                                 "status": status,
                                 }

                tCollection.insert(newRecord)

            else:
                if isDeleted:
                    status = "deleted"
                    taskContext.getResultCollector().addRecordsDeleted(1)
                else:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)

                if not recordTimestamp is None:
                    mongoRecord["record"] = binary
                    mongoRecord["status"] = status
                    mongoRecord["datum"] = str(datetime.now())[:10]
                    mongoRecord["recordTimestamp"] = recordTimestamp
                else:
                    mongoRecord["record"] = binary
                    mongoRecord["status"] = status
                    mongoRecord["datum"] = str(datetime.now())[:10]

                #save is deprecated  in pymongo version > 3
                #tCollection.save(mongoRecord)
                tCollection.replace_one({"_id":rid }, mongoRecord)
                #count = result.matched_count
                #modified = result.modified_count


        except:
            message = ["error while persisting record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            raise ErrorMongoProcessing(message)


    def beispielLesenEinesRecord(self):

    #test = self.collectionRecords.find()

    #for document in test:
    #    r = document["record"]
    #    lesbar = zlib.decompress(r)
    #    print dict(r)
        pass



class PersistDNBGNDRecordMongo(PersistRecordMongo):

    def __init__(self):
        PersistRecordMongo.__init__(self)
        self.pHasMetastructure = re.compile('<header><identifier>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.pCoreRecord = re.compile('.*?(<record type="Authority".*?</record>).*?</metadata>.*?</record>.*',re.UNICODE | re.DOTALL | re.IGNORECASE)

    def  processRecord(self, taskContext=None ):
        #todo: search for recordID if None -> use HasType
        #if rid is None or dbWrapper is None:
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: id of record must not be None and dbWrapper must not be None")

        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistDNBGNDRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        sMetaStrcuture = self.pHasMetastructure.search(record)
        if sMetaStrcuture:

            sCoreRecord = self.pCoreRecord.search(record)
            if not sCoreRecord is None:
                record = sCoreRecord.group(1)
            else:
                #this should not happen!
                message = ["OAI metastructure was found but was not able to grep the core record\n",
                           "docid: ", rid,
                           "record: ", record]
                raise ErrorMongoProcessing(message)


        isDeleted = taskContext.isDeleted()

        recordTimestamp = taskContext.getRecordTimestamp()

        if not recordTimestamp is None:
            try:
                recordTimestamp = datetime.strptime(recordTimestamp, "%Y-%m-%dT%H:%M:%SZ")
            except:
                recordTimestamp = None

        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

            status = None
            #if re.search("status=\"deleted\"",record,re.UNICODE | re.DOTALL):
            if isDeleted:

                taskContext.getResultCollector().addRecordsDeleted(1)

                deleteStructure = {"_id":rid}
                tCollection.remove(deleteStructure)
                return


            else:
                #cGNDContent = CollectGNDContent()
                cGNDContent = CollectGNDContentNoNamespace()
                xml.sax.parseString("".join(record), cGNDContent)

                selectedGNDFields = cGNDContent.getSelectedValues()
                selectedMACSFields = cGNDContent.getSelectedMACSValues()

                #tId = result["id"]
                #dbid and gndid has to be deleted in the GNDFieldsValueStructure
                dbid = selectedGNDFields["dbid"]
                gndid = selectedGNDFields["gndid"]

                selectedGNDFields.pop("dbid")
                selectedGNDFields.pop("gndid")

            mongoRecord = tCollection.find_one({"_id": rid})
            binary = Binary( zlib.compress(record,9))





            if not mongoRecord:
                if status is None:
                    status = "new"
                    taskContext.getResultCollector().addRecordsToCBSInserted(1)

                if not recordTimestamp is None:

                    newRecord = {"_id":rid,
                                 "datum":str(datetime.now())[:10],
                                 "gndid": gndid,
                                 "dbid" : dbid,
                                 "record":binary,
                                 "gndfields":selectedGNDFields,
                                 "macsfields" : selectedMACSFields,
                                 "status":status,
                                 "recordTimestamp": recordTimestamp
                                }
                else:
                    newRecord = {"_id":rid,
                                 "datum":str(datetime.now())[:10],
                                 "gndid": gndid,
                                 "dbid" : dbid,
                                 "record":binary,
                                 "gndfields":selectedGNDFields,
                                 "macsfields" : selectedMACSFields,
                                 "status":status
                                 }

                tCollection.insert(newRecord)

            else:

                if status is None:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)


                mongoRecord["record"] = binary
                mongoRecord["gndid"] = gndid
                mongoRecord["dbid"] = dbid
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]
                mongoRecord["gndfields"] = selectedGNDFields
                mongoRecord["macsfields"] = selectedMACSFields

                if not recordTimestamp is None:
                    mongoRecord["recordTimestamp"] = recordTimestamp

                #tCollection.save(mongoRecord,safe=True)
                tCollection.replace_one({"_id": rid}, mongoRecord)


        except Exception as tException:


            print "fehler in record"
            print str(tException)
            print record

            message = ["error while persisting gnd record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            #raise ErrorMongoProcessing(message)

class PersistNLMongo(PersistRecordMongo):


    def __init__(self):
        self.doctypePattern = re.compile('<!DOCTYPE.*?>',re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.articleStructure = re.compile('.*?(<article .*?</article>).*',re.UNICODE | re.DOTALL | re.IGNORECASE)
        PersistRecordMongo.__init__(self)

    def  processRecord(self, taskContext=None ):
        jatsRecord = taskContext.getRecord()
        modsRecord = taskContext.getModsRecord()
        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()

        isDeleted = taskContext.isDeleted()

        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


            mongoRecord = tCollection.find_one({"_id": rid})
            jatsBinary = Binary( zlib.compress(jatsRecord,9))
            modsBinary = Binary( zlib.compress(modsRecord,9))

            recordTree=etree.fromstring(jatsRecord)

            # Get year from XML
            xpathGetPYear = "//pub-date[@pub-type='ppub']/year"
            xpathGetEYear = "//pub-date[@pub-type='epub']/year"
            xpathGetYear = "//pub-date/year"
            xpathCopyrightYear= "//copyright-year"

            resultPYear = recordTree.xpath(xpathGetPYear)
            resultEYear = recordTree.xpath(xpathGetEYear)
            resultYear = recordTree.xpath(xpathGetYear)
            resultCopyrightYear = recordTree.xpath(xpathCopyrightYear)

            year=0
            if len(resultPYear) > 0 :
                year=int(resultPYear[0].text)
            elif len(resultEYear) > 0:
                year=int(resultEYear[0].text)
            elif len(resultYear) > 0:
                year=int(resultYear[0].text)
            elif len(resultCopyrightYear) > 0:
                year=int(resultCopyrightYear[0].text)

            if not mongoRecord:
                #record isn't in database so far
                newRecord = {"_id":rid,
                             "datum":str(datetime.now())[:10],
                             "year":year,
                             "status": "new",
                             "jatsRecord":jatsBinary,
                             "modsRecord": modsBinary
                            }
                tCollection.insert(newRecord)
                taskContext.getResultCollector().addRecordsToCBSInserted(1)

            else:
                #there is already a record with the current id in the database
                if isDeleted:
                    status = "deleted"
                    taskContext.getResultCollector().addRecordsDeleted(1)

                else:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)

                mongoRecord["year"] = year
                mongoRecord["jatsRecord"] = jatsBinary
                mongoRecord["modsRecord"] = modsBinary
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]

                #tCollection.save(mongoRecord, safe=True)
                tCollection.replace_one({"_id": rid}, mongoRecord)


        except Exception as tException:
            #todo: do something meaningful with the exception
            print tException


class PersistSpringerNLMongo(PersistNLMongo):

    def __init__(self):
        # the springer id of the journals which are part of the contract
        self.nationalLicencesJournals = (
            3, #Journal für Verbraucherschutz und Lebensmittelsicherheit
            4, #Nexus Network Journal
            5, #Archivum Immunologiae et Therapiae Experimentalis
            6, #Advances in Applied Clifford Algebras
            9, #Mediterranean Journal of Mathematics
            10, #Aequationes mathematicae
            11, #Inflammation Research
            12, #Algebra universalis
            13, #Archiv der Mathematik
            15, #Eclogae Geologicae Helvetiae
            15, #Swiss Journal of Geosciences
            16, #Physics in Perspective
            18, #Cellular and Molecular Life Sciences
            20, #Integral Equations and Operator Theory
            21, #Journal of Mathematical Fluid Mechanics
            22, #Journal of Geometry
            23, #Annales Henri Poincaré
            24, #Pure and Applied Geophysics
            25, #Results in Mathematics
            26, #Annals of Combinatorics
            27, #Aquatic Sciences (= Aquatic Science)
            28, #Journal of Evolution Equations
            29, #Selecta Mathematica
            30, #Nonlinear Differential Equations and Applications NoDEA
            31, #Transformation Groups
            32, #Milan Journal of Mathematics
            33, #Zeitschrift für angewandte Mathematik und Physik
            34, #Circuits, Systems, and Signal Processing
            35, #Alpine Botany (= Botanica helvetica)
            35, #Botanica helvetica (s. Alpine Botany)
            37, #computational complexity
            38, #International Journal of Public Health
            39, #Geometric and Functional Analysis
            40, #Insectes Sociaux
            41, #Journal of Fourier Analysis and Applications
            44, #Medicinal Chemistry Research
            48, #NTM Zeitschrift für Geschichte der Wissenschaften, Technik und Medizin
            49, #Chemoecology
            53, #Coloproctology
            56, #Journal of Orofacial Orthopedics / Fortschritte der Kieferorthopädie
            58, #Heilberufe
            59, #Herz
            60, #HNO Nachrichten
            62, #Clinical Neuroradiology (former Klinische Neuroradiologie)
            63, #Medizinische Klinik - Intensivmedizin und Notfallmedizin (= Medizinische Klinik)
            63, #Medizinische Klinik (s. Medizinische Klinik - Intensivmedizin und Notfallmedizi)
            64, #Operative Orthopädie und Traumatologie
            65, #Orthopedics Traumatology
            66, #Strahlentherapie und Onkologie
            68, #European Journal of Trauma and Emergency Surgery
            101, #Der Anaesthesist
            103, #Bundesgesundheitsblatt - Gesundheitsforschung - Gesundheitsschutz
            104, #Der Chirurg
            105, #Der Hautarzt
            106, #HNO
            107, #European Journal of Wood and Wood Products (= Holz als Roh- und Werkstoff)
            108, #Der Internist
            109, #Journal of Molecular Medicine
            112, #Monatsschrift Kinderheilkunde
            113, #Der Unfallchirurg
            114, #The Science of Nature (bis 2015: Die Naturwissenschaften, 0028-1042, 1432-1904)
            115, #Der Nervenarzt
            117, #Der Radiologe
            120, #Der Urologe (A)
            122, #Theoretical and Applied Genetics
            125, #Diabetologia
            126, #Mineralium Deposita
            127, #Social Psychiatry and Psychiatric Epidemiology
            128, #Bulletin of Environmental Contamination and Toxicology
            129, #Der Gynäkologe
            132, #Der Orthopäde
            134, #Intensive Care Medicine
            135, #Journal Materials Engineering
            136, #Journal Heat Treating
            138, #Machine Vision and Applications
            142, #Arthroskopie
            145, #Journal of Cryptology
            146, #AI & SOCIETY
            148, #Journal of Population Economics
            153, #Archive for Mathematical Logic
            158, #Structural and Multidisciplinary Optimization
            159, #The Astronomy and Astrophysics Review
            161, #Continuum Mechanics and Thermodynamics
            162, #Theoretical and Computational Fluid Dynamics
            163, #Research in Engineering Design
            165, #Formal Aspects of Computing
            167, #Knee Surgery, Sports Traumatology, Arthroscopy
            168, #The Annals of Regional Science
            170, #International Journal of Advanced Manufacturing Technology
            180, #Computational Statistics
            181, #Empirical Economics
            182, #International Journal of Game Theory
            184, #Metrika
            186, #Mathematical Methods of Operations Research
            187, #Journal of Management Control (former: Zeitschrift für Planung & Unternehmenssteuerung)
            190, #Journal of Geodesy
            191, #Journal of Evolutionary Economics
            192, #International Urogynecology Journal
            193, #Shock Waves
            194, #Rechtsmedizin
            198, #Osteoporosis International
            199, #Economic Theory
            200, #Applicable Algebra in Engineering, Communication and Computing
            202, #Electrical Engineering
            203, #Archives of Microbiology
            204, #Archives of Toxicology
            205, #Archive for Rational Mechanics and Analysis
            208, #Mathematische Annalen
            209, #Mathematische Zeitschrift
            210, #Naunyn-Schmiedeberg's Archives of Pharmacology
            211, #Numerische Mathematik
            213, #Psychopharmacology
            214, #Theoretical Chemistry Accounts
            216, #Analytical and Bioanalytical Chemistry (former Fresenius' Journal of Analytical Chemistry)
            217, #European Food Research and Technology
            218, #Zeitschrift Physik A Hadrons nuclei
            220, #Communications in Mathematical Physics
            221, #Experimental Brain Research
            222, #Inventiones mathematicae
            223, #Calcified Tissue International
            224, #Theory of Computing Systems
            226, #Wood Science and Technology
            227, #Marine Biology
            228, #European Journal of Clinical Pharmacology
            229, #Manuscripta Mathematica
            231, #Heat and Mass Transfer
            232, #The Journal of Membrane Biology
            233, #Semigroup Forum
            234, #Neuroradiology
            236, #Acta Informatica
            238, #European Journal of Plastic Surgery
            239, #Journal of Molecular Evolution
            240, #Urolithiasis (früher: Urological Research)
            244, #Archives of Environmental Contamination and Toxicology
            245, #Applied Mathematics & Optimization
            246, #Pediatric Cardiology
            247, #Pediatric Radiology
            248, #Microbial Ecology
            249, #European Biophysics Journal
            251, #Immunogenetics
            253, #Applied Microbiology and Biotechnology
            254, #Environmental Geology
            256, #Skeletal Radiology
            257, #Zeitschrift Physik B Condensed Matter
            259, #European Journal of Nuclear Medicine and Molecular Imaging
            261, #Abdominal Radiology (Prior to Volume 41 (2016) published as “Abdominal Imaging”)
            262, #Cancer Immunology, Immunotherapy
            264, #International Orthopaedics
            265, #Behavioral Ecology and Sociobiology
            266, #Aesthetic Plastic Surgery
            267, #Environmental Management
            268, #World Journal of Surgery
            269, #Physics and Chemistry of Minerals
            270, #CardioVascular and Interventional Radiology
            271, #Irrigation Science
            276, #Surgical and Radiologic Anatomy
            277, #Annals of Hematology
            278, #Psychotherapeut
            280, #Cancer Chemotherapy and Pharmacology
            281, #Seminars in Immunopathology
            283, #The Mathematical Intelligencer
            284, #Current Microbiology
            285, #Journal of Mathematical Biology
            287, #Informatik-Spektrum
            288, #Zeitschrift Physik C Particles Fields
            289, #Polymer Bulletin
            290, #Urologic Radiology
            291, #OR Spectrum
            292, #Der Pathologe
            294, #Current Genetics
            296, #Rheumatology International
            299, #Plant Cell Reports
            300, #Polar Biology
            330, #European Radiology
            332, #Journal of Nonlinear Science
            334, #Vegetation History and Archaeobotany
            335, #Mammalian Genome
            337, #Manuelle Medizin
            338, #Coral Reefs
            339, #Applied Physics A
            340, #Applied Physics B
            343, #Chinese Journal of Oceanology and Limnology
            344, #Journal of Plant Growth Regulation
            345, #World Journal of Urology
            347, #Der Ophthalmologe
            348, #Experiments in Fluids
            350, #Medizinrecht (=MedR - Medizinrecht)
            354, #New Generation Computing
            355, #Social Choice and Welfare
            357, #Journal of Classification
            359, #Journal of Comparative Physiology A
            360, #Journal of Comparative Physiology B
            362, #Statistical Papers
            365, #Constructive Approximation
            366, #Engineering with Computers
            367, #Geo-Marine Letters
            371, #The Visual Computer
            373, #Graphs and Combinatorics
            374, #Biology and Fertility of Soils
            376, #Advances Atmospheric Sciences
            380, #Heart and Vessels
            381, #Child's Nervous System
            382, #Climate Dynamics
            383, #Pediatric Surgery International
            384, #International Journal of Colorectal Disease
            391, #Zeitschrift für Gerontologie und Geriatrie
            392, #Clinical Research in Cardiology (see Zeitschrift für Kardiologie)
            393, #Zeitschrift für Rheumatologie
            394, #European Journal of Nutrition
            395, #Basic Research in Cardiology
            396, #Colloid and Polymer Science
            397, #Rheologica Acta
            399, #Herzschrittmachertherapie + Elektrophysiologie
            401, #Acta Neuropathologica
            402, #Archives of Orthopaedic and Trauma Surgery
            403, #Archives of Dermatological Research
            404, #Archives of Gynecology and Obstetrics
            405, #European Archives of Oto-Rhino-Laryngology
            406, #European Archives of Psychiatry and Clinical Neuroscience
            407, #Archive for History of Exact Sciences
            408, #Lung
            410, #Contributions to Mineralogy and Petrology
            411, #Radiation and Environmental Biophysics
            412, #Chromosoma
            414, #International Journal of Legal Medicine
            415, #Journal of Neurology
            417, #Graefe's Archive for Clinical and Experimental Ophthalmology
            418, #Histochemistry and Cell Biology
            419, #Archive of Applied Mechanics
            420, #International Archives of Occupational and Environmental Health
            421, #European Journal of Applied Physiology
            422, #Biological Cybernetics
            423, #Langenbeck's Archives of Surgery
            424, #Pflügers Archiv - European Journal of Physiology
            425, #Planta
            426, #Psychological Research
            427, #Development Genes and Evolution
            428, #Virchows Archiv
            429, #Brain Structure and Function (=Anatomy and Embryology)
            430, #Medical Microbiology and Immunology
            431, #European Journal of Pediatrics
            432, #Journal of Cancer Research and Clinical Oncology
            433, #Research Experimental Medicine
            435, #Zoomorphology
            436, #Parasitology Research
            438, #Molecular Genetics and Genomics
            439, #Human Genetics
            440, #Probability Theory and Related Fields
            441, #Cell and Tissue Research
            442, #Oecologia
            443, #Virchows Archiv B Cell Pathology
            445, #Bulletin of Volcanology
            446, #Distributed Computing
            449, #Bioprocess and Biosystems Engineering
            450, #Computer Science - Research and Development (= Informatik - Forschung und Entwicklung)
            450, #Informatik - Forschung und Entwicklung (s. Computer Science - Research and Development)
            451, #Forum der Psychoanalyse
            453, #Algorithmica
            454, #Discrete & Computational Geometry
            455, #Dysphagia
            460, #Zeitschrift Physik D Atoms Molecules Clusters
            464, #Surgical Endoscopy
            466, #Computational Mechanics
            467, #Pediatric Nephrology
            468, #Trees
            477, #Stochastic Environmental Research and Risk Assessment
            481, #Ethik in der Medizin
            482, #Der Schmerz
            484, #International Journal of Biometeorology
            493, #Combinatorica
            497, #Plant Reproduction (früher: Sexual Plant Reproduction)
            498, #MCSS Mathematics of Control, Signals and Systems
            499, #Journal Materials Shaping Technology
            500, #Soft Computing
            501, #BHM Berg- und Hüttenmännische Monatshefte
            502, #e & i Elektrotechnik und Informationstechnik
            506, #Österreichische Wasser- und Abfallwirtschaft
            508, #Wiener klinische Wochenschrift
            520, #Supportive Care in Cancer
            521, #Neural Computing and Applications
            526, #Calculus of Variations and Partial Differential Equations
            530, #Multimedia Systems
            531, #International Journal of Earth Sciences
            535, #Journal of Gastroenterology
            540, #Journal of Anesthesia
            542, #Microsystem Technologies
            547, #International Journal Angiology
            548, #Standort
            550, #uwf UmweltWirtschaftsForum
            572, #Mycorrhiza
            574, #Bulletin of the Brazilian Mathematical Society
            580, #Comparative Clinical Pathology
            586, #European Spine Journal
            590, #European Journal of Orthopaedic Surgery & Traumatology
            591, #Mathematische Semesterberichte
            592, #Acta Diabetologica
            595, #Surgery Today
            599, #International Journal Clinical Laboratory Research
            601, #Few-Body Systems
            603, #Rock Mechanics and Rock Engineering
            604, #Microchimica Acta
            605, #Monatshefte für Mathematik
            606, #Plant Systematics and Evolution
            607, #Computing
            701, #Acta Neurochirurgica
            702, #Journal of Neural Transmission
            703, #Meteorology and Atmospheric Physics
            704, #Theoretical and Applied Climatology
            705, #Archives of Virology
            706, #Monatshefte für Chemie - Chemical Monthly
            707, #Acta Mechanica
            709, #Protoplasma
            710, #Mineralogy and Petrology
            712, #Journal of Economics
            717, #Spektrum der Augenheilkunde
            722, #Journal Neural Transmission Parkinson's Disease Dementia Section
            723, #Applied Magnetic Resonance
            726, #Amino Acids
            735, #ProCare
            737, #Archives of Women's Mental Health
            761, #Der Onkologe
            766, #Requirements Engineering
            767, #Grundwasser
            769, #Accreditation and Quality Assurance
            772, #Gefässchirurgie
            773, #Journal of Marine Science and Technology
            774, #Journal of Bone and Mineral Metabolism
            775, #JBIC Journal of Biological Inorganic Chemistry
            778, #The VLDB Journal
            779, #Personal and Ubiquitous Computing
            780, #Finance and Stochastics
            784, #Clinical Oral Investigations
            787, #European Child & Adolescent Psychiatry
            791, #Computing and Visualization in Science
            792, #Extremophiles
            795, #Medical Molecular Morphology
            799, #International Journal on Digital Libraries
            894, #Journal of Molecular Modeling
            10006, #Mund-, Kiefer- und Gesichtschirurgie (s. Oral and Maxillofacial Surgery)
            10006, #Oral and Maxillofacial Surgery (=Mund-, Kiefer- und Gesichtschirurgie)
            10008, #Journal of Solid State Electrochemistry
            10009, #International Journal on Software Tools for Technology Transfer
            10010, #Forschung im Ingenieurwesen
            10014, #Brain Tumor Pathology
            10015, #Artificial Life and Robotics
            10018, #Environmental Economics and Policy Studies
            10021, #Ecosystems
            10029, #Hernia
            10032, #International Journal on Document Analysis and Recognition (IJDAR)
            10035, #Granular Matter
            10037, #Review of Regional Research (=Jahrbuch für Regionalwissenschaft)
            10037, #Review of Regional Research (s. Jahrbuch für Regionalwissenschaft)
            10039, #Trauma und Berufskrankheit
            10040, #Hydrogeology Journal
            10043, #Optical Review
            10044, #Pattern Analysis and Applications
            10047, #Journal of Artificial Organs
            10048, #Neurogenetics
            10049, #Notfall +  Rettungsmedizin
            10050, #The European Physical Journal A
            10051, #The European Physical Journal B
            10053, #The European Physical Journal D
            10055, #Virtual Reality
            10058, #Review of Economic Design
            10064, #Bulletin of Engineering Geology and the Environment
            10067, #Clinical Rheumatology
            10068, #Food Science and Biotechnology
            10071, #Animal Cognition
            10072, #Neurological Sciences
            10086, #Journal of Wood Science
            10092, #Calcolo
            10096, #European Journal of Clinical Microbiology & Infectious Diseases
            10098, #Clean Technologies and Environmental Policy (see Clean Products and Processes)
            10100, #Central European Journal of Operations Research
            10101, #Economics of Governance
            10103, #Lasers in Medical Science
            10107, #Mathematical Programming
            10109, #Journal of Geographical Systems
            10113, #Regional Environmental Change
            10114, #Acta Mathematica Sinica, English Series
            10115, #Knowledge and Information Systems
            10118, #Chinese Journal of Polymer Science
            10120, #Gastric Cancer
            10126, #Marine Biotechnology
            10140, #Emergency Radiology
            10142, #Functional & Integrative Genomics
            10143, #Neurosurgical Review
            10144, #Population Ecology
            10147, #International Journal of Clinical Oncology
            10151, #Techniques in Coloproctology
            10157, #Clinical and Experimental Nephrology
            10158, #Invertebrate Neuroscience
            10160, #Economic Bulletin
            10162, #JARO - Journal of the Association for Research in Otolaryngology
            10163, #Journal of Material Cycles and Waste Management
            10164, #Journal of Ethology
            10182, #Allgemeines Statistisches Archiv
            10182, #AStA Advances in Statistical Analysis
            10189, #The European Physical Journal E
            10198, #The European Journal of Health Economics
            10201, #Limnology
            10203, #Decisions in Economics and Finance
            10207, #International Journal of Information Security
            10208, #Foundations of Computational Mathematics
            10209, #Universal Access in the Information Society
            10211, #acta ethologica
            10212, #European Journal of Psychology of Education
            10228, #Ichthyological Research
            10230, #Mine Water and the Environment
            10231, #Annali di Matematica Pura ed Applicata
            10236, #Ocean Dynamics
            10237, #Biomechanics and Modeling in Mechanobiology
            10238, #Clinical and Experimental Medicine
            10240, #Publications mathématiques de l'IHÉS
            10255, #Acta Mathematicae Applicatae Sinica, English Series
            10257, #Information Systems and e-Business Management
            10258, #Portuguese Economic Journal
            10260, #Statistical Methods and Applications
            10265, #Journal of Plant Research
            10266, #Odontology
            10270, #Software and Systems Modeling
            10272, #Intereconomics
            10273, #Wirtschaftsdienst
            10278, #Journal of Digital Imaging
            10286, #Clinical Autonomic Research
            10287, #Computational Management Science
            10288, #4OR
            10290, #Review of World Economics
            10291, #GPS Solutions
            10295, #Journal of Industrial Microbiology & Biotechnology
            10304, #Gynäkologische Endokrinologie
            10308, #Asia Europe Journal
            10309, #Zeitschrift für Epileptologie
            10310, #Journal of Forest Research
            10311, #Environmental Chemistry Letters
            10327, #Journal of General Plant Pathology
            10329, #Primates
            10333, #Paddy and Water Environment
            10334, #Magnetic Resonance Materials in Physics, Biology and Medicine
            10336, #Journal of Ornithology
            10337, #Chromatographia
            10339, #Cognitive Processing
            10340, #Journal of Pest Science
            10341, #Erwerbs-Obstbau
            10342, #European Journal of Forest Research
            10343, #Gesunde Pflanzen
            10344, #European Journal of Wildlife Research
            10346, #Landslides
            10347, #Facies
            10353, #European Surgery
            10354, #Wiener Medizinische Wochenschrift
            10357, #Natur und Recht
            10368, #International Economics and Economic Policy
            10384, #Japanese Journal of Ophthalmology
            10388, #Esophagus
            10389, #Journal of Public Health
            10393, #EcoHealth
            10396, #Journal of Medical Ultrasonics
            10397, #Gynecological Surgery
            10404, #Microfluidics and Nanofluidics
            10405, #Der Pneumologe
            10409, #Acta Mechanica Sinica
            10433, #European Journal of Ageing
            10434, #Annals of Surgical Oncology
            10436, #Annals of Finance
            10437, #African Archaeological Review
            10439, #Annals of Biomedical Engineering
            10440, #Acta Applicandae Mathematicae
            10441, #Acta Biotheoretica
            10443, #Applied Composite Materials
            10444, #Advances in Computational Mathematics
            10447, #International Journal for the Advancement of Counselling
            10450, #Adsorption
            10451, #Advances Contraception
            10452, #Aquatic Ecology
            10453, #Aerobiologia
            10455, #Annals of Global Analysis and Geometry
            10456, #Angiogenesis
            10457, #Agroforestry Systems
            10458, #Autonomous Agents and Multi-Agent Systems
            10459, #Advances in Health Sciences Education
            10460, #Agriculture and Human Values
            10461, #AIDS and Behavior
            10462, #Artificial Intelligence Review
            10463, #Annals of the Institute of Statistical Mathematics
            10465, #American Journal of Dance Therapy
            10468, #Algebras and Representation Theory
            10469, #Algebra and Logic
            10470, #Analog Integrated Circuits and Signal Processing
            10472, #Annals of Mathematics and Artificial Intelligence
            10474, #Acta Mathematica Hungarica
            10476, #Analysis Mathematica
            10479, #Annals of Operations Research
            10480, #Annals Software Engineering
            10482, #Antonie van Leeuwenhoek
            10483, #Applied Mathematics and Mechanics
            10484, #Applied Psychophysiology and Biofeedback
            10485, #Applied Categorical Structures
            10488, #Administration and Policy in Mental Health and Mental Health Services Research
            10489, #Applied Intelligence
            10490, #Asia Pacific Journal of Management
            10492, #Applications of Mathematics
            10493, #Experimental and Applied Acarology
            10494, #Flow, Turbulence and Combustion
            10495, #Apoptosis
            10498, #Aquatic Geochemistry
            10499, #Aquaculture International
            10502, #Archival Science
            10503, #Argumentation
            10505, #Archives Museum Informatics
            10506, #Artificial Intelligence and Law
            10508, #Archives of Sexual Behavior
            10509, #Astrophysics and Space Science
            10511, #Astrophysics
            10512, #Atomic Energy
            10514, #Autonomous Robots
            10515, #Automated Software Engineering
            10516, #Axiomathes
            10517, #Bulletin of Experimental Biology and Medicine
            10518, #Bulletin of Earthquake Engineering
            10519, #Behavior Genetics
            10522, #Biogerontology
            10526, #BioControl
            10527, #Biomedical Engineering
            10528, #Biochemical Genetics
            10529, #Biotechnology Letters
            10530, #Biological Invasions
            10531, #Biodiversity and Conservation
            10532, #Biodegradation
            10533, #Biogeochemistry
            10534, #BioMetals
            10535, #Biologia Plantarum
            10537, #Biotherapy
            10539, #Biology & Philosophy
            10541, #Biochemistry (Moscow)
            10542, #Biotechnology Techniques
            10543, #BIT Numerical Mathematics
            10544, #Biomedical Microdevices
            10545, #Journal of Inherited Metabolic Disease
            10546, #Boundary-Layer Meteorology
            10548, #Brain Topography
            10549, #Breast Cancer Research and Treatment
            10551, #Journal of Business Ethics
            10552, #Cancer Causes & Control
            10553, #Chemistry and Technology of Fuels and Oils
            10554, #The International Journal of Cardiovascular Imaging
            10555, #Cancer and Metastasis Reviews
            10556, #Chemical and Petroleum Engineering
            10557, #Cardiovascular Drugs and Therapy
            10559, #Cybernetics and Systems Analysis
            10560, #Child and Adolescent Social Work Journal
            10561, #Cell and Tissue Banking
            10562, #Catalysis Letters
            10563, #Catalysis Surveys from Asia
            10565, #Cell Biology and Toxicology
            10566, #Child & Youth Care Forum
            10567, #Clinical Child and Family  Psychology Review
            10569, #Celestial Mechanics and Dynamical Astronomy
            10570, #Cellulose
            10571, #Cellular and Molecular Neurobiology
            10573, #Combustion, Explosion and Shock Waves
            10577, #Chromosome Research
            10578, #Child Psychiatry & Human Development
            10579, #Language Resources and Evaluation
            10582, #Czechoslovak Journal Physics
            10583, #Children's Literature in Education
            10584, #Climatic Change
            10585, #Clinical & Experimental Metastasis
            10586, #Cluster Computing
            10587, #Czechoslovak Mathematical Journal
            10588, #Computational and Mathematical Organization Theory
            10589, #Computational Optimization and Applications
            10590, #Machine Translation
            10591, #Contemporary Family Therapy
            10592, #Conservation Genetics
            10593, #Chemistry of Heterocyclic Compounds
            10595, #Colloid Journal
            10596, #Computational Geosciences
            10597, #Community Mental Health Journal
            10598, #Computational Mathematics and Modeling
            10600, #Chemistry of Natural Compounds
            10601, #Constraints
            10602, #Constitutional Political Economy
            10603, #Journal of Consumer Policy
            10606, #Computer Supported Cooperative Work (CSCW)
            10608, #Cognitive Therapy and Research
            10609, #Criminal Law Forum
            10610, #European Journal on Criminal Policy and Research
            10611, #Crime, Law and Social Change
            10612, #Critical Criminology
            10614, #Computational Economics
            10615, #Clinical Social Work Journal
            10616, #Cytotechnology
            10617, #Design Automation for Embedded Systems
            10618, #Data Mining and Knowledge Discovery
            10619, #Distributed and Parallel Databases
            10620, #Digestive Diseases and Sciences
            10623, #Designs, Codes and Cryptography
            10624, #Dialectical Anthropology
            10626, #Discrete Event Dynamic Systems
            10631, #Doklady Chemistry
            10633, #Documenta Ophthalmologica
            10637, #Investigational New Drugs
            10638, #Dynamics Control
            10639, #Education and Information Technologies
            10640, #Environmental and Resource Economics
            10641, #Environmental Biology of Fishes
            10643, #Early Childhood Education Journal
            10644, #Economic Change and Restructuring
            10645, #De Economist
            10646, #Ecotoxicology
            10648, #Educational Psychology Review
            10649, #Educational Studies in Mathematics
            10651, #Environmental and Ecological Statistics
            10652, #Environmental Fluid Mechanics
            10653, #Environmental Geochemistry and Health
            10654, #European Journal of Epidemiology
            10657, #European Journal of Law and Economics
            10658, #European Journal of Plant Pathology
            10659, #Journal of Elasticity
            10660, #Electronic Commerce Research
            10661, #Environmental Monitoring and Assessment
            10663, #Empirica
            10664, #Empirical Software Engineering
            10665, #Journal of Engineering Mathematics
            10666, #Environmental Modeling & Assessment
            10669, #Environments Systems and Decisions
            10670, #Erkenntnis
            10671, #Educational Research for Policy and Practice
            10672, #Employee Responsibilities and Rights Journal
            10676, #Ethics and Information Technology
            10677, #Ethical Theory and Moral Practice
            10680, #European Journal of Population / Revue européenne de Démographie
            10681, #Euphytica
            10682, #Evolutionary Ecology
            10683, #Experimental Economics
            10686, #Experimental Astronomy
            10687, #Extremes
            10688, #Functional Analysis and Its Applications
            10689, #Familial Cancer
            10690, #Asia-Pacific Financial Markets
            10691, #Feminist Legal Studies
            10692, #Fibre Chemistry
            10693, #Journal of Financial Services Research
            10694, #Fire Technology
            10695, #Fish Physiology and Biochemistry
            10696, #Flexible Services and Manufacturing Journal
            10697, #Fluid Dynamics
            10698, #Foundations of Chemistry
            10699, #Foundations of Science
            10700, #Fuzzy Optimization and Decision Making
            10701, #Foundations of Physics
            10702, #Foundations Physics Letters
            10703, #Formal Methods in System Design
            10704, #International Journal of Fracture
            10705, #Nutrient Cycling in Agroecosystems
            10706, #Geotechnical and Geological Engineering
            10707, #GeoInformatica
            10708, #GeoJournal
            10709, #Genetica
            10710, #Genetic Programming and Evolvable Machines
            10711, #Geometriae Dedicata
            10712, #Surveys in Geophysics
            10714, #General Relativity and Gravitation
            10715, #Geriatric Nephrology Urology
            10717, #Glass and Ceramics
            10719, #Glycoconjugate Journal
            10720, #Glass Physics and Chemistry
            10722, #Genetic Resources and Crop Evolution
            10723, #Journal of Grid Computing
            10725, #Plant Growth Regulation
            10726, #Group Decision and Negotiation
            10728, #Health Care Analysis
            10729, #Health Care Management Science
            10730, #HEC Forum
            10732, #Journal of Heuristics
            10733, #High Energy Chemistry
            10734, #Higher Education
            10735, #Journal of Molecular Histology
            10739, #Journal of the History of Biology
            10740, #High Temperature
            10741, #Heart Failure Reviews
            10742, #Health Services and Outcomes Research Methodology
            10743, #Husserl Studies
            10745, #Human Ecology
            10746, #Human Studies
            10747, #Human Physiology
            10749, #Power Technology and Engineering
            10750, #Hydrobiologia
            10751, #Hyperfine Interactions
            10753, #Inflammation
            10754, #International Journal of Health Economics and Management (= from 2001 to 2014 published as International Journal of Health Care Finance and Economics 1389-6563 1573-6962)
            10755, #Innovative Higher Education
            10758, #Technology, Knowledge and Learning
            10761, #International Journal of Historical Archaeology
            10762, #Journal of Infrared, Millimeter, and Terahertz Waves
            10763, #International Journal of Science and Mathematics Education
            10764, #International Journal of Primatology
            10765, #International Journal of Thermophysics
            10766, #International Journal of Parallel Programming
            10767, #International Journal of Politics, Culture, and Society
            10769, #International Journal Rehabilitation Health
            10770, #International Journal Salt Lake Research
            10771, #International Journal Stress Management
            10772, #International Journal of Speech Technology
            10773, #International Journal of Theoretical Physics
            10774, #International Journal Value-Based Management
            10775, #International Journal for Educational and Vocational Guidance
            10776, #International Journal of Wireless Information Networks
            10778, #International Applied Mechanics
            10780, #Interchange
            10781, #Journal of Indian Philosophy
            10786, #Instruments and Experimental Techniques
            10787, #InflammoPharmacology
            10789, #Inorganic Materials
            10790, #The Journal of Value Inquiry
            10791, #Information Retrieval
            10792, #International Ophthalmology
            10793, #Interface Science
            10794, #Integrated Pest Management Reviews
            10795, #Irrigation Drainage Systems
            10796, #Information Systems Frontiers
            10797, #International Tax and Public Finance
            10798, #International Journal of Technology and Design Education
            10799, #Information Technology and Management
            10800, #Journal of Applied Electrochemistry
            10801, #Journal of Algebraic Combinatorics
            10802, #Journal of Abnormal Child Psychology
            10803, #Journal of Autism and Developmental Disorders
            10804, #Journal of Adult Development
            10805, #Journal of Academic Ethics
            10806, #Journal of Agricultural and Environmental Ethics
            10808, #Journal of Applied Mechanics and Technical Physics
            10809, #Journal of Analytical Chemistry
            10811, #Journal of Applied Phycology
            10812, #Journal of Applied Spectroscopy
            10813, #Journal Aquatic Ecosystem Stress Recovery
            10814, #Journal of Archaeological Research
            10815, #Journal of Assisted Reproduction and Genetics
            10816, #Journal of Archaeological Method and Theory
            10817, #Journal of Automated Reasoning
            10818, #Journal of Bioeconomics
            10820, #Scientific Modeling Simulation SMNS
            10821, #Journal Child Adolescent Group Therapy
            10822, #Journal of Computer-Aided Molecular Design
            10823, #Journal of Cross-Cultural Gerontology
            10824, #Journal of Cultural Economics
            10825, #Journal of Computational Electronics
            10826, #Journal of Child and Family Studies
            10827, #Journal of Computational Neuroscience
            10828, #The Journal of Comparative Germanic Linguistics
            10831, #Journal of East Asian Linguistics
            10832, #Journal of Electroceramics
            10833, #Journal of Educational Change
            10834, #Journal of Family and Economic Issues
            10835, #Jewish History
            10836, #Journal of Electronic Testing
            10838, #Journal for General Philosophy of Science
            10840, #Journal of Interventional Cardiac Electrophysiology
            10841, #Journal of Insect Conservation
            10843, #Journal of International Entrepreneurship
            10844, #Journal of Intelligent Information Systems
            10845, #Journal of Intelligent Manufacturing
            10846, #Journal of Intelligent & Robotic Systems
            10847, #Journal of Inclusion Phenomena and Macrocyclic Chemistry (= Journal of Inclusion Phenomena)
            10849, #Journal of Logic, Language and Information
            10851, #Journal of Mathematical Imaging and Vision
            10853, #Journal of Materials Science
            10854, #Journal of Materials Science: Materials in Electronics
            10855, #Journal Materials Science Letters
            10856, #Journal of Materials Science: Materials in Medicine
            10857, #Journal of Mathematics Teacher Education
            10858, #Journal of Biomolecular NMR
            10862, #Journal of Psychopathology and Behavioral Assessment
            10863, #Journal of Bioenergetics and Biomembranes
            10864, #Journal of Behavioral Education
            10865, #Journal of Behavioral Medicine
            10867, #Journal of Biological Physics
            10869, #Journal of Business and Psychology
            10870, #Journal of Chemical Crystallography
            10872, #Journal of Oceanography
            10874, #Journal of Atmospheric Chemistry
            10875, #Journal of Clinical Immunology
            10876, #Journal of Cluster Science
            10877, #Journal of Clinical Monitoring and Computing
            10878, #Journal of Combinatorial Optimization
            10879, #Journal of Contemporary Psychotherapy
            10880, #Journal of Clinical Psychology in Medical Settings
            10882, #Journal of Developmental and Physical Disabilities
            10883, #Journal of Dynamical and Control Systems
            10884, #Journal of Dynamics and Differential Equations
            10886, #Journal of Chemical Ecology
            10887, #Journal of Economic Growth
            10888, #The Journal of Economic Inequality
            10891, #Journal of Engineering Physics and Thermophysics
            10892, #The Journal of Ethics
            10894, #Journal of Fusion Energy
            10895, #Journal of Fluorescence
            10896, #Journal of Family Violence
            10897, #Journal of Genetic Counseling
            10898, #Journal of Global Optimization
            10899, #Journal of Gambling Studies
            10900, #Journal of Community Health
            10901, #Journal of Housing and the Built Environment
            10902, #Journal of Happiness Studies
            10903, #Journal of Immigrant and Minority Health
            10904, #Journal of Inorganic and Organometallic Polymers and Materials
            10905, #Journal of Insect Behavior
            10909, #Journal of Low Temperature Physics
            10910, #Journal of Mathematical Chemistry
            10911, #Journal of Mammary Gland Biology and Neoplasia
            10912, #Journal of Medical Humanities
            10913, #Journal of Mining Science
            10914, #Journal of Mammalian Evolution
            10915, #Journal of Scientific Computing
            10916, #Journal of Medical Systems
            10919, #Journal of Nonverbal Behavior
            10921, #Journal of Nondestructive Evaluation
            10922, #Journal of Network and Systems Management
            10924, #Journal of Polymers and the Environment
            10926, #Journal of Occupational Rehabilitation
            10928, #Journal of Pharmacokinetics and Pharmacodynamics
            10930, #The Protein Journal
            10933, #Journal of Paleolimnology
            10934, #Journal of Porous Materials
            10935, #The Journal of Primary Prevention
            10936, #Journal of Psycholinguistic Research
            10940, #Journal of Quantitative Criminology
            10942, #Journal of Rational-Emotive & Cognitive-Behavior Therapy
            10943, #Journal of Religion and Health
            10946, #Journal of Russian Laser Research
            10947, #Journal of Structural Chemistry
            10948, #Journal of Superconductivity and Novel Magnetism (= Journal of Superconductivity)
            10950, #Journal of Seismology
            10951, #Journal of Scheduling
            10952, #Journal Systems Integration
            10953, #Journal of Solution Chemistry
            10955, #Journal of Statistical Physics
            10956, #Journal of Science Education and Technology
            10957, #Journal of Optimization Theory and Applications
            10958, #Journal of Mathematical Sciences
            10959, #Journal of Theoretical Probability
            10961, #The Journal of Technology Transfer
            10963, #Journal of World Prehistory
            10964, #Journal of Youth and Adolescence
            10965, #Journal of Polymer Research
            10967, #Journal of Radioanalytical and Nuclear Chemistry
            10969, #Journal of Structural and Functional Genomics
            10971, #Journal of Sol-Gel Science and Technology
            10972, #Journal of Science Teacher Education
            10973, #Journal of Thermal Analysis and Calorimetry
            10974, #Journal of Muscle Research and Cell Motility
            10975, #Kinetics and Catalysis
            10978, #Law and Critique
            10980, #Landscape Ecology
            10982, #Law and Philosophy
            10984, #Learning Environments Research
            10985, #Lifetime Data Analysis
            10986, #Lithuanian Mathematical Journal
            10988, #Linguistics and Philosophy
            10989, #International Journal of Peptide Research and Therapeutics
            10991, #Liverpool Law Review
            10992, #Journal of Philosophical Logic
            10993, #Language Policy
            10994, #Machine Learning
            10995, #Maternal and Child Health Journal
            10997, #Journal of Management & Governance
            10998, #Periodica Mathematica Hungarica
            10999, #International Journal of Mechanics and Materials in Design
            11001, #Marine Geophysical Research
            11002, #Marketing Letters
            11003, #Materials Science
            11004, #Mathematical Geosciences
            11005, #Letters in Mathematical Physics
            11006, #Mathematical Notes
            11007, #Continental Philosophy Review
            11009, #Methodology and Computing in Applied Probability
            11010, #Molecular and Cellular Biochemistry
            11011, #Metabolic Brain Disease
            11012, #Meccanica
            11013, #Culture, Medicine, and Psychiatry
            11015, #Metallurgist
            11016, #Metascience
            11017, #Theoretical Medicine and Bioethics
            11018, #Measurement Techniques
            11019, #Medicine, Health Care and Philosophy
            11021, #Microbiology
            11022, #Methods Cell Science
            11023, #Minds and Machines
            11024, #Minerva
            11027, #Mitigation and Adaptation Strategies for Global Change
            11029, #Mechanics of Composite Materials
            11030, #Molecular Diversity
            11031, #Motivation and Emotion
            11032, #Molecular Breeding
            11033, #Molecular Biology Reports
            11036, #Mobile Networks and Applications
            11037, #Molecular Engineering
            11038, #Earth, Moon, and Planets
            11039, #MOCT-MOST Economic Policy Transitional Economies
            11041, #Metal Science and Heat Treatment
            11042, #Multimedia Tools and Applications
            11043, #Mechanics of Time-Dependent Materials
            11044, #Multibody System Dynamics
            11045, #Multidimensional Systems and Signal Processing
            11046, #Mycopathologia
            11047, #Natural Computing
            11049, #Natural Language & Linguistic Theory
            11050, #Natural Language Semantics
            11051, #Journal of Nanoparticle Research
            11053, #Natural Resources Research
            11055, #Neuroscience and Behavioral  Physiology
            11056, #New Forests
            11059, #Neohelicon
            11060, #Journal of Neuro-Oncology
            11061, #Neophilologus
            11062, #Neurophysiology
            11063, #Neural Processing Letters
            11064, #Neurochemical Research
            11065, #Neuropsychology Review
            11066, #NETNOMICS: Economic Research and Electronic Networking
            11067, #Networks and Spatial Economics
            11068, #Brain Cell Biology
            11069, #Natural Hazards
            11071, #Nonlinear Dynamics
            11075, #Numerical Algorithms
            11077, #Policy Sciences
            11079, #Open Economies Review
            11081, #Optimization and Engineering
            11082, #Optical and Quantum Electronics
            11083, #Order
            11084, #Origins of Life and Evolution of Biospheres
            11085, #Oxidation of Metals
            11088, #Plasmas Polymers
            11089, #Pastoral Psychology
            11090, #Plasma Chemistry and Plasma Processing
            11092, #Educational Assessment Evaluation Accountability
            11094, #Pharmaceutical Chemistry Journal
            11095, #Pharmaceutical Research
            11096, #International Journal Clinical Pharmacy
            11097, #Phenomenology and the Cognitive Sciences
            11098, #Philosophical Studies
            11099, #Photosynthetica
            11101, #Phytochemistry Reviews
            11102, #Pituitary
            11103, #Plant Molecular Biology
            11104, #Plant and Soil
            11105, #Plant Molecular Biology Reporter
            11106, #Powder Metallurgy and Metal Ceramics
            11107, #Photonic Network Communications
            11109, #Political Behavior
            11110, #Physical Oceanography
            11111, #Population and Environment
            11113, #Population Research and Policy Review
            11115, #Public Organization Review
            11116, #Transportation
            11117, #Positivity
            11118, #Potential Analysis
            11119, #Precision Agriculture
            11120, #Photosynthesis Research
            11121, #Prevention Science
            11123, #Journal of Productivity Analysis
            11125, #PROSPECTS
            11126, #Psychiatric Quarterly
            11127, #Public Choice
            11128, #Quantum Information Processing
            11129, #QME Quantitative Marketing and Economics
            11130, #Plant Foods for Human Nutrition
            11133, #Qualitative Sociology
            11134, #Queueing Systems
            11135, #Quality & Quantity
            11136, #Quality of Life Research
            11137, #Radiochemistry
            11138, #The Review of Austrian Economics
            11139, #The Ramanujan Journal
            11141, #Radiophysics and Quantum Electronics
            11142, #Review of Accounting Studies
            11144, #Reaction Kinetics, Mechanisms and Catalysis
            11145, #Reading and Writing
            11146, #The Journal of Real Estate Finance and Economics
            11147, #Review of Derivatives Research
            11148, #Refractories and Industrial Ceramics
            11149, #Journal of Regulatory Economics
            11150, #Review of Economics of the Household
            11151, #Review of Industrial Organization
            11153, #International Journal for Philosophy of Religion
            11154, #Reviews in Endocrine & Metabolic Disorders
            11156, #Review of Quantitative Finance and Accounting
            11157, #Reviews in Environmental Science and Bio/Technology
            11158, #Res Publica
            11159, #International Review of Education
            11160, #Reviews in Fish Biology and Fisheries
            11162, #Research in Higher Education
            11164, #Research on Chemical Intermediates
            11165, #Research in Science Education
            11166, #Journal of Risk and Uncertainty
            11167, #Russian Journal of Applied Chemistry
            11172, #Russian Chemical Bulletin
            11175, #Russian Journal of Electrochemistry
            11176, #Russian Journal of General Chemistry
            11178, #Russian Journal of Organic Chemistry
            11181, #Russian Journal of Nondestructive Testing
            11182, #Russian Physics Journal
            11185, #Russian Linguistics
            11186, #Theory and Society
            11187, #Small Business Economics
            11188, #Somatic Cell Molecular Genetics
            11191, #Science & Education
            11192, #Scientometrics
            11195, #Sexuality and Disability
            11196, #International Journal for the Semiotics of Law - Revue internationale de Sémiotique juridique
            11199, #Sex Roles
            11200, #Studia Geophysica et Geodaetica
            11202, #Siberian Mathematical Journal
            11203, #Statistical Inference for Stochastic Processes
            11204, #Soil Mechanics and Foundation  Engineering
            11205, #Social Indicators Research
            11207, #Solar Physics
            11211, #Social Justice Research
            11212, #Studies in East European Thought
            11213, #Systemic Practice and Action Research
            11214, #Space Science Reviews
            11217, #Studies in Philosophy and Education
            11218, #Social Psychology of Education
            11219, #Software Quality Journal
            11220, #Sensing and Imaging: An International Journal (= Subsurface Sensing Technologies and Applications)
            11220, #Subsurface Sensing Technologies and Applications (s. Sensing and Imaging: An International Journal)
            11222, #Statistics and Computing
            11223, #Strength of Materials
            11224, #Structural Chemistry
            11225, #Studia Logica
            11227, #The Journal of Supercomputing
            11228, #Set-Valued and Variational Analysis
            11229, #Synthese
            11230, #Systematic Parasitology
            11232, #Theoretical and Mathematical Physics
            11233, #Tertiary Education Management
            11235, #Telecommunication Systems
            11236, #Theoretical Foundations of Chemical Engineering
            11237, #Theoretical and Experimental Chemistry
            11238, #Theory and Decision
            11239, #Journal of Thrombosis and Thrombolysis
            11240, #Plant Cell, Tissue and Organ Culture (PCTOC)
            11241, #Real-Time Systems
            11242, #Transport in Porous Media
            11243, #Transition Metal Chemistry
            11244, #Topics in Catalysis
            11245, #Topoi
            11248, #Transgenic Research
            11249, #Tribology Letters
            11250, #Tropical Animal Health and Production
            11251, #Instructional Science
            11252, #Urban Ecosystems
            11253, #Ukrainian Mathematical Journal
            11255, #International Urology and Nephrology
            11256, #The Urban Review
            11257, #User Modeling and User-Adapted Interaction
            11258, #Plant Ecology
            11259, #Veterinary Research Communications
            11262, #Virus Genes
            11263, #International Journal of Computer Vision
            11265, #Journal of Signal Processing Systems
            11266, #VOLUNTAS: International Journal of Voluntary and Nonprofit Organizations
            11268, #Water Resources
            11269, #Water Resources Management
            11270, #Water, Air, & Soil Pollution
            11273, #Wetlands Ecology and Management
            11274, #World Journal of Microbiology and Biotechnology
            11276, #Wireless Networks
            11277, #Wireless Personal Communications
            11280, #World Wide Web
            11282, #Oral Radiology
            11284, #Ecological Research
            11290, #Georgian Mathematical Journal
            11292, #Journal of Experimental Criminology
            11293, #Atlantic Economic Journal
            11294, #International Advances in Economic Research
            11295, #Tree Genetics & Genomes
            11298, #CME
            11299, #Mind & Society
            11301, #Management Review Quarterly (= previously until 2014 Journal für Betriebswirtschaft)
            11302, #Purinergic Signalling
            11306, #Metabolomics
            11307, #Molecular Imaging and Biology
            11325, #Sleep and Breathing
            11332, #Sport Sciences for Health
            11334, #Innovations in Systems and Software Engineering
            11336, #Psychometrika
            11340, #Experimental Mechanics
            11355, #Landscape and Ecological Engineering
            11356, #Environmental Science and Pollution Research
            11357, #AGE
            11365, #International Entrepreneurship and Management Journal
            11367, #The International Journal of Life Cycle Assessment
            11368, #Journal of Soils and Sediments
            11370, #Intelligent Service Robotics
            11373, #Journal Biomedical Science
            11377, #Der Gastroenterologe
            11390, #Journal of Computer Science and Technology
            11401, #Chinese Annals of Mathematics, Series B
            11403, #Journal of Economic Interaction and Coordination
            11406, #Philosophia
            11407, #International Journal of Hindu Studies
            11408, #Financial Markets and Portfolio Management
            11409, #Metacognition and Learning
            11412, #International Journal of Computer-Supported Collaborative Learning
            11414, #The Journal of Behavioral Health Services & Research
            11416, #Journal in Computer Virology
            11417, #Asian Journal of Criminology
            11418, #Journal of Natural Medicines
            11419, #Forensic Toxicology
            11420, #HSS Journal
            11422, #Cultural Studies of Science Education
            11423, #Educational Technology Research and Development
            11424, #Journal of Systems Science and Complexity
            11425, #Science China Mathematics
            11428, #Der Diabetologe
            11430, #Science China Earth Sciences
            11439, #Biophysics
            11440, #Acta Geotechnica
            11441, #Acoustical Physics
            11443, #Astronomy Letters
            11444, #Astronomy Reports
            11445, #Crystallography Reports
            11446, #Doklady Physics
            11447, #Journal of Experimental and Theoretical Physics
            11448, #JETP Letters (=Journal of Experimental and Theoretical Physics Letters)
            11448, #Journal of Experimental and Theoretical Physics Letters (s. JETP Letters)
            11449, #Optics and Spectroscopy
            11450, #Physics of Atomic Nuclei
            11451, #Physics of the Solid State
            11452, #Plasma Physics Reports
            11453, #Semiconductors
            11454, #Technical Physics
            11455, #Technical Physics Letters
            11457, #Journal of Maritime Archaeology
            11464, #Frontiers of Mathematics in China
            11465, #Frontiers of Mechanical Engineering in China
            11467, #Frontiers of Physics in China
            11468, #Plasmonics
            11469, #International Journal of Mental Health and Addiction
            11470, #Computational Mathematics and Mathematical Physics
            11471, #Doklady Earth Sciences
            11472, #Doklady Mathematics
            11474, #Entomological Review
            11475, #Eurasian Soil Science
            11476, #Geochemistry International
            11477, #Geology of Ore Deposits
            11478, #Geomagnetism and Aeronomy
            11479, #Geotectonics
            11480, #Herald of the Russian Academy of Sciences
            11481, #Journal of Neuroimmune Pharmacology
            11482, #Applied Research in Quality of Life
            11483, #Food Biophysics
            11485, #Izvestiya, Atmospheric and Oceanic Physics
            11486, #Izvestiya, Physics of the Solid Earth
            11487, #Journal of Communications Technology and Electronics
            11488, #Journal of Computer and Systems Sciences International
            11489, #Journal of Ichthyology
            11491, #Oceanology
            11492, #Paleontological Journal
            11493, #Pattern Recognition and Image Analysis
            11494, #Petroleum Chemistry
            11495, #Petrology
            11501, #Proceedings of the Steklov Institute of Mathematics
            11502, #Russian Journal of Inorganic Chemistry
            11503, #Russian Journal of Mathematical Physics
            11504, #Russian Journal of Physical Chemistry A
            11505, #Russian Metallurgy (Metally)
            11506, #Stratigraphy and Geological Correlation
            11507, #Studies on Russian Economic Development
            11508, #The Physics of Metals and Metallography
            11509, #Thermal Engineering
            11510, #Thermophysics and Aeromechanics
            11511, #Acta Mathematica
            11512, #Arkiv för Matematik
            11515, #Frontiers of Biology in China (= Frontiers in Biology)
            11517, #Medical & Biological Engineering & Computing
            11518, #Journal of Systems Science and Systems Engineering
            11523, #Targeted Oncology
            11524, #Journal of Urban Health
            11525, #Morphology
            11527, #Materials and Structures
            11528, #TechTrends
            11529, #Polymer Science, Series A - D
            11537, #Japanese Journal of Mathematics
            11538, #Bulletin of Mathematical Biology
            11539, #Nuovo Cimento A 1965-1970
            11540, #Potato Research
            11542, #Nuovo Cimento B 1965-1970
            11543, #Nuovo Cimento C
            11544, #Nuovo Cimento D
            11545, #Lettere al Nuovo Cimento 1969-1970
            11546, #Rivista del Nuovo Cimento 1969-1970
            11547, #La Radiologia Medica
            11548, #International Journal of Computer Assisted Radiology and Surgery
            11553, #Prävention und Gesundheitsförderung
            11554, #Journal of Real-Time Image Processing
            11557, #Mycological Progress
            11558, #The Review of International Organizations
            11560, #Der Nephrologe
            11562, #Contemporary Islam
            11565, #Annali dell'Universita di Ferrara
            11569, #NanoEthics
            11571, #Cognitive Neurodynamics
            11572, #Criminal Law and Philosophy
            11573, #Journal of Business Economics (= former Zeitschrift für Betriebswirtschaft)
            11575, #Management International Review
            11577, #KZfSS Kölner Zeitschrift für Soziologie und Sozialpsychologie
            11579, #Mathematics and Financial Economics
            11581, #Ionics
            11582, #Journal of Zhejiang University - Science A
            11583, #Nuovo Cimento 1855-1868
            11584, #Cimento
            11585, #Journal of Zhejiang University - Science B
            11587, #Ricerche di Matematica
            11596, #Journal Huazhong University Science Technology [Medical Sciences]
            11604, #Japanese Journal of Radiology (=Radiation Medicine)
            11604, #Radiation Medicine (s. Japanese Journal of Radiology)
            11605, #Journal of Gastrointestinal Surgery
            11606, #Journal of General Internal Medicine
            11609, #Berliner Journal für Soziologie
            11612, #Gruppe – Interaktion – Organisation | Zeitschrift für Angewandte Organisationspsychologie (Prior to Volume 47 (2016) published as Gruppendynamik und Organisationsberatung)
            11613, #Organisationsberatung, Supervision, Coaching
            11614, #Österreichische Zeitschrift für Soziologie
            11616, #Publizistik
            11618, #Zeitschrift für Erziehungswissenschaft
            11623, #Datenschutz und Datensicherheit - DuD
            11625, #Sustainability Science
            11626, #In Vitro Cellular & Developmental Biology - Animal
            11627, #In Vitro Cellular & Developmental Biology - Plant
            11630, #Journal of Thermal Science
            11631, #Chinese Journal Geochemistry
            11633, #International Journal of Automation and Computing
            11654, #Best Practice Onkologie
            11655, #Chinese Journal Integrative Medicine
            11657, #Archives of Osteoporosis
            11661, #Metallurgical and Materials Transactions A
            11663, #Metallurgical and Materials Transactions B
            11664, #Journal of Electronic Materials
            11665, #Journal of Materials Engineering and Performance
            11666, #Journal of Thermal Spray Technology
            11669, #Journal of Phase Equilibria and Diffusion
            11676, #Journal Forestry Research
            11678, #Obere Extremität
            11682, #Brain Imaging and Behavior
            11684, #Frontiers of Medicine (= Frontiers of Medicine in China)
            11692, #Evolutionary Biology
            11694, #Journal of Food Measurement and Characterization
            11695, #Obesity Surgery
            11704, #Frontiers of Computer Science in China
            11705, #Frontiers of Chemical Engineering in China
            11706, #Frontiers of Materials Science
            11707, #Frontiers of Earth Science in China
            11708, #Frontiers of Energy and Power Engineering in China
            11709, #Frontiers of Architecture and Civil Engineering in China
            11711, #Journal of Volcanology and Seismology
            11712, #Dao
            11734, #The European Physical Journal Special Topics
            11738, #Acta Physiologiae Plantarum
            11739, #Internal and Emergency Medicine
            11743, #Journal of Surfactants and Detergents
            11745, #Lipids
            11746, #Journal of the American Oil Chemists' Society
            11747, #Journal of the Academy of Marketing Science
            11748, #General Thoracic and Cardiovascular Surgery
            11749, #TEST
            11750, #TOP
            11757, #Forensische Psychiatrie, Psychologie, Kriminologie
            11769, #Chinese Geographical Science
            11771, #Journal Central South University
            11783, #Frontiers of Environmental Science & Engineering in China
            11801, #Optoelectronics Letters
            11812, #Wiener klinische Wochenschrift Education
            11814, #Korean Journal of Chemical Engineering
            11818, #Somnologie - Schlafforschung und Schlafmedizin
            11819, #Regular and Chaotic Dynamics
            11821, #Cell and Tissue Biology
            11825, #medizinische genetik
            11829, #Arthropod-Plant Interactions
            11831, #Archives Computational Methods Engineering
            11837, #JOM
            11841, #Sophia
            11845, #Irish Journal of Medical Science
            11846, #Review of Managerial Science
            11852, #Journal of Coastal Conservation
            11854, #Journal d'Analyse Mathématique
            11856, #Israel Journal of Mathematics
            11857, #Blätter DGVFM
            11858, #ZDM (= Zentralblatt für Didaktik der Mathematik)
            11859, #Wuhan University Journal Natural Sciences
            11864, #Current Treatment Options in Oncology
            11869, #Air Quality, Atmosphere & Health
            11881, #Annals of Dyslexia
            11892, #Current Diabetes Reports
            11896, #Journal Police Criminal Psychology
            11904, #Current HIV/AIDS Reports
            11908, #Current Infectious Disease Reports
            11910, #Current Neurology and Neuroscience Reports
            11940, #Current Treatment Options in Neurology
            11947, #Food and Bioprocess Technology
            11948, #Science and Engineering Ethics
            11957, #Journal of Contemporary Mathematical Analysis
            11982, #Russian Mathematics
            11983, #Russian Meteorology and Hydrology
            11988, #Vestnik St. Petersburg University: Mathematics
            11999, #Clinical Orthopaedics and Related Research®
            12003, #International Journal of Self-Propagating High-Temperature Synthesis
            12008, #International Journal on Interactive Design and Manufacturing (IJIDeM)
            12010, #Applied Biochemistry and Biotechnology
            12011, #Biological Trace Element Research
            12012, #Cardiovascular Toxicology
            12013, #Cell Biochemistry and Biophysics
            12015, #Stem Cell Reviews and Reports
            12016, #Clinical Reviews Allergy Immunology
            12017, #NeuroMolecular Medicine
            12020, #Endocrine
            12021, #Neuroinformatics
            12022, #Endocrine Pathology
            12024, #Forensic Science, Medicine, and Pathology
            12026, #Immunologic Research
            12027, #ERA Forum
            12028, #Neurocritical Care
            12029, #Journal of Gastrointestinal Cancer
            12031, #Journal of Molecular Neuroscience
            12032, #Medical Oncology
            12033, #Molecular Biotechnology
            12034, #Bulletin Materials Science
            12035, #Molecular Neurobiology
            12036, #Journal of Astrophysics and Astronomy
            12038, #Journal of Biosciences
            12039, #Journal of Chemical Sciences
            12040, #Journal of Earth System Science (formerly: Proceedings - Earth and Planetary Sciences)
            12041, #Journal of Genetics
            12042, #Tropical Plant Biology
            12043, #Pramana - Journal of Physics
            12044, #Proceedings - Mathematical Sciences (= Proc. In the Indian Academy of Sciences - Math. Sciences)
            12045, #Resonance
            12046, #Sadhana
            12053, #Energy Efficiency
            12054, #Sozial Extra
            12055, #Indian Journal of Thoracic and Cardiovascular Surgery
            12061, #Applied Spatial Analysis and Policy
            12064, #Theory in Biosciences
            12065, #Evolutionary  Intelligence
            12070, #Indian Journal of Otolaryngology and Head & Neck Surgery
            12078, #Chemosensory Perception
            12080, #Theoretical Ecology
            12088, #Indian Journal of Microbiology
            12094, #Clinical and Translational Oncology
            12098, #Indian Journal of Pediatrics
            12103, #American Journal Criminal Justice
            12104, #Biomolecular NMR Assignments
            12108, #The American Sociologist
            12109, #Publishing Research Quarterly
            12110, #Human Nature
            12111, #Journal African American Studies
            12114, #Review Black Political Economy
            12115, #Society
            12116, #Studies in Comparative International Development
            12117, #Trends in Organized Crime
            12122, #Journal of Labor Research
            12124, #Integrative Psychological and Behavioral Science
            12126, #Ageing International
            12127, #International Journal for Ion Mobility Spectrometry
            12129, #Academic Questions
            12132, #Urban Forum
            12134, #Journal of International Migration and Integration
            12136, #Acta Analytica
            12138, #International Journal of the Classical Tradition
            12140, #East Asia
            12142, #Human Rights Review
            12144, #Current Psychology
            12147, #Gender Issues
            12149, #Annals of Nuclear Medicine
            12155, #BioEnergy Research
            12160, #Annals of Behavioral Medicine
            12161, #Food Analytical Methods
            12176, #Controlling & Management Review (= Controlling & Management)
            12186, #Vocations and Learning
            12188, #Abhandlungen aus dem Mathematischen Seminar der Universität Hamburg
            12190, #Journal Applied Mathematics Computing
            12192, #Cell Stress and Chaperones
            12193, #Journal on Multimodal User Interfaces
            12195, #Cellular and Molecular Bioengineering
            12199, #Environmental Health and Preventive Medicine
            12200, #Frontiers of Optoelectronics in China
            12206, #Journal Mechanical Science Technology
            12210, #Rendiconti Lincei
            12212, #Inland Water Biology
            12215, #Rendiconti del Circolo Matematico di Palermo
            12220, #Journal of Geometric Analysis
            12221, #Fibers and Polymers
            12223, #Folia Microbiologica
            12224, #Folia Geobotanica
            12225, #Kew Bulletin
            12228, #Brittonia
            12229, #The Botanical Review
            12230, #American Journal of Potato Research
            12231, #Economic Botany
            12232, #International Review of Economics
            12237, #Estuaries Coasts
            12242, #Acta Physica Hungarica
            12243, #annals of telecommunications - annales des télécommunications
            12247, #Journal of Pharmaceutical Innovation
            12248, #The AAPS Journal
            12249, #AAPS PharmSciTech
            12257, #Biotechnology Bioprocess Engineering
            12262, #Indian Journal of Surgery
            12268, #BIOspektrum
            12272, #Archives Pharmacal Research
            12273, #Building Simulation
            12274, #Nano Research
            12275, #Journal of Microbiology
            12277, #Fortschrittsberichte über Kolloide Polymere
            12279, #Chemists' Section Cotton Oil Press
            12282, #Breast Cancer
            12286, #Zeitschrift für Vergleichende Politikwissenschaft
            12288, #Indian Journal of Hematology and Blood Transfusion
            12289, #International Journal of Material Forming
            12291, #Indian Journal Clinical Biochemistry
            12297, #Zeitschrift für die gesamte Versicherungswissenschaft
            12298, #Physiology and Molecular Biology of Plants
            12306, #MUSCULOSKELETAL SURGERY
            12307, #Cancer Microenvironment
            12308, #Journal of Hematopathology
            12311, #The Cerebellum
            12325, #Advances in Therapy
            12328, #Clinical Journal of Gastroenterology
            12350, #Journal of Nuclear Cardiology
            12357, #Bulletin Géodésique 1922-1943
            12359, #Zeitschrift gesamte Neurologie Psychiatrie
            12361, #Archiv Mikroskopische Anatomie
            12362, #Bulletin Volcanologique
            12363, #Mikrochemie
            12364, #American Journal Digestive Diseases
            12365, #European Demographic Information Bulletin
            12366, #Bulletin General Relativity Gravitation
            12369, #International Journal of Social Robotics
            12371, #Geoheritage
            12373, #Molecular chemical neuropathology
            12374, #Journal of Plant Biology
            12375, #Annalen Philosophie philosophischen Kritik
            12377, #Annalen Philosophie
            12379, #Zeitschrift Kristallographie Mineralogie Petrographie
            12380, #Applied Scientific Research
            12383, #Zeitschrift experimentelle Pathologie
            12384, #Journal instructional development
            12386, #Journal Materials Energy Systems
            12387, #Journal Applied Metalworking
            12388, #Proceedings Plant Sciences
            12391, #Current Psychological Reviews
            12393, #Food Engineering Reviews
            12395, #Chesapeake Science
            12397, #Contemporary Jewry
            12398, #Zeitschrift für Energiewirtschaft
            12402, #ADHD Attention Deficit and Hyperactivity Disorders
            12403, #Water Quality, Exposure and Health
            12519, #World Journal of Pediatrics
            12521, #International journal clinical monitoring computing
            12522, #Reproductive Medicine and Biology
            12524, #Journal Indian Society Remote Sensing
            12525, #Electronic Markets
            12528, #Journal Computing Higher Education
            12529, #International Journal Behavioral Medicine
            12532, #Mathematical Programming Computation
            12535, #Trabajos estadística
            12536, #Trabajos estadística investigación operativa
            12537, #Trabajos investigación operativa
            12540, #Metals Materials International
            12541, #International Journal of Precision Engineering and Manufacturing
            12542, #Paläontologische Zeitschrift
            12546, #Journal Population Research
            12549, #Palaeobiodiversity and Palaeoenvironments
            12550, #Mycotoxin Research
            12551, #Biophysical Reviews
            12559, #Cognitive Computation
            12560, #Food and Environmental Virology
            12561, #Statistics in Biosciences
            12565, #Anatomical Science International
            12567, #CEAS Space Journal
            12571, #Food Security
            12576, #The Journal of Physiological Sciences
            12588, #International Journal of Plastics Technology
            12592, #Soziale Passagen
            12594, #Journal of the Geological Society of India
            12596, #Journal of Optics
            12599, #Business & Information Systems Engineering
            12600, #Phytoparasitica
            12602, #Probiotics and Antimicrobial Proteins
            12603, #The journal of nutrition, health & aging
            12613, #International Journal of Minerals, Metallurgy, and Materials
            12627, #Dublin Journal Medical Science 1836-1845
            12628, #Dublin Quarterly Journal Medical Science
            12629, #Dublin Journal Medical Chemical Science
            12630, #Canadian Journal of Anesthesia/Journal canadien d'anesthésie
            12633, #Silicon
            12650, #Journal of Visualization
            12656, #Acta Physica Hungarica A Heavy Ion Physics
            12658, #Acta physica Academiae Scientiarum Hungaricae
            12659, #Hungarica Acta Physica
            12662, #Sportwissenschaft
            12665, #Environmental Earth Sciences
            12666, #Transactions of the Indian Institute of Metals
            12671, #Mindfulness
            12680, #Transactions Royal Academy Medicine Ireland
            12686, #Conservation Genetics Resources
            12689, #China-EU Law Journal
            12927, #Journal of Service Science Research
            12928, #Cardiovascular Intervention and Therapeutics
            12975, #Translational Stroke Research
            13093, #Iconographia mycologica
            13105, #Journal of Physiology and Biochemistry
            13126, #Hellenic Journal of Surgery
            13127, #Organisms Diversity & Evolution
            13129, #The European Physical Journal H
            13131, #Acta Oceanologica Sinica
            13138, #Journal für Mathematik-Didaktik
            13143, #Asia-Pacific Journal of Atmospheric Sciences
            13146, #Carbonates and Evaporites
            13147, #Raumforschung und Raumordnung
            13157, #Wetlands
            13158, #International Journal of Early Childhood
            13160, #Japan Journal of Industrial and Applied Mathematics
            13163, #Revista Matemática Complutense
            13164, #Review of Philosophy and Psychology
            13177, #International Journal of Intelligent Transportation Systems Research
            13181, #Journal of Medical Toxicology
            13187, #Journal of Cancer Education
            13194, #European Journal for Philosophy of Science
            13197, #Journal of Food Science and Technology
            13199, #Symbiosis
            13206, #BioChip Journal
            13218, #KI - Künstliche Intelligenz
            13222, #Datenbank-Spektrum
            13225, #Fungal Diversity
            13226, #Indian Journal of Pure and Applied Mathematics
            13237, #The Nucleus
            13239, #Cardiovascular Engineering and Technology
            13246, #Australasian Physical & Engineering Sciences in Medicine
            13253, #Journal of Agricultural, Biological, and Environmental Statistics
            13270, #Journal Elementary Science Education
            13271, #Proceedings Animal Sciences
            13279, #der junge zahnarzt
            13280, #AMBIO
            13291, #Jahresbericht der Deutschen Mathematiker-Vereinigung
            13295, #e-Neuroforum
            13295, #e-Neuroforum
            13313, #Australasian Plant Pathology
            13318, #European Journal of Drug Metabolism and Pharmacokinetics
            13346, #Drug Delivery and Translational Research
            13347, #Philosophy & Technology
            13355, #Applied Entomology and Zoology
            13358, #Swiss Journal of Palaeontology
            13360, #The European Physical Journal Plus
            13361, #Journal of The American Society for Mass Spectrometry
            13364, #Mammal Research (previous 2015: Acta theriologica, 0001-7051, 2190-3743)
            13365, #Journal of NeuroVirology
            13366, #Beiträge zur Algebra und Geometrie / Contributions to Algebra and Geometry
            13370, #Afrika Matematika
            13384, #The Australian Educational Researcher
            13385, #European Actuarial Journal
            13394, #Mathematics Education Research Journal
            13414, #Attention, Perception, & Psychophysics
            13415, #Cognitive, Affective, & Behavioral Neuroscience
            13420, #Learning & Behavior
            13421, #Memory & Cognition
            13423, #Psychonomic Bulletin & Review
            13428, #Behavior Research Methods
            13524, #Demography
            13572, #Sankhya (Series A und B - combined subscription mit Refs. 13171 und 13571)
            13577, #Human Cell
            13592, #Apidologie
            13593, #Agronomy for Sustainable Development
            13594, #Dairy Science & Technology
            13595, #Annals of Forest Science
            13644, #Review of Religious Research
            13752, #Biological Theory
            15004, #InFo Onkologie
            15006, #MMW - Fortschritte der Medizin
            15007, #Allergo Journal
            15010, #Infection
            15012, #hautnah dermatologie
            15034, #Info Diabetologie
            40194, #Welding in the World
            40295, #The Journal of the Astronautical Sciences
            40520, #Aging Clinical and Experimental Research
            40592, #Monash Bioethics Review
            40596, #Academic Psychiatry
            40618, #Journal of Endocrinological Investigation
            40653, #Journal of Child & Adolescent Trauma
            40664, #Zentralblatt für Arbeitsmedizin, Arbeitsschutz und Ergonomie
            40688, #Contemporary School Psychology
            40702, #HMD Praxis der Wirtschaftsinformatik
            40752, #Glycosylation Disease
            40754, #Nuovo Cimento 1869-1876
            40755, #Nuovo Cimento 1877-1894
            40756, #Nuovo Cimento 1895-1900
            40757, #Nuovo Cimento 1901-1910
            40758, #Nuovo Cimento 1911-1923
            40760, #Nuovo Cimento 1924-1042
            40761, #Nuovo Cimento 1943-1954
            40762, #Nuovo Cimento 1955-1965
            40763, #Nuovo Cimento A 1971-1996
            40764, #Nuovo Cimento B 1971-1996
            40765, #Rivista del Nuovo Cimento 1971-1977
            40766, #Rivista del Nuovo Cimento 1978-1999
            40767, #Lettere al Nuovo Cimento 1971-1985
            40768, #Annali Matematica Pura ed Applicata 1858-1865
            40769, #Annali Matematica Pura ed Applicata 1867-1897
            40770, #Annali Matematica Pura ed Applicata 1898-1922
            40771, #Bulletin Géodésique 1946-1975
            40772, #Dublin Journal Medical Science 1872-1920
            40773, #Dublin Journal Medical Science 1920-1922
            40774, #Irish Journal Medical Science 1922-1925
            40775, #Irish Journal Medical Science 1926-1967
            40776, #Irish Journal Medical Science 1968-1970
            40777, #Rendiconti del Circolo Matematico Palermo 1884-1940
            40802, #Netherlands International Law Review
            40804, #European Business Organization Law Review
        )

        # for some journals, the moving wall does not apply and they have a special end year
        self.journalsWithASpecialEndYear = {
            65 : 1995, #Orthopedics Traumatology
            135 : 1991, #Journal Materials Engineering
            136 : 1991, #Journal Heat Treating
            218 : 1996, #Zeitschrift Physik A Hadrons nuclei
            254 : 1996, #Environmental Geology
            257 : 1996, #Zeitschrift Physik B Condensed Matter
            288 : 1996, #Zeitschrift Physik C Particles Fields
            290 : 1992, #Urologic Radiology
            354 : 2004, #New Generation Computing
            376 : 2004, #Advances Atmospheric Sciences
            433 : 1996, #Research Experimental Medicine
            443 : 1993, #Virchows Archiv B Cell Pathology
            460 : 1996, #Zeitschrift Physik D Atoms Molecules Clusters
            499 : 1991, #Journal Materials Shaping Technology
            547 : 1996, #International Journal Angiology
            599 : 1996, #International Journal Clinical Laboratory Research
            722 : 1995, #Journal Neural Transmission Parkinson's Disease Dementia Section
            795 : 2004, #Medical Molecular Morphology
            10160 : 1996, #Economic Bulletin
            10451 : 1996, #Advances Contraception
            10480 : 1996, #Annals Software Engineering
            10505 : 1996, #Archives Museum Informatics
            10537 : 1996, #Biotherapy
            10542 : 1996, #Biotechnology Techniques
            10582 : 1996, #Czechoslovak Journal Physics
            10638 : 1996, #Dynamics Control
            10702 : 1996, #Foundations Physics Letters
            10715 : 1996, #Geriatric Nephrology Urology
            10769 : 1996, #International Journal Rehabilitation Health
            10770 : 1996, #International Journal Salt Lake Research
            10771 : 1996, #International Journal Stress Management
            10774 : 1996, #International Journal Value-Based Management
            10793 : 1996, #Interface Science
            10794 : 1995, #Integrated Pest Management Reviews
            10795 : 1996, #Irrigation Drainage Systems
            10813 : 1996, #Journal Aquatic Ecosystem Stress Recovery
            10820 : 1996, #Scientific Modeling Simulation SMNS
            10821 : 1996, #Journal Child Adolescent Group Therapy
            10855 : 1996, #Journal Materials Science Letters
            10952 : 1996, #Journal Systems Integration
            11022 : 1996, #Methods Cell Science
            11037 : 1996, #Molecular Engineering
            11039 : 1996, #MOCT-MOST Economic Policy Transitional Economies
            11068 : 1996, #Brain Cell Biology
            11088 : 1996, #Plasmas Polymers
            11092 : 2004, #Educational Assessment Evaluation Accountability
            11096 : 2004, #International Journal Clinical Pharmacy
            11105 : 2004, #Plant Molecular Biology Reporter
            11110 : 1996, #Physical Oceanography
            11188 : 1996, #Somatic Cell Molecular Genetics
            11233 : 1996, #Tertiary Education Management
            11290 : 1996, #Georgian Mathematical Journal
            11373 : 1996, #Journal Biomedical Science
            11539 : 1970, #Nuovo Cimento A 1965-1970
            11542 : 1970, #Nuovo Cimento B 1965-1970
            11543 : 1996, #Nuovo Cimento C
            11544 : 1996, #Nuovo Cimento D
            11545 : 1970, #Lettere al Nuovo Cimento 1969-1970
            11546 : 1970, #Rivista del Nuovo Cimento 1969-1970
            11583 : 1867, #Nuovo Cimento 1855-1868
            11584 : 1847, #Cimento
            11596 : 2004, #Journal Huazhong University Science Technology [Medical Sciences]
            11631 : 2004, #Chinese Journal Geochemistry
            11655 : 2004, #Chinese Journal Integrative Medicine
            11676 : 2004, #Journal Forestry Research
            11749 : 2004, #TEST
            11750 : 2004, #TOP
            11769 : 2004, #Chinese Geographical Science
            11771 : 2004, #Journal Central South University
            11831 : 2004, #Archives Computational Methods Engineering
            11857 : 1996, #Blätter DGVFM
            11859 : 2004, #Wuhan University Journal Natural Sciences
            11896 : 2004, #Journal Police Criminal Psychology
            12016 : 2004, #Clinical Reviews Allergy Immunology
            12032 : 2004, #Medical Oncology
            12034 : 2004, #Bulletin Materials Science
            12103 : 2004, #American Journal Criminal Justice
            12109 : 2004, #Publishing Research Quarterly
            12111 : 2004, #Journal African American Studies
            12114 : 2004, #Review Black Political Economy
            12126 : 2004, #Ageing International
            12132 : 2004, #Urban Forum
            12190 : 2004, #Journal Applied Mathematics Computing
            12206 : 2004, #Journal Mechanical Science Technology
            12237 : 2004, #Estuaries Coasts
            12242 : 1994, #Acta Physica Hungarica
            12257 : 2004, #Biotechnology Bioprocess Engineering
            12272 : 2004, #Archives Pharmacal Research
            12277 : 1971, #Fortschrittsberichte über Kolloide Polymere
            12279 : 1924, #Chemists' Section Cotton Oil Press
            12291 : 2004, #Indian Journal Clinical Biochemistry
            12357 : 1939, #Bulletin Géodésique 1922-1943
            12359 : 1944, #Zeitschrift gesamte Neurologie Psychiatrie
            12361 : 1923, #Archiv Mikroskopische Anatomie
            12362 : 1931, #Bulletin Volcanologique
            12363 : 1938, #Mikrochemie
            12364 : 1955, #American Journal Digestive Diseases
            12365 : 1983, #European Demographic Information Bulletin
            12366 : 1969, #Bulletin General Relativity Gravitation
            12373 : 1996, #Molecular chemical neuropathology
            12375 : 1929, #Annalen Philosophie philosophischen Kritik
            12377 : 1921, #Annalen Philosophie
            12379 : 1945, #Zeitschrift Kristallographie Mineralogie Petrographie
            12380 : 1966, #Applied Scientific Research
            12383 : 1921, #Zeitschrift experimentelle Pathologie
            12384 : 1988, #Journal instructional development
            12386 : 1986, #Journal Materials Energy Systems
            12387 : 1985, #Journal Applied Metalworking
            12388 : 1996, #Proceedings Plant Sciences
            12391 : 1982, #Current Psychological Reviews
            12395 : 1977, #Chesapeake Science
            12397 : 2004, #Contemporary Jewry
            12521 : 1996, #International journal clinical monitoring computing
            12524 : 2004, #Journal Indian Society Remote Sensing
            12528 : 2004, #Journal Computing Higher Education
            12529 : 2004, #International Journal Behavioral Medicine
            12535 : 1991, #Trabajos estadística
            12536 : 1985, #Trabajos estadística investigación operativa
            12537 : 1992, #Trabajos investigación operativa
            12540 : 2004, #Metals Materials International
            12546 : 2004, #Journal Population Research
            12627 : 1845, #Dublin Journal Medical Science 1836-1845
            12628 : 1871, #Dublin Quarterly Journal Medical Science
            12629 : 1835, #Dublin Journal Medical Chemical Science
            12656 : 1996, #Acta Physica Hungarica A Heavy Ion Physics
            12658 : 1982, #Acta physica Academiae Scientiarum Hungaricae
            12659 : 1949, #Hungarica Acta Physica
            12680 : 1919, #Transactions Royal Academy Medicine Ireland
            13093 : 1983, #Iconographia mycologica
            13270 : 1996, #Journal Elementary Science Education
            13271 : 1990, #Proceedings Animal Sciences
            13313 : 2004, #Australasian Plant Pathology
            13394 : 2004, #Mathematics Education Research Journal
            40752 : 1994, #Glycosylation Disease
            40754 : 1876, #Nuovo Cimento 1869-1876
            40755 : 1894, #Nuovo Cimento 1877-1894
            40756 : 1900, #Nuovo Cimento 1895-1900
            40757 : 1910, #Nuovo Cimento 1901-1910
            40758 : 1923, #Nuovo Cimento 1911-1923
            40760 : 1942, #Nuovo Cimento 1924-1042
            40761 : 1954, #Nuovo Cimento 1943-1954
            40762 : 1965, #Nuovo Cimento 1955-1965
            40763 : 1996, #Nuovo Cimento A 1971-1996
            40764 : 1996, #Nuovo Cimento B 1971-1996
            40765 : 1977, #Rivista del Nuovo Cimento 1971-1977
            40766 : 1996, #Rivista del Nuovo Cimento 1978-1999
            40767 : 1985, #Lettere al Nuovo Cimento 1971-1985
            40768 : 1865, #Annali Matematica Pura ed Applicata 1858-1865
            40769 : 1897, #Annali Matematica Pura ed Applicata 1867-1897
            40770 : 1922, #Annali Matematica Pura ed Applicata 1898-1922
            40771 : 1975, #Bulletin Géodésique 1946-1975
            40772 : 1920, #Dublin Journal Medical Science 1872-1920
            40773 : 1922, #Dublin Journal Medical Science 1920-1922
            40774 : 1924, #Irish Journal Medical Science 1922-1925
            40775 : 1966, #Irish Journal Medical Science 1926-1967
            40776 : 1970, #Irish Journal Medical Science 1968-1970
            40777 : 1940, #Rendiconti del Circolo Matematico Palermo 1884-1940
            10310 : 2012, #Journal of Forest Research
            10397 : 2012, #Gynecological Surgery
            10969 : 2012, #Journal of Structural and Functional Genomics
            10972 : 2012, #Journal of Science Teacher Education
            11511 : 2012, #Acta Mathematica
            11512 : 2012, #Arkiv för Matematik
            11743 : 2012, #Journal of Surfactants and Detergents
            11745 : 2012, #Lipids
            11746 : 2012, #Journal of the American Oil Chemists' Society
            11999 : 2012, #Clinical Orthopaedics and Related Research®
            12160 : 2012, #Annals of Behavioral Medicine
            12199 : 2012, #Environmental Health and Preventive Medicine
            12522 : 2012, #Reproductive Medicine and Biology
            13295 : 2012, #e-Neuroforum
            13594 : 2012, #Dairy Science & Technology
        }

        # for some journals, the national licence doesn't start with volume 1 altough Springer delivered all the metadata
        self.journalsWithASpecialStartYear = {
            12630: 2005,  # Canadian Journal of Anaesthesia
            13414: 2005,  # Perception & Psychophysics
            13428: 2005,  # Behavior Research Methods & Instrumentation
            12662: 2005,  # Sportwissenschaft
            13420: 2005,  # Animal Learning & Behavior
            13421: 2005,  # Memory & Cognition
            11837: 2005,  # JOM
            12297: 2005,  # Zeitschrift für die gesamte Versicherungswissenschaft
            11401: 2005,  # Chinese Annals of Mathematics, Series B
            13138: 2005,  # Journal für Mathematik-Didaktik
            12140: 2005,  # East Asia
            10409: 2005,  # Acta Mechanica Sinica
            12550: 2005,  # Mycotoxin Research
            287: 2005,  # Informatik-Spektrum
            482: 2005,  # Der Schmerz
            10278: 2005,  # Journal of Digital Imaging
            11524: 2005,  # Journal of Urban Health
            13361: 2005,  # Journal of the American Society for Mass Spectrometry
            717: 2005,  # Spektrum der Augenheilkunde
            591: 2005,  # Mathematische Semesterberichte
            10043: 2005,  # Optical Review
            101: 2005,  # Der Anaesthesist
            105: 2005,  # Der Hautarzt
            13423: 2005,  # Psychonomic Bulletin & Review
            292: 2005,  # Der Pathologe
            10291: 2005,  # GPS Solutions
            10699: 2005,  # Foundations of Science
            12160: 2005,  # Annals of Behavioral Medicine
            450: 2005,  # Informatik Forschung und Entwicklung
            104: 2005,  # Der Chirurg
            106: 2005,  # HNO
            112: 2005,  # Monatsschrift Kinderheilkunde
            113: 2005,  # Der Unfallchirurg
            11325: 2005,  # Sleep and Breathing
            11448: 2005,  # Journal of Experimental and Theoretical Physics Letters
            115: 2005,  # Der Nervenarzt
            117: 2005,  # Der Radiologe
            120: 2005,  # Der Urologe
            12199: 2005,  # Environmental Health and Preventive Medicine
            12549: 2005,  # Senckenbergiana lethaea
            129: 2005,  # Der Gynäkologe
            132: 2005,  # Der Orthopäde
            278: 2005,  # Psychotherapeut
            347: 2005,  # Der Ophthalmologe
            761: 2005,  # Der Onkologe
            767: 2005,  # Grundwasser
            780: 2005,  # Finance and Stochastics
            10006: 2005,  # Mund-, Kiefer- und Gesichtschirurgie
            10008: 2005,  # Journal of Solid State Electrochemistry
            10009: 2005,  # International Journal on Software Tools for Technology Transfer
            10014: 2005,  # Brain Tumor Pathology
            10015: 2005,  # Artificial Life and Robotics
            10029: 2005,  # Hernia
            10048: 2005,  # Neurogenetics
            10049: 2005,  # Notfall + Rettungsmedizin
            10157: 2005,  # Clinical and Experimental Nephrology
            10266: 2005,  # Odontology
            103: 2005,  # Bundesgesundheitsblatt - Gesundheitsforschung - Gesundheitsschutz
            10456: 2005,  # Angiogenesis
            10461: 2005,  # AIDS and Behavior
            10492: 2005,  # Applications of Mathematics
            10563: 2005,  # Catalysis Surveys from Asia
            10587: 2005,  # Czechoslovak Mathematical Journal
            10596: 2005,  # Computational Geosciences
            10618: 2005,  # Data Mining and Knowledge Discovery
            10707: 2005,  # GeoInformatica
            10761: 2005,  # International Journal of Historical Archaeology
            108: 2005,  # Der Internist
            10828: 2005,  # The Journal of Comparative Germanic Linguistics
            10832: 2005,  # Journal of Electroceramics
            10840: 2005,  # Journal of Interventional Cardiac Electrophysiology
            10841: 2005,  # Journal of Insect Conservation
            10878: 2005,  # Journal of Combinatorial Optimization
            10892: 2005,  # The Journal of Ethics
            10950: 2005,  # Journal of Seismology
            10995: 2005,  # Maternal and Child Health Journal
            10997: 2005,  # Journal of Management & Governance
            11043: 2005,  # Mechanics of Time-Dependent Materials
            11044: 2005,  # Multibody System Dynamics
            11099: 2005,  # Photosynthetica
            11117: 2005,  # Positivity
            11139: 2005,  # The Ramanujan Journal
            11252: 2005,  # Urban Ecosystems
            11407: 2005,  # International Journal of Hindu Studies
            11425: 2005,  # Science in China Series A: Mathematics
            11430: 2005,  # Science in China Series D: Earth Sciences
            11447: 2005,  # Journal of Experimental and Theoretical Physics
            11451: 2005,  # Physics of the Solid State
            11453: 2005,  # Semiconductors
            11454: 2005,  # Technical Physics
            11455: 2005,  # Technical Physics Letters
            11605: 2005,  # Journal of Gastrointestinal Surgery
            11738: 2005,  # Acta Physiologiae Plantarum
            11818: 2005,  # Somnologie - Schlafforschung und Schlafmedizin
            11858: 2005,  # ZDM
            12374: 2005,  # Journal of Plant Biology
            194: 2005,  # Rechtsmedizin
            26: 2005,  # Annals of Combinatorics
            337: 2005,  # Manuelle Medizin
            392: 2005,  # Zeitschrift für Kardiologie
            393: 2005,  # Zeitschrift für Rheumatologie
            399: 2005,  # Herzschrittmachertherapie und Elektrophysiologie
            500: 2005,  # Soft Computing
            502: 2005,  # e&i Elektrotechnik und Informationstechnik
            53: 2005,  # coloproctology
            548: 2005,  # STANDORT
            59: 2005,  # Herz
            6: 2005,  # Advances in Applied Clifford Algebras
            62: 2005,  # Clinical Neuroradiology
            63: 2005,  # Medizinische Klinik
            66: 2005,  # Strahlentherapie und Onkologie
            772: 2005,  # Gefässchirurgie
            779: 2005,  # Personal and Ubiquitous Computing
            784: 2005,  # Clinical Oral Investigations
            791: 2005,  # Computing and Visualization in Science
            792: 2005,  # Extremophiles
            799: 2005,  # International Journal on Digital Libraries
            10018: 2005,  # Environmental Economics and Policy Studies
            10021: 2005,  # Ecosystems
            10032: 2005,  # International Journal on Document Analysis and Recognition
            10035: 2005,  # Granular Matter
            10039: 2005,  # Trauma und Berufskrankheit
            10044: 2005,  # Pattern Analysis and Applications
            10047: 2005,  # Journal of Artificial Organs
            10050: 2005,  # The European Physical Journal A - Hadrons and Nuclei
            10051: 2005,  # The European Physical Journal B - Condensed Matter and Complex Systems
            10053: 2005,  # The European Physical Journal D - Atomic, Molecular, Optical and Plasma Physics
            10071: 2005,  # Animal Cognition
            10086: 2005,  # Journal of Wood Science
            10098: 2005,  # Clean Technologies and Environmental Policy
            10120: 2005,  # Gastric Cancer
            10458: 2005,  # Autonomous Agents and Multi-Agent Systems
            10468: 2005,  # Algebras and Representation Theory
            10544: 2005,  # Biomedical Microdevices
            10567: 2005,  # Clinical Child and Family Psychology Review
            10586: 2005,  # Cluster Computing
            10677: 2005,  # Ethical Theory and Moral Practice
            10683: 2005,  # Experimental Economics
            10687: 2005,  # Extremes
            10729: 2005,  # Health Care Management Science
            10857: 2005,  # Journal of Mathematics Teacher Education
            10984: 2005,  # Learning Environments Research
            11019: 2005,  # Medicine, Health Care and Philosophy
            11102: 2005,  # Pituitary
            11203: 2005,  # Statistical Inference for Stochastic Processes
            11280: 2005,  # World Wide Web
            11743: 2005,  # Journal of Surfactants and Detergents
            11748: 2005,  # The Japanese Journal of Thoracic and Cardiovascular Surgery
            12650: 2005,  # Journal of Visualization
            13147: 2005,  # Raumforschung und Raumordnung
            142: 2005,  # Arthroskopie
            350: 2005,  # Medizinrecht
            391: 2005,  # Zeitschrift für Gerontologie und Geriatrie
            40802: 2005,  # Netherlands International Law Review
            451: 2005,  # Forum der Psychoanalyse
            481: 2005,  # Ethik in der Medizin
            737: 2005,  # Archives of Women's Mental Health
            10109: 2005,  # Journal of Geographical Systems
            10113: 2005,  # Regional Environmental Change
            10115: 2005,  # Knowledge and Information Systems
            10126: 2005,  # Marine Biotechnology
            10151: 2005,  # Techniques in Coloproctology
            10163: 2005,  # Journal of Material Cycles and Waste Management
            10211: 2005,  # acta ethologica
            10530: 2005,  # Biological Invasions
            10676: 2005,  # Ethics and Information Technology
            10698: 2005,  # Foundations of Chemistry
            10791: 2005,  # Information Retrieval
            10796: 2005,  # Information Systems Frontiers
            10818: 2005,  # Journal of Bioeconomics
            10903: 2005,  # Journal of Immigrant and Minority Health
            11009: 2005,  # Methodology and Computing in Applied Probability
            11051: 2005,  # Journal of Nanoparticle Research
            11066: 2005,  # NETNOMICS: Economic Research and Electronic Networking
            11107: 2005,  # Photonic Network Communications
            11119: 2005,  # Precision Agriculture
            11908: 2005,  # Current Infectious Disease Reports
            11940: 2005,  # Current Treatment Options in Neurology
            12142: 2005,  # Human Rights Review
            12248: 2005,  # The AAPS Journal
            16: 2005,  # Physics in Perspective
            180: 2005,  # Computational Statistics
            21: 2005,  # Journal of Mathematical Fluid Mechanics
            4: 2005,  # Nexus Network Journal
            10101: 2005,  # Economics of Governance
            10142: 2005,  # Functional & Integrative Genomics
            10162: 2005,  # Journal of the Association for Research in Otolaryngology
            10189: 2005,  # The European Physical Journal E
            10198: 2005,  # The European Journal of Health Economics
            10201: 2005,  # Limnology
            10327: 2005,  # Journal of General Plant Pathology
            10522: 2005,  # Biogerontology
            10541: 2005,  # Biochemistry (Moscow)
            10561: 2005,  # Cell and Tissue Banking
            10592: 2005,  # Conservation Genetics
            10595: 2005,  # Colloid Journal
            10631: 2005,  # Doklady Chemistry
            10710: 2005,  # Genetic Programming and Evolvable Machines
            10720: 2005,  # Glass Physics and Chemistry
            10733: 2005,  # High Energy Chemistry
            10740: 2005,  # High Temperature
            10742: 2005,  # Health Services and Outcomes Research Methodology
            10747: 2005,  # Human Physiology
            10786: 2005,  # Instruments and Experimental Techniques
            10789: 2005,  # Inorganic Materials
            10799: 2005,  # Information Technology and Management
            10809: 2005,  # Journal of Analytical Chemistry
            10833: 2005,  # Journal of Educational Change
            10902: 2005,  # Journal of Happiness Studies
            10969: 2005,  # Journal of Structural and Functional Genomics
            10975: 2005,  # Kinetics and Catalysis
            11021: 2005,  # Microbiology
            11081: 2005,  # Optimization and Engineering
            11121: 2005,  # Prevention Science
            11154: 2005,  # Reviews in Endocrine and Metabolic Disorders
            11175: 2005,  # Russian Journal of Electrochemistry
            11181: 2005,  # Russian Journal of Nondestructive Testing
            11220: 2005,  # Subsurface Sensing Technologies and Applications
            11236: 2005,  # Theoretical Foundations of Chemical Engineering
            11268: 2005,  # Water Resources
            11299: 2005,  # Mind & Society
            11441: 2005,  # Acoustical Physics
            11443: 2005,  # Astronomy Letters
            11444: 2005,  # Astronomy Reports
            11445: 2005,  # Crystallography Reports
            11446: 2005,  # Doklady Physics
            11449: 2005,  # Optics and Spectroscopy
            11450: 2005,  # Physics of Atomic Nuclei
            11452: 2005,  # Plasma Physics Reports
            11577: 2005,  # KZfSS Kölner Zeitschrift für Soziologie und Sozialpsychologie
            11582: 2005,  # Journal of Zhejiang University-SCIENCE A
            11609: 2005,  # Berliner Journal für Soziologie
            11612: 2005,  # Gruppe. Interaktion. Organisation. Zeitschrift für Angewandte Organisationspsychologie (GIO)
            11613: 2005,  # Organisationsberatung, Supervision, Coaching
            11616: 2005,  # Publizistik
            11618: 2005,  # Zeitschrift für Erziehungswissenschaft
            11864: 2005,  # Current Treatment Options in Oncology
            12027: 2005,  # ERA Forum
            12064: 2005,  # Theory in Biosciences
            12094: 2005,  # Clinical and Translational Oncology
            12134: 2005,
        # Journal of International Migration and Integration / Revue de l'integration et de la migration internationale
            12176: 2005,  # Controlling & Management
            12221: 2005,  # Fibers and Polymers
            12249: 2005,  # AAPS PharmSciTech
            12325: 2005,  # Advances in Therapy
            12596: 2005,  # Journal of Optics
            13105: 2005,  # Journal of Physiology and Biochemistry
            23: 2005,  # Annales Henri Poincaré
            40804: 2005,  # European Business Organization Law Review
            10207: 2005,  # International Journal of Information Security
            10208: 2005,  # Foundations of Computational Mathematics
            10209: 2005,  # Universal Access in the Information Society
            10238: 2005,  # Clinical and Experimental Medicine
            10396: 2005,  # Journal of Medical Ultrasonics
            10502: 2005,  # Archival Science
            10652: 2005,  # Environmental Fluid Mechanics
            10660: 2005,  # Electronic Commerce Research
            10689: 2005,  # Familial Cancer
            10754: 2005,  # International Journal of Health Care Finance and Economics
            10775: 2005,  # International Journal for Educational and Vocational Guidance
            11067: 2005,  # Networks and Spatial Economics
            11115: 2005,  # Public Organization Review
            11137: 2005,  # Radiochemistry
            11167: 2005,  # Russian Journal of Applied Chemistry
            11176: 2005,  # Russian Journal of General Chemistry
            11178: 2005,  # Russian Journal of Organic Chemistry
            11368: 2005,  # Journal of Soils and Sediments
            11408: 2005,  # Financial Markets and Portfolio Management
            11614: 2005,  # Österreichische Zeitschrift für Soziologie
            11712: 2005,  # Dao
            11892: 2005,  # Current Diabetes Reports
            11910: 2005,  # Current Neurology and Neuroscience Reports
            12012: 2005,  # Cardiovascular Toxicology
            13246: 2005,  # Australasian Physics & Engineering Sciences in Medicine
            13253: 2005,  # Journal of Agricultural, Biological, and Environmental Statistics
            13364: 2005,  # Acta Theriologica
            13365: 2005,  # Journal of NeuroVirology
            13415: 2005,  # Cognitive, Affective, & Behavioral Neuroscience
            28: 2005,  # Journal of Evolution Equations
            10237: 2005,  # Biomechanics and Modeling in Mechanobiology
            10258: 2005,  # Portuguese Economic Journal
            10270: 2005,  # Software & Systems Modeling
            10304: 2005,  # Gynäkologische Endokrinologie
            10343: 2005,  # Gesunde Pflanzen
            10671: 2005,  # Educational Research for Policy and Practice
            10700: 2005,  # Fuzzy Optimization and Decision Making
            10825: 2005,  # Journal of Computational Electronics
            10993: 2005,  # Language Policy
            11047: 2005,  # Natural Computing
            11097: 2005,  # Phenomenology and the Cognitive Sciences
            11101: 2005,  # Phytochemistry Reviews
            11128: 2005,  # Quantum Information Processing
            11157: 2005,  # Reviews in Environmental Science and Bio/Technology
            11557: 2005,  # Mycological Progress
            12017: 2005,  # NeuroMolecular Medicine
            12136: 2005,  # Acta Analytica
            12311: 2005,  # The Cerebellum
            12522: 2005,  # Reproductive Medicine and Biology
            12565: 2005,  # Anatomical Science International
            13577: 2005,  # Human Cell
            40194: 2005,  # Welding in the World
            10257: 2005,  # Information Systems and e-Business Management
            10287: 2005,  # Computational Management Science
            10288: 2005,  # 4OR
            10308: 2005,  # Asia Europe Journal
            10309: 2005,  # Zeitschrift für Epileptologie
            10311: 2005,  # Environmental Chemistry Letters
            10333: 2005,  # Paddy and Water Environment
            10354: 2005,  # Wiener Medizinische Wochenschrift
            10388: 2005,  # Esophagus
            10518: 2005,  # Bulletin of Earthquake Engineering
            10723: 2005,  # Journal of Grid Computing
            10763: 2005,  # International Journal of Science and Mathematics Education
            10805: 2005,  # Journal of Academic Ethics
            10843: 2005,  # Journal of International Entrepreneurship
            10888: 2005,  # The Journal of Economic Inequality
            10951: 2005,  # Journal of Scheduling
            11129: 2005,  # Quantitative Marketing and Economics
            11150: 2005,  # Review of Economics of the Household
            11518: 2005,  # Journal of Systems Science and Systems Engineering
            12021: 2005,  # Neuroinformatics
            187: 2005,  # Zeitschrift für Planung & Unternehmenssteuerung
            508: 2005,  # Wiener klinische Wochenschrift
            10182: 2005,  # AStA Advances in Statistical Analysis
            10339: 2005,  # Cognitive Processing
            10341: 2005,  # Erwerbs-Obstbau
            10346: 2005,  # Landslides
            10357: 2005,  # Natur und Recht
            10368: 2005,  # International Economics and Economic Policy
            10384: 2005,  # Japanese Journal of Ophthalmology
            10393: 2005,  # EcoHealth
            10397: 2005,  # Gynecological Surgery
            10404: 2005,  # Microfluidics and Nanofluidics
            10405: 2005,  # Der Pneumologe
            10433: 2005,  # European Journal of Ageing
            10999: 2005,  # International Journal of Mechanics and Materials in Design
            11302: 2005,  # Purinergic Signalling
            11332: 2005,  # Sport Sciences for Health
            11633: 2005,  # International Journal of Automation and Computing
            11904: 2005,  # Current HIV/AIDS Reports
            12028: 2005,  # Neurocritical Care
            12054: 2005,  # Sozial Extra
            15: 2005,  # Swiss Journal of Geosciences
            44: 2005,  # Medicinal Chemistry Research
            9: 2005,  # Mediterranean Journal of Mathematics
        }

        PersistRecordMongo.__init__(self)

    def  processRecord(self, taskContext=None):
        originalRecord = taskContext.getRecord()
        modsRecord = taskContext.getModsRecord()

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()

        isDeleted = taskContext.isDeleted()


        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]


            mongoRecord = tCollection.find_one({"_id": rid})
            modsBinary = Binary( zlib.compress(modsRecord,9))

            recordTree=etree.fromstring(modsRecord)

            # Get year from MODS XML
            xpathGetYear = "//ns:originInfo/ns:dateIssued[@encoding='w3cdtf']" #result is like that 2002-12-23
            fullDate = recordTree.xpath(xpathGetYear, namespaces={'ns' : 'http://www.loc.gov/mods/v3'})

            year=0
            if len(fullDate) > 0 :
                year=int(fullDate[0].text[0:4])

            xpathGetJournalId = "//ns:relatedItem[@type='host']/ns:identifier[@type='PublisherID']"
            journalIdRE = recordTree.xpath(xpathGetJournalId, namespaces={'ns': 'http://www.loc.gov/mods/v3'})

            journalId=0
            if len(journalIdRE) > 0 :
                journalId=int(journalIdRE[0].text)

            includedInNationalLicences=""

            if journalId in self.nationalLicencesJournals:
                if journalId in self.journalsWithASpecialEndYear:
                    if year <= self.journalsWithASpecialEndYear[journalId]:
                        includedInNationalLicences="yes"
                    else:
                        includedInNationalLicences="no"
                elif journalId in self.journalsWithASpecialStartYear:
                    if year >= self.journalsWithASpecialStartYear[journalId]:
                        includedInNationalLicences="yes"
                    else:
                        includedInNationalLicences="no"
                else:
                    includedInNationalLicences="yes"
            else:
                includedInNationalLicences="no"


            #print str(journalId) + " " + str(year) + " " + includedInNationalLicences




            if not mongoRecord:
                #record isn't in database so far
                newRecord = {"_id":rid,
                             "datum":str(datetime.now())[:10],
                             "year":year,
                             "status": "new",
                             "includedInNationalLicences" : includedInNationalLicences,
                             "journalId" : journalId,
                             #"jatsRecord":jatsBinary,
                             "modsRecord": modsBinary
                             }

                tCollection.insert(newRecord)
                taskContext.getResultCollector().addRecordsToCBSInserted(1)

            else:
                #there is already a record with the current id in the database
                if isDeleted:
                    status = "deleted"
                    taskContext.getResultCollector().addRecordsDeleted(1)

                else:
                    status = "updated"
                    taskContext.getResultCollector().addRecordsToCBSUpdated(1)

                mongoRecord["year"] = year
                mongoRecord["modsRecord"] = modsBinary
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]
                mongoRecord["journalId"] = journalId
                mongoRecord["includedInNationalLicences"] = includedInNationalLicences

                #tCollection.save(mongoRecord, safe=True)
                tCollection.replace_one({"_id": rid}, mongoRecord)


        except Exception as tException:
            #todo: do something meaningful with the exception
            print tException




class PersistDSV11RecordMongo(PersistRecordMongo):

    def __init__(self):
        PersistRecordMongo.__init__(self)

        self.matchTagCodes = {'100': None, '110': None,'111': None, '130':None,'152':None}
        self.originalTagCodes = {'100': None, '110': None,'111': None, '130':None,'152':None}

        self.regexNoSort = re.compile("<<.*?>>", re.UNICODE)
        self.regexCreateMatch = re.compile("[\W]", re.UNICODE)



    def  processRecord(self, taskContext=None ):

        for key in self.matchTagCodes:
            self.matchTagCodes[key] = None
        for key in self.originalTagCodes:
            self.originalTagCodes[key] = None


        #todo: search for recordID if None -> use HasType

        #Problemsatz
        #{ "_id" : "(DSV11)oai:alephtest.unibas.ch:DSV11-000000020", "status" : "new", "match130" : "targumyerushalmiii",
        # "match151" : null, "match150" : null, "match100" : "echovantonpavloviostrovsachalin", "dbid" : "000000020", "match110" : null, "datum" : "2014-03-11",
        # "additionalvalues" : { "400" : [ "Čechov, Anton Pavlovič", "<<Die>> Insel Sachalin" ] }, "org150" : null, "org151" : null,
        # "org100" : [ "Čechov, Anton Pavlovič", "Ostrov Sachalin" ], "org110" : null, "org130" : [ "Targum Yerushalmi II" ], "record" : BinData(") }
        #das ist jetzt besser durch re.UNICODE

        #Frage
        #ich habe zwei matchkeys aber nicht mehere 400er values - richtig?
        #{ "_id" : "(DSV11)oai:alephtest.unibas.ch:DSV11-000000054", "status" : "new", "match130" : "targumyerushalmiii", "match151" : null, "match150" : null,
        # "match100" : "cioranemilemicheltentationdexister", "dbid" : "000000054", "match110" : null, "datum" : "2014-03-11",
        # "additionalvalues" : { "400" : [ "Cioran, Emile Michel", "Dasein als Versuchung" ] }, "org150" : null, "org151" : null,
        # "org100" : [ "Cioran, Emile Michel", "<<La>> tentation d'exister" ], "org110" : null, "org130" : [ "Targum Yerushalmi II" ], "record" : BinData() }



        #if rid is None or dbWrapper is None:
        #    raise Exception("[harvestingTasks.py] in PersistRecordMongo.procesRecord: id of record must not be None and dbWrapper must not be None")

        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistDNBGNDRecordMongo.procesRecord: no valid taskContext")

        dbWrapper = taskContext.getDBWrapper()
        rid = taskContext.getID()
        record = taskContext.getRecord()
        isDeleted = taskContext.isDeleted()


        recordTimestamp = taskContext.getRecordTimestamp()

        if not recordTimestamp is None:
            try:
                recordTimestamp = datetime.strptime(recordTimestamp, "%Y-%m-%dT%H:%M:%SZ")
            except:
                recordTimestamp = None

        try:
            tCollection = dbWrapper.getDBConnections()["nativeSources"]["collections"]["sourceDB"]

            status = None
            #if re.search("status=\"deleted\"",record,re.UNICODE | re.DOTALL):
            selectedMatchFields = {}
            selectedAdditionalValues = {}
            cDSV11Content = CollectDSV11Content()

            if isDeleted:
                dbid = None
                #selectedAdditionalValues = {}
                status = "deleted"
            else:
                #cGNDContent = CollectDSV11Content()

                xml.sax.parseString("".join(record), cDSV11Content)

                selectedMatchFields = cDSV11Content.getSelectedMatchValues()
                selectedAdditionalValues = cDSV11Content.getSelectedAdditionalValues()

                #tId = result["id"]
                #dbidhas to be deleted in the GNDFieldsValueStructure
                dbid = selectedMatchFields["dbid"]
                selectedMatchFields.pop("dbid")

                #regex = re.compile("[^\\p{L}\\p{M}*\\p{N}]", re.UNICODE | re.DOTALL)
                #regex = re.compile(r"[^\p{L}\p{M}*\p{N}]")
                for key,valueList in selectedMatchFields.items():
                    self.originalTagCodes[key] = valueList
                    self.matchTagCodes[key] = self.buildMatchKey(valueList)

            mongoRecord = tCollection.find_one({"_id": rid})
            binary = Binary( zlib.compress(record,9))


            if not mongoRecord:
                if status is None:
                    status = "new"
                newRecord = {"_id":rid,
                             "datum":str(datetime.now())[:10],
                             "dbid" : dbid,
                             "match100": self.matchTagCodes['100'],
                             "match110": self.matchTagCodes['110'],
                             "match111": self.matchTagCodes['111'],
                             "match130": self.matchTagCodes['130'],
                             "match152": self.matchTagCodes['152'],
                             "org100" : self.originalTagCodes['100'],
                             "org110" : self.originalTagCodes['110'],
                             "org111" : self.originalTagCodes['111'],
                             "org130" : self.originalTagCodes['130'],
                             "org152" : self.originalTagCodes['152'],
                             "record":binary,
                             "additionalvalues":selectedAdditionalValues,
                             "status":status,
                             "recordTimestamp": recordTimestamp
                }

                tCollection.insert(newRecord)

            else:

                if status is None:
                    status = "updated"

                #todo: Suche nach deleted record!
                mongoRecord["record"] = binary
                #mongoRecord["gndid"] = gndid
                mongoRecord["dbid"] = dbid
                mongoRecord["match100"] = self.matchTagCodes['100'],
                mongoRecord["match110"] = self.matchTagCodes['110'],
                mongoRecord["match111"] = self.matchTagCodes['111'],
                mongoRecord["match130"] = self.matchTagCodes['130'],
                mongoRecord["match152"] = self.matchTagCodes['152'],
                mongoRecord["org100"] = self.originalTagCodes['100'],
                mongoRecord["org110"] = self.originalTagCodes['110'],
                mongoRecord["org111"] = self.originalTagCodes['111'],
                mongoRecord["org130"] = self.originalTagCodes['130'],
                mongoRecord["org152"] = self.originalTagCodes['152'],
                mongoRecord["status"] = status
                mongoRecord["datum"] = str(datetime.now())[:10]
                mongoRecord["additionalvalues"] = selectedAdditionalValues
                mongoRecord["recordTimestamp"] = recordTimestamp

                #tCollection.save(mongoRecord,safe=True)
                tCollection.replace_one({"_id": rid}, mongoRecord)


        except Exception as tException:


            print "fehler in record"
            print str(tException)
            print record

            message = ["error while persisting gnd record against Mongo\n",
                       "docid: ", rid,
                       "SytemInfo: ", sys.exc_info()]
            #raise ErrorMongoProcessing(message)

    def  buildMatchKey(self, valueList ):
        newList = []
        for value in valueList:
            #newValue = regex.sub("",value)
            #newValue = re.sub("[^\\p{L}\\p{M}*\\p{N}]","",value,1000,re.UNICODE | re.DOTALL)
            #value = "test<<der>>" + value + "<<la>>" + "nun das ende"
            #value = self.regexNoSort.sub("",value,10000)
            #test = re.sub("<<.*?>>","",value,10000)
            #newValue = re.sub("[\W]","",value,10000).lower()
            value = self.regexCreateMatch.sub("",value,10000).lower()
            #newValue = newValue.lower()
            #newValue1 = re.sub("[^\p{L}\p{M}*\p{N}]","",value,re.UNICODE )
            newList.append(value)

        return "".join(newList)


class PersistInitialDNBGNDRecordMongo(PersistDNBGNDRecordMongo):
    def __init__(self):
        PersistDNBGNDRecordMongo.__init__(self)

        self.header= "<record>\n<header>\n<identifier>valuerecordid</identifier>\n<datestamp>valuedatestamp</datestamp>\n<setSpec>authorities</setSpec>\n</header>\n<metadata>\n"

    def  processRecord(self, taskContext=None ):


        if taskContext is None or  not isinstance(taskContext,StoreNativeRecordContext):
            raise Exception("[harvestingTasks.py] in PersistInitialDNBGNDRecordMongo.procesRecord: no valid taskContext")



        #clean up the record
        #for GND we doesn't want to use whole OAI record as we did before

        taskContext.setRecord(re.sub("<record .*?type=.*?>","<record type=\"Authority\" xmlns=\"http://www.loc.gov/MARC21/slim\">",
                                     taskContext.getRecord(),re.UNICODE | re.DOTALL))

        taskContext.setID("(" + taskContext.getConfiguration().getNetworkPrefix() + ")" + taskContext.getID())
        PersistDNBGNDRecordMongo.processRecord(self,taskContext=taskContext)





class RecordDirectToSearchEngine(HarvestingTask):

    def __init__(self,element):
        HarvestingTask.__init__(self)


    def  processRecord(self, taskContext=None):
        pass


class WriteModsForCBS(HarvestingTask):
    #not used any more I think (lio, 10.3.2017)
    def __init__(self):
        HarvestingTask.__init__(self)

        #self.doctypePattern = re.compile('<!DOCTYPE.*?>', re.UNICODE | re.DOTALL | re.IGNORECASE)
        #self.articleStructure = re.compile('.*?(<article .*?</article>).*', re.UNICODE | re.DOTALL | re.IGNORECASE)

    def processRecord(self, taskContext=None):

        taskContext.appContext.getWriteContext().writeItem(taskContext.getModsRecord())
            #print(etree.tostring(mods, pretty_print=True))

class CollectGNDContent(ContentHandler):

    def __init__(self):
        ContentHandler.__init__(self)
        #TAGS.TO.USE=400_a###400_b###400_c###400_d###400_x###410_a###410_b###411_a###411_b###430_a###450_a###450_x###451_a###451_x
        self.searchedTagCodes = {'400': ['a','b','c','d','x'], '410': ['a','b'], '411': ['a','b'],'430':['a'],'450':['a','x'],'451':['a','x']}
        #self.searchedTagMacCodes = {'750': ['a','b','v','x','y','z','0','2','5']}
        self.searchedTagMacCodes = {'750': ['a']}
        self.foundTagCodesValues ={}
        self.foundMACSTagCodesValues ={}
        self.lastValidTag = None
        self.lastValidSubFieldCode = None
        self.tagName = ""

        self.procContentSubfield = {}
        self.relevantGNDIDdatafield = "035"
        self.relevantGNDIDsubfield = "a"
        self.inGNDIDField = False
        self.inGNDIDsubfield = False

        self.pGNDIDPattern = re.compile("\(DE-588\)",re.UNICODE | re.DOTALL | re.IGNORECASE)

        #self.


    def getSelectedValues(self):
        return self.foundTagCodesValues

    def getSelectedMACSValues(self):
        return self.foundMACSTagCodesValues



    def startElement(self, name, attrs):

        if name.find('slim:controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('slim:datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes or attrs.get("tag") in self.searchedTagMacCodes:
                self.lastValidTag = attrs.get("tag")
            else:
                self.lastValidTag = None
        elif name.find("slim:subfield") != -1:
            if self.lastValidTag is not None:
                self.lastValidSubFieldCode = attrs.get("code")
            else:
                self.lastValidSubFieldCode = None
            if self.inGNDIDField and attrs.get("code") == self.relevantGNDIDsubfield:
                self.inGNDIDsubfield = True
            else:
                self.inGNDIDsubfield = False


        else:
            self.lastValidTag = None
            self.lastValidSubFieldCode = None
        if name.find('slim:datafield') != -1:
            if attrs.get("tag") == self.relevantGNDIDdatafield:
                self.inGNDIDField = True
            else:
                self.inGNDIDField = False





    def endElement(self, name):
        if name.find("slim:subfield") != -1:
            t = self.procContentSubfield.items()
            if self.procContentSubfield.__len__() > 0:
                for key in self.procContentSubfield:

                    if self.lastValidTag in self.searchedTagCodes:
                        if key in self.foundTagCodesValues:
                            self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    elif self.lastValidTag in self.searchedTagMacCodes:
                        if key in self.foundMACSTagCodesValues:
                            self.foundMACSTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundMACSTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    else:
                        print "can't assign last valid to to any searchedTagCodes in endElement"
            self.procContentSubfield = {}
            self.lastValidSubFieldCode = None
        elif name.find('slim:datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None



    def characters(self, content):
        if self.tagName == "controlfield_001":
            self.foundTagCodesValues["dbid"] = content.rstrip()
            self.tagName = ""
        if self.lastValidTag is not None and   self.lastValidSubFieldCode is not None:
            if self.lastValidTag in self.searchedTagCodes:

                if self.lastValidSubFieldCode in self.searchedTagCodes[self.lastValidTag]:

                    #Warum dieser "Zwischenspeicher" self.procContentSubfield
                    #{u'400_a': [u'Cresse\u0301, Auguste J. ', u'\x98', u'de', u'\x9c']}
                    #{u'400_a': [u'Cresse\u0301, Auguste J. \x98de\x9c']}
                    #Es gibt Werte von tags wie der gezeigte, fuer die der character handler des Sax Parsers mehrfach aufgerufen wird,
                    #ohne dass zuvor der endElement Handler fuer das subfield aufgerufen wuerde
                    #schriebe man den Wert von content dann direkt nach self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode]
                    #werden die Elemente im Beipiel als einzelne items der Liste gesetzt und als mehrfache Werte des Codes 400_a behandelt


                    if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.procContentSubfield:
                        self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content.rstrip())
                    else:
                        self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content.rstrip()]
                        #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.foundTagCodesValues:
                        #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                        #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                        #else:
                        #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
                        #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
            elif self.lastValidTag in self.searchedTagMacCodes:
                if self.lastValidSubFieldCode in self.searchedTagMacCodes[self.lastValidTag]:


                    if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.procContentSubfield:
                        self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content.rstrip())
                    else:
                        self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content.rstrip()]
                        #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.foundTagCodesValues:
                        #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                        #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                        #else:
                        #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
                        #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
            else:
                print "tag: " + self.lastValidTag + " not part of any search dictionaries (GND or MACS)"

        elif self.inGNDIDsubfield:

            if self.pGNDIDPattern.search(content):
                self.foundTagCodesValues["gndid"] = content.rstrip()
                #self.gndSearchID = content

            self.inGNDIDsubfield = False





class CollectGNDContentNoNamespace(CollectGNDContent):
    def __init__(self):
        CollectGNDContent.__init__(self)

    def startElement(self, name, attrs):

        if name.find('controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes or attrs.get("tag") in self.searchedTagMacCodes:
                self.lastValidTag = attrs.get("tag")
            else:
                self.lastValidTag = None
        elif name.find("subfield") != -1:
            if self.lastValidTag is not None:
                self.lastValidSubFieldCode = attrs.get("code")
            else:
                self.lastValidSubFieldCode = None
            if self.inGNDIDField and attrs.get("code") == self.relevantGNDIDsubfield:
                self.inGNDIDsubfield = True
            else:
                self.inGNDIDsubfield = False


        else:
            self.lastValidTag = None
            self.lastValidSubFieldCode = None
        if name.find('datafield') != -1:
            if attrs.get("tag") == self.relevantGNDIDdatafield:
                self.inGNDIDField = True
            else:
                self.inGNDIDField = False





    def endElement(self, name):
        if name.find("subfield") != -1:
            t = self.procContentSubfield.items()
            if self.procContentSubfield.__len__() > 0:
                for key in self.procContentSubfield:

                    if self.lastValidTag in self.searchedTagCodes:
                        if key in self.foundTagCodesValues:
                            self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    elif self.lastValidTag in self.searchedTagMacCodes:
                        if key in self.foundMACSTagCodesValues:
                            self.foundMACSTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                        else:
                            self.foundMACSTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
                    else:
                        print "can't assign last valid to to any searchedTagCodes in endElement"
            self.procContentSubfield = {}
            self.lastValidSubFieldCode = None
        elif name.find('datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None



class CollectDSV11Content(ContentHandler):

    def __init__(self):
        ContentHandler.__init__(self)
        #TAGS.TO.USE=400_a###400_b###400_c###400_d###400_x###410_a###410_b###411_a###411_b###430_a###450_a###450_x###451_a###451_x
        self.searchedTagCodes = {'100': ['a','b','c','d', 'q'],  '110': ['a','b'],'111':['a'], '130': ['a','g','k' ,'m','n' ,'o','p','r','s'],'152':['d']}
        #$a$g$k$m$n$o$p$r$s
        self.additionalAuthorityValue = {'400': ['a','b','c','d','q'], '410': ['a','b'],'411': ['a'], '430': ['a','g','k','m','n','o','p','r','s'], '452':['d'],'500': ['a','b','c','d','q'], '510': ['a','b'],'511': ['a'], '530': ['a','g','k','m','n','o','p','r','s'], '552':['d']}


        #Besonderheiten 130: Oliver sucht nach drei p - Subfields
        #-> Probleme dabei: Reihenfolge / was ist, wenn es nur zwei oder aber vier p - subfields gibt?

        #Besonderheiten 100 / 700:
        # -> c nur das erste subfield -> gibt es nur ein subfield? was wenn mehr?

        #110 verwendet er gar nicht - warum?

        #150 wird nicht verwendet - warum?

        # 151 wird nicht verwendet - warum







        self.foundTagCodesValues ={}
        self.foundTagCodesAuthorityValues ={}
        self.lastValidTag = None
        self.lastValidAuthorityTag = None
        self.lastValidSubFieldCode = None
        self.lastValidAuthoritySubFieldCode = None
        self.tagName = ""

        self.procContentSubfield = {}
        self.procContentAuthoritySubfield = {}
        self.relevantGNDIDdatafield = "035"
        self.relevantGNDIDsubfield = "a"
        self.inGNDIDField = False
        self.inGNDIDsubfield = False

        #self.pGNDIDPattern = re.compile("\(DE-588\)",re.UNICODE | re.DOTALL | re.IGNORECASE)

        #self.


    def getSelectedMatchValues(self):
        return self.foundTagCodesValues

    def getSelectedAdditionalValues(self):
        return self.foundTagCodesAuthorityValues

    def startElement(self, name, attrs):

        if name.find('marc:controlfield') != -1 and attrs.get("tag") == "001":
            self.tagName = "controlfield_001"
        elif name.find('marc:datafield') != -1:
            #print attrs.get("tag")
            if attrs.get("tag") in self.searchedTagCodes:
                self.lastValidTag = attrs.get("tag")
            elif attrs.get("tag") in self.additionalAuthorityValue:
                self.lastValidAuthorityTag = attrs.get("tag")
            else:
                self.lastValidTag = None
                self.lastValidAuthorityTag  = None

        elif name.find("marc:subfield") != -1:
            if self.lastValidTag is not None:
                self.lastValidSubFieldCode = attrs.get("code")
            elif self.lastValidAuthorityTag is not None:
                self.lastValidAuthoritySubFieldCode = attrs.get("code")
            else:
                self.lastValidSubFieldCode = None
                self.lastValidAuthoritySubFieldCode = None
            #if self.inGNDIDField and attrs.get("code") == self.relevantGNDIDsubfield:
            #    self.inGNDIDsubfield = True
            #else:
            #    self.inGNDIDsubfield = False


        else:
            self.lastValidTag = None
            self.lastValidSubFieldCode = None
            self.lastValidAuthorityTag = None
            self.lastValidAuthoritySubFieldCode = None

        #if name.find('slim:datafield') != -1:
        #    if attrs.get("tag") == self.relevantGNDIDdatafield:
        #        self.inGNDIDField = True
        #    else:
        #        self.inGNDIDField = False





    def endElement(self, name):
        if name.find("marc:subfield") != -1:
            #t = self.procContentSubfield.items()
            if self.procContentSubfield.__len__() > 0:
                for key in self.procContentSubfield:

                    if key in self.foundTagCodesValues:
                        self.foundTagCodesValues[key].append("".join(self.procContentSubfield[key]))
                    else:
                        self.foundTagCodesValues[key] = ["".join(self.procContentSubfield[key])]
            elif self.procContentAuthoritySubfield.__len__() > 0:

                for key in self.procContentAuthoritySubfield:

                    if key in self.foundTagCodesAuthorityValues:
                        self.foundTagCodesAuthorityValues[key].append("".join(self.procContentAuthoritySubfield[key]))
                    else:
                        self.foundTagCodesAuthorityValues[key] = ["".join(self.procContentAuthoritySubfield[key])]

            self.procContentSubfield = {}
            self.procContentAuthoritySubfield = {}
            self.lastValidSubFieldCode = None
            self.lastValidAuthoritySubFieldCode = None
        elif name.find('marc:datafield') != -1:
            self.lastValidSubFieldCode = None
            self.lastValidTag = None
            self.lastValidAuthorityTag = None
            self.lastValidAuthoritySubFieldCode = None



    def characters(self, content):
        if self.tagName == "controlfield_001":
            self.foundTagCodesValues["dbid"] = content.rstrip()
            self.tagName = ""
        if self.lastValidTag is not None and   self.lastValidSubFieldCode is not None:
            if self.lastValidSubFieldCode in self.searchedTagCodes[self.lastValidTag]:

                #Warum dieser "Zwischenspeicher" self.procContentSubfield
                #{u'400_a': [u'Cresse\u0301, Auguste J. ', u'\x98', u'de', u'\x9c']}
                #{u'400_a': [u'Cresse\u0301, Auguste J. \x98de\x9c']}
                #Es gibt Werte von tags wie der gezeigte, fuer die der character handler des Sax Parsers mehrfach aufgerufen wird,
                #ohne dass zuvor der endElement Handler fuer das subfield aufgerufen wuerde
                #schriebe man den Wert von content dann direkt nach self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode]
                #werden die Elemente im Beipiel als einzelne items der Liste gesetzt und als mehrfache Werte des Codes 400_a behandelt


                #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.procContentSubfield:
                if self.lastValidTag in self.procContentSubfield:
                    #self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content.rstrip())
                    self.procContentSubfield[self.lastValidTag].append(content.rstrip())
                else:
                    #self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content.rstrip()]
                    self.procContentSubfield[self.lastValidTag] = [content.rstrip()]
                    #if self.lastValidTag + "_" + self.lastValidSubFieldCode in self.foundTagCodesValues:
                    #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                    #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode].append(content)
                    #else:
                    #    self.procContentSubfield[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
                    #self.foundTagCodesValues[self.lastValidTag + "_" + self.lastValidSubFieldCode] = [content]
        elif self.lastValidAuthorityTag is not None and   self.lastValidAuthoritySubFieldCode is not None:
            if self.lastValidAuthoritySubFieldCode in self.additionalAuthorityValue[self.lastValidAuthorityTag]:
                #if self.lastValidAuthorityTag + "_" + self.lastValidAuthoritySubFieldCode in self.procContentAuthoritySubfield:
                if self.lastValidAuthorityTag in self.procContentAuthoritySubfield:
                    #self.procContentAuthoritySubfield[self.lastValidAuthorityTag + "_" + self.lastValidAuthoritySubFieldCode].append(content.rstrip())
                    self.procContentAuthoritySubfield[self.lastValidAuthorityTag].append(content.rstrip())
                else:
                    #self.procContentAuthoritySubfield[self.lastValidAuthorityTag + "_" + self.lastValidAuthoritySubFieldCode] = [content.rstrip()]
                    self.procContentAuthoritySubfield[self.lastValidAuthorityTag] = [content.rstrip()]
        #elif self.inGNDIDsubfield:
        #
        #    if self.pGNDIDPattern.search(content):
        #        self.foundTagCodesValues["gndid"] = content.rstrip()
        #        #self.gndSearchID = content

        #    self.inGNDIDsubfield = False




