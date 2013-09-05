from xml.sax.handler import ContentHandler
import re



__author__ = 'swissbib'



class HashMarcContent(ContentHandler):

    def __init__(self, harvestingConfigs):
        ContentHandler.__init__(self)
        self.tag001 = False
        self.docid = '0'
        self.numericDataField = False
        self.validsubfield = False
        self.marccontent = []
        self.validOAIDC = False
        self.numericControlField = False
        self.harvestingConfigs = harvestingConfigs



    def startElement(self, name, attrs):

        if name.find('marc:datafield') != -1:
            if attrs.get("tag").isnumeric() and not self.isDataTagExcluded(attrs.get("tag")) :
                self.numericDataField = True
            else:
                self.numericDataField = False
        elif name.find('marc:controlfield') != -1:
            #b = attrs.get("tag").isnumeric()
            testAlpha = attrs.get("tag")
            if attrs.get("tag") == '001':
                self.tag001 = True
            elif attrs.get("tag").isnumeric() and testAlpha <> '005':
                self.numericControlField = True
            else:
                self.numericControlField = False



    def endElement(self, name):
        if name.find('marc:datafield') != -1:
            self.numericDataField = False
        elif name.find('marc:controlfield') != -1:
            self.numericControlField = False



    def characters(self, content):
        if self.numericDataField or self.numericControlField:
            #remove EOL and whitespaces at the tail of the line
            self.marccontent.append(content.rstrip())
        elif self.tag001:
            self.docid = content
            self.tag001 = False
        elif self.numericControlField:
            self.marccontent.append(content.rstrip())
        elif self.validOAIDC:
            self.marccontent.append(content.rstrip())




    def getMarccontent(self):
        return "".join(self.marccontent)

    def getDocid(self):
        return self.docid



    def isDataTagExcluded(self,tagValue):

        if not self.harvestingConfigs.getDataTagExcludedFromHash() is None and tagValue in self.harvestingConfigs.getDataTagExcludedFromHash():
            return True
        else:
            return False



class HashNebisMarcContent(HashMarcContent):

    def __init__(self,harvestingConfigs):
        HashMarcContent.__init__(self,harvestingConfigs)


    def startElement(self, name, attrs):

        #Nebis benutzt keine namespaces

        if name.find('datafield') != -1 :
            if attrs.get("tag").isnumeric() and not self.isDataTagExcluded(attrs.get("tag")):
                self.numericDataField = True
            else:
                self.numericDataField = False
        elif name.find('controlfield') != -1:
            #b = attrs.get("tag").isnumeric()
            testAlpha = attrs.get("tag")
            if attrs.get("tag") == '001':
                self.tag001 = True
            elif attrs.get("tag").isnumeric() and testAlpha <> '005':
                self.numericControlField = True
            else:
                self.numericControlField = False



    def endElement(self, name):
        if name.find('datafield') != -1:
            self.numericDataField = False
        elif name.find('controlfield') != -1:
            self.numericControlField = False




class HashSwissBibMarcContent(HashMarcContent):

    def __init__(self, harvestingConfigs):
        HashMarcContent.__init__(self, harvestingConfigs)


    def startElement(self, name, attrs):
        if name.find('mx:datafield') != -1 :
            if attrs.get("tag").isnumeric() and not self.isDataTagExcluded(attrs.get("tag")):
                self.numericDataField = True
            else:
                self.numericDataField = False
        elif name.find('mx:controlfield') != -1:
            test = attrs.get("tag")
            if attrs.get("tag") == '001':
                self.tag001 = True
            elif attrs.get("tag").isnumeric() and test <> '005':
                self.numericControlField = True
            else:
                self.numericControlField = False

    def endElement(self, name):
        if name.find('mx:datafield') != -1:
            self.numericDataField = False
        elif name.find('mx:controlfield') != -1:
            self.numericControlField = False



class HashDcContent(HashMarcContent):

    #todo: sinnvolle Regel um content von DC auszuschliessen, im Moment begrenze ich das auf datafields
    #evtl. sollte man die Ausschlussregel auch auf controlfields anwenden
    #zur Zeit fuer die einzelnen Klassen ausprogrammiert
    def __init__(self, harvestingConfigs):
        HashMarcContent.__init__(self, harvestingConfigs)
        self.pIdentifier = re.compile("^identifier$",re.UNICODE | re.DOTALL | re.IGNORECASE)
        self.pdcField = re.compile("^dc:",re.UNICODE | re.DOTALL | re.IGNORECASE)



    def startElement(self, name, attrs):

        dcField = self.pdcField.search(name)
        ident = self.pIdentifier.search(name)

        if dcField :
            self.validOAIDC = True
        elif  ident:
            self.tag001 = True


    def endElement(self, name):

        if self.pdcField.search(name) or self.pIdentifier.search(name):
            self.validOAIDC = False



class HashReroMarcContent(HashMarcContent):

    def __init__(self, harvestingConfigs):
        HashMarcContent.__init__(self, harvestingConfigs)


    def startElement(self, name, attrs):
        #rero Besonderheit:
        #es wird nicht das Standardattribut tag sonder type fuer controlfields und datafields verwendet
        if name.find('marc:datafield') != -1 and not self.isDataTagExcluded(attrs.get("type")):
            if attrs.get("type").isnumeric():
                self.numericDataField = True
            else:
                self.numericDataField = False
        elif name.find('marc:controlfield') != -1:
            #b = attrs.get("tag").isnumeric()
            testAlpha = attrs.get("type")
            if attrs.get("type") == '001':
                self.tag001 = True
            elif attrs.get("type").isnumeric() and testAlpha <> '005':
                self.numericControlField = True
            else:
                self.numericControlField = False



