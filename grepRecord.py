
from argparse import ArgumentParser
import re
import sys

__author__ = 'swissbib'


oParser = ArgumentParser()
oParser.add_argument("-s", "--search", dest="toSearch")
oParser.add_argument("-f", "--file", dest="inputfile")
args = oParser.parse_args()


#pattern = ['<record><header>.*?','tag="001">',args.toSearch,'.*?</metadata></record>']
#sPattern = "".join(pattern)

#pattern = ['<record>.*?',args.toSearch,'.*?</metadata></record>']
#sPattern = "".join(pattern)



#cp = re.compile(sPattern,re.UNICODE | re.DOTALL | re.IGNORECASE)


infile = open(args.inputfile,"r")
content = infile.read()
allRecordsP = re.compile('<record>.*?</record>',re.UNICODE | re.DOTALL | re.IGNORECASE)
#allRecordsP = re.compile(sPattern,re.UNICODE | re.DOTALL | re.IGNORECASE)
iterator = allRecordsP.finditer(content)

searchStringP = re.compile(args.toSearch)


#record = cp.search(content)
#if record:
#    sys.stdout.write (record.group())

for match in iterator:
    rS = searchStringP.search(match.group())
    if rS:

        sys.stdout.write (match.group())













