"""
Import the authorlist from Christian's php-like file.
"""
from __future__ import print_function

import json
import io
from pprint import pprint
try:
    from html import unescape as unescape
except ImportError:
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape

import latexcodec

def parse_date(d):
    if d.startswith('9999'):
        return ''
    return d[0:4]+'-'+d[4:6]+'-'+d[6:]

def replace_tex(line):
    try:
        line = line.encode('ascii')
    except Exception:
        pass
    line = line.decode('latex')
    if '&' in line:
        line = unescape(line)
    return line

PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'
def parse_name(name, author=None):
    if name.startswith('%P+'):
        if (not author) or (not author['to']) or author['to'] >= GEN2_START_DATE:
            return name[3:],['Icecube-Gen2','PINGU']
        else:
            return name[3:],['PINGU']
    elif name.startswith('%G-'):
        if (not author) or (not author['to']) or author['to'] >= PINGU_START_DATE:
            return name[3:],['Icecube','PINGU']
        else:
            return name[3:],['IceCube']
    elif name.startswith('%G+'):
        return name[3:],['IceCube-Gen2']
    elif name.startswith('%P-'):
        return name[3:],['IceCube']
    else:
        if (not author) or (not author['to']) or author['to'] >= GEN2_START_DATE:
            return name,['IceCube','IceCube-Gen2','PINGU']
        elif author['to'] >= PINGU_START_DATE and author['to'] < GEN2_START_DATE:
            return name,['Icecube','PINGU']
        else:
            return name,['IceCube']

def author_reader(input_lines):
    authors = []
    for line in input_lines:
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
            name = replace_tex(name).replace('{','').replace('}','')
            # TODO: fix Sarkar2 properly
            #while name[-1].isdigit():
            #    name = name[:-1]
            author['authname'] = name
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

def labs_reader(input_lines):
    labs = {}
    for line in input_lines:
        parts = line.split(':',1)
        name,collabs = parse_name(parts[0])
        if name.startswith('Lab '):
            name = name[4:]
        name = replace_tex(name).replace('{','').replace('}','')
        # TODO: fix BartolOld
        cite = replace_tex(parts[1].strip())
        cite = cite.replace('Dept.~','Dept. ')
        labs[name.lower()] = {
            'collabs': [c.lower() for c in collabs],
            'name': name,
            'cite': cite,
        }
    return labs

def thanks_reader(input_lines):
    thanks = {}
    for line in input_lines:
        if line.startswith('Thanks'):
            line = line[7:]
        line = line.strip()
        if ':' in line:
            parts = line.split(':',1)
            thanks[parts[0].lower()] = replace_tex(parts[1]).strip()
    return thanks

def ack_reader(input_lines):
    acks = []
    for line in input_lines:
        parts = line.split(':',3)
        assert(parts[0] == 'Ack')
        value = replace_tex(parts[3]).replace('{','').replace('}','')
        ack = {
            'from': parse_date(parts[1]),
            'to': parse_date(parts[2]),
            'value': value,
        }
        acks.append(ack)
    return acks

def check(authors, institutions):
    for a in authors:
        if a['instname'] not in institutions:
            print(a['authname'],a['instname'])
            raise Exception('bad instname')

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist importer')
    parser.add_argument('--json',help='output as json to the file specified')
    parser.add_argument('authors',help='input php-like file with old authorlist format')
    args = parser.parse_args()

    section_names = ['author', 'lab', 'thanks', 'ack']
    sections = {k:[] for k in section_names}
    section = None
    with open(args.authors) as f:
        for line in f:
            line = line.strip()
            if line == '%' or line.startswith('% '):
                print('comment:',line)
                continue
            name,collabs = parse_name(line.split(':',1)[0])
            if name.startswith('Lab'):
                section = 'lab'
            elif name.startswith('Thanks'):
                section = 'thanks'
            elif name.startswith('Ack'):
                section = 'ack'
            else:
                section = 'author'
            print('section',section,'line:',line)
            sections[section].append(line)

    authors = author_reader(sections['author'])
    institutions = labs_reader(sections['lab'])
    thanks = thanks_reader(sections['thanks'])
    acknowledgements = ack_reader(sections['ack'])

    # sanity check that authors and instutions match
    check(authors, institutions)

    output = {
        'authors': authors,
        'institutions': institutions,
        'thanks': thanks,
        'acknowledgements': acknowledgements,
    }

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(output, f)
    else:
        pprint(output)


if __name__ == '__main__':
    main()
