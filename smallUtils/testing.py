# -*- coding: utf-8 -*-

__author__ = 'swissbib'



class TestContent:


    def __init__(self):
        pass




    def getWellFormedRecord(self):
        return """
                <record>
                <header>
                <identifier>oai:HSG_Libraries:HSB02-000173039</identifier>
                <datestamp>2013-04-24T16:39:10Z</datestamp>
                <setSpec>SWISSBIB-FULL-HSB02</setSpec>
                </header>
                <metadata>
                <marc:record xmlns:marc="http://www.loc.gov/MARC21/slim" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
                <marc:leader>     nam  22     7u 4500</marc:leader>
                <marc:controlfield tag="FMT">BK</marc:controlfield>
                <marc:controlfield tag="LDR">     nam  22     7u 4500</marc:controlfield>
                <marc:controlfield tag="001">000173039</marc:controlfield>
                <marc:controlfield tag="008">040929s2005                  00    ger d</marc:controlfield>
                <marc:datafield tag="020" ind1=" " ind2=" "><marc:subfield code="a">3-468-20409-4</marc:subfield></marc:datafield>
                <marc:datafield tag="040" ind1=" " ind2=" "><marc:subfield code="a">HPHS</marc:subfield><marc:subfield code="d">HFHB</marc:subfield></marc:datafield>
                <marc:datafield tag="100" ind1=" " ind2=" "><marc:subfield code="a">Worsch, Wolfgang</marc:subfield></marc:datafield>
                <marc:datafield tag="245" ind1=" " ind2=" "><marc:subfield code="a">Grundschulwörterbuch Deutsch</marc:subfield><marc:subfield code="c">Projektl.: Wolfgang Worsch</marc:subfield></marc:datafield>
                <marc:datafield tag="260" ind1=" " ind2=" "><marc:subfield code="a">Berlin &lt;etc.&gt;</marc:subfield><marc:subfield code="b">Langenscheidt</marc:subfield><marc:subfield code="c">2005</marc:subfield></marc:datafield>
                <marc:datafield tag="300" ind1=" " ind2=" "><marc:subfield code="a">192 S.</marc:subfield><marc:subfield code="b">Ill.</marc:subfield></marc:datafield>
                <marc:datafield tag="490" ind1=" " ind2=" "><marc:subfield code="a">Kids</marc:subfield></marc:datafield>
                <marc:datafield tag="690" ind1="H" ind2="P"><marc:subfield code="8">803(03)</marc:subfield><marc:subfield code="a">Deutsch: Wörterbücher</marc:subfield><marc:subfield code="2">PHS</marc:subfield></marc:datafield>
                <marc:datafield tag="650" ind1=" " ind2=" "><marc:subfield code="8">803</marc:subfield><marc:subfield code="a">Deutsch</marc:subfield></marc:datafield>
                <marc:datafield tag="655" ind1=" " ind2=" "><marc:subfield code="8">8(03)</marc:subfield><marc:subfield code="a">Wörterbuch</marc:subfield></marc:datafield>
                <marc:datafield tag="949" ind1=" " ind2=" "><marc:subfield code="b">HPHG</marc:subfield><marc:subfield code="c">MKV</marc:subfield><marc:subfield code="j">803(03)//038</marc:subfield><marc:subfield code="p">HR40005163</marc:subfield><marc:subfield code="q">000173039</marc:subfield><marc:subfield code="r">000010</marc:subfield><marc:subfield code="0">PHSG/RDZ Gossau</marc:subfield><marc:subfield code="1">Migration und Kulturelle Vielfalt</marc:subfield><marc:subfield code="3">LM</marc:subfield><marc:subfield code="4">01</marc:subfield><marc:subfield code="6"></marc:subfield></marc:datafield>
                <marc:datafield tag="AVA" ind1=" " ind2=" "><marc:subfield code="a">HSD52</marc:subfield><marc:subfield code="b">HPHG</marc:subfield><marc:subfield code="c">Migration und Kulturelle Vielfalt</marc:subfield><marc:subfield code="d">803(03)//038</marc:subfield><marc:subfield code="e">available</marc:subfield><marc:subfield code="f">1</marc:subfield><marc:subfield code="g">0</marc:subfield><marc:subfield code="h">N</marc:subfield><marc:subfield code="i">unknown</marc:subfield><marc:subfield code="j">MKV</marc:subfield></marc:datafield>
                <marc:datafield tag="AVA" ind1=" " ind2=" "><marc:subfield code="a">HSD54</marc:subfield><marc:subfield code="b">HFHB</marc:subfield><marc:subfield code="c">Interkulturelle Bibliothek</marc:subfield><marc:subfield code="d">803</marc:subfield><marc:subfield code="e">unavailable</marc:subfield><marc:subfield code="f">1</marc:subfield><marc:subfield code="g">1</marc:subfield><marc:subfield code="h">N</marc:subfield><marc:subfield code="i">unknown</marc:subfield><marc:subfield code="j">IB</marc:subfield></marc:datafield>
                </marc:record></metadata>
                </record>
        """


    def getNotWellFormedRecord(self):
        return """
                record>
                <header>
                <identifier>oai:HSG_Libraries:HSB02-000173039</identifier>
                <datestamp>2013-04-24T16:39:10Z</datestamp>
                <setSpec>SWISSBIB-FULL-HSB02</setSpec>
                </header>
                <metadata>
                <marc:record xmlns:marc="http://www.loc.gov/MARC21/slim" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
                <marc:leader>     nam  22     7u 4500</marc:leader>
                <marc:controlfield tag="FMT">BK</marc:controlfield>
                <marc:controlfield tag="LDR">     nam  22     7u 4500</marc:controlfield>
                <marc:controlfield tag="001">000173039</marc:controlfield>
                <marc:controlfield tag="008">040929s2005                  00    ger d</marc:controlfield>
                <marc:datafield tag="020" ind1=" " ind2=" "><marc:subfield code="a">3-468-20409-4</marc:subfield></marc:datafield>
                <marc:datafield tag="040" ind1=" " ind2=" "><marc:subfield code="a">HPHS</marc:subfield><marc:subfield code="d">HFHB</marc:subfield></marc:datafield>
                <marc:datafield tag="100" ind1=" " ind2=" "><marc:subfield code="a">Worsch, Wolfgang</marc:subfield></marc:datafield>
                <marc:datafield tag="245" ind1=" " ind2=" "><marc:subfield code="a">Grundschulwörterbuch Deutsch</marc:subfield><marc:subfield code="c">Projektl.: Wolfgang Worsch</marc:subfield></marc:datafield>
                <marc:datafield tag="260" ind1=" " ind2=" "><marc:subfield code="a">Berlin &lt;etc.&gt;</marc:subfield><marc:subfield code="b">Langenscheidt</marc:subfield><marc:subfield code="c">2005</marc:subfield></marc:datafield>
                <marc:datafield tag="300" ind1=" " ind2=" "><marc:subfield code="a">192 S.</marc:subfield><marc:subfield code="b">Ill.</marc:subfield></marc:datafield>
                <marc:datafield tag="490" ind1=" " ind2=" "><marc:subfield code="a">Kids</marc:subfield></marc:datafield>
                <marc:datafield tag="690" ind1="H" ind2="P"><marc:subfield code="8">803(03)</marc:subfield><marc:subfield code="a">Deutsch: Wörterbücher</marc:subfield><marc:subfield code="2">PHS</marc:subfield></marc:datafield>
                <marc:datafield tag="650" ind1=" " ind2=" "><marc:subfield code="8">803</marc:subfield><marc:subfield code="a">Deutsch</marc:subfield></marc:datafield>
                <marc:datafield tag="655" ind1=" " ind2=" "><marc:subfield code="8">8(03)</marc:subfield><marc:subfield code="a">Wörterbuch</marc:subfield></marc:datafield>
                <marc:datafield tag="949" ind1=" " ind2=" "><marc:subfield code="b">HPHG</marc:subfield><marc:subfield code="c">MKV</marc:subfield><marc:subfield code="j">803(03)//038</marc:subfield><marc:subfield code="p">HR40005163</marc:subfield><marc:subfield code="q">000173039</marc:subfield><marc:subfield code="r">000010</marc:subfield><marc:subfield code="0">PHSG/RDZ Gossau</marc:subfield><marc:subfield code="1">Migration und Kulturelle Vielfalt</marc:subfield><marc:subfield code="3">LM</marc:subfield><marc:subfield code="4">01</marc:subfield><marc:subfield code="6"></marc:subfield></marc:datafield>
                <marc:datafield tag="AVA" ind1=" " ind2=" "><marc:subfield code="a">HSD52</marc:subfield><marc:subfield code="b">HPHG</marc:subfield><marc:subfield code="c">Migration und Kulturelle Vielfalt</marc:subfield><marc:subfield code="d">803(03)//038</marc:subfield><marc:subfield code="e">available</marc:subfield><marc:subfield code="f">1</marc:subfield><marc:subfield code="g">0</marc:subfield><marc:subfield code="h">N</marc:subfield><marc:subfield code="i">unknown</marc:subfield><marc:subfield code="j">MKV</marc:subfield></marc:datafield>
                <marc:datafield tag="AVA" ind1=" " ind2=" "><marc:subfield code="a">HSD54</marc:subfield><marc:subfield code="b">HFHB</marc:subfield><marc:subfield code="c">Interkulturelle Bibliothek</marc:subfield><marc:subfield code="d">803</marc:subfield><marc:subfield code="e">unavailable</marc:subfield><marc:subfield code="f">1</marc:subfield><marc:subfield code="g">1</marc:subfield><marc:subfield code="h">N</marc:subfield><marc:subfield code="i">unknown</marc:subfield><marc:subfield code="j">IB</marc:subfield></marc:datafield>
                </marc:record></metadata>
                </record>
        """