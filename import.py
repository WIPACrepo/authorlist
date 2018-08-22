"""
Import the authorlist from a text file.
"""
from __future__ import print_function

import csv
import json
from pprint import pprint
try:
    import html.unescape as unescape
except ImportError:
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape

import latexcodec

def parse_date(d):
    if d.startswith('9999'):
        return ''
    return d[0:4]+'-'+d[4:6]+'-'+d[6:]

def replace_tex(line):
    line = line.decode('latex')
    if '&' in line:
        line = unescape(line)
    return line

PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'
def parse_name(name, author):
    if name.startswith('%P+'):
        if (not author['to']) or author['to'] >= GEN2_START_DATE:
            return name[3:],['Icecube-Gen2','PINGU']
        else:
            return name[3:],['PINGU']
    elif name.startswith('%G-'):
        if (not author['to']) or author['to'] >= PINGU_START_DATE:
            return name[3:],['Icecube','PINGU']
        else:
            return name[3:],['IceCube']
    elif name.startswith('%G+'):
        return name[3:],['IceCube-Gen2']
    elif name.startswith('%P-'):
        return name[3:],['IceCube']
    else:
        if (not author['to']) or author['to'] >= GEN2_START_DATE:
            return name,['IceCube','IceCube-Gen2','PINGU']
        elif author['to'] >= PINGU_START_DATE and author['to'] < GEN2_START_DATE:
            return name,['Icecube','PINGU']
        else:
            return name,['IceCube']

def author_reader(filename):
    authors = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                parts = [x for x in line.split(':') if x]
                author = {
                    'authname': '',
                    'instname': '',
                    'collab': '',
                    'from': '',
                    'to': '',
                    'thanks': '',
                }
                labs = []
                for p in parts[1:]:
                    name,value = p.split(' ',1)
                    value = replace_tex(value)
                    if name.startswith('lab'):
                        labs.append(value)
                    elif name == 'thanks':
                        author['thanks'] = value.lower()
                    elif name == 'from':
                        author['from'] = parse_date(value)
                    elif name == 'to':
                        author['to'] = parse_date(value)
                    elif name == 'web':
                        pass
                    else:
                        print(name,value)
                        raise Exception('unknown author type')
                name,collabs = parse_name(parts[0], author)
                author['authname'] = replace_tex(name).replace('{','').replace('}','')
                for l in labs:
                    for c in collabs:
                        a = dict(author)
                        a['collab'] = c.lower()
                        a['instname'] = l.lower()
                        authors.append(a)
    for a in authors:
        if a['collab'] == 'pingu' and a['from'] < PINGU_START_DATE:
            a['from'] = PINGU_START_DATE
        elif a['collab'] == 'icecube-gen2' and a['from'] < GEN2_START_DATE:
            a['from'] = GEN2_START_DATE
    return authors

def labs_reader(filename):
    labs = {}
    with open(filename) as f:
        reader = csv.DictReader(f)
        for row in reader:
            labs[row['institution_shortname'].lower()] = {
                'instname': row['institution_shortname'],
                'name': row['institution_name'],
                'dept': row['institution_dept'],
                'city': row['institution_city_or_municipal'],
                'cite': row['old_string'],
            }
    return labs

def thanks_reader(filename):
    thanks = {}
    with open(filename) as f:
        for line in f:
            if line.startswith('Thanks'):
                line = line[7:]
            line = line.strip()
            if ':' in line:
                parts = line.split(':',1)
                thanks[parts[0].lower()] = replace_tex(parts[1]).strip()
    return thanks

def check(authors, institutions):
    for a in authors:
        if a['instname'] not in institutions:
            print(a['authname'],a['instname'])
            raise Exception('bad instname')

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist importer')
    parser.add_argument('--json',help='output as json to the file specified')
    parser.add_argument('--authors',help='input text file with old authorlist format')
    parser.add_argument('--labs',help='input text file with labs in csv format')
    parser.add_argument('--thanks',help='input text file with old footnote/thanks format')
    args = parser.parse_args()

    authors = author_reader(args.authors)
    institutions = labs_reader(args.labs)
    thanks = thanks_reader(args.thanks)

    check(authors, institutions)

    output = {
        'authors': authors,
        'institutions': institutions,
        'thanks': thanks,
    }

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(output, f)
    else:
        pprint(output)


if __name__ == '__main__':
    main()
