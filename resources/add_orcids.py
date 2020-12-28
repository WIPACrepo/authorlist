import os
import sys
import csv
import argparse
import json

def read_csv(filename):
    ret = {}
    with open(filename) as f:
        csvreader = csv.reader(f)
        next(csvreader) # read header
        for row in csvreader:
            ret[row[0]] = row[1].rsplit('/',1)[-1]
    return ret

def read_authors(filename):
    with open(filename) as f:
        return json.load(f)

def write_authors(filename, authors):
    with open(filename, 'w') as f:
        json.dump(authors, f, indent=2)

def add_orcids(authors, orcids):
    for a in authors:
        if a['to'] == '' and a['authname'] in orcids: # for current authors with orcids
            a['orcid'] = orcids[a['authname']]
        else:
            a['orcid'] = ''
    return authors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('orcid', help='orcid csv filename')
    parser.add_argument('input', help='json input filename')
    parser.add_argument('output', help='json output filename')
    args = parser.parse_args()

    orcids = read_csv(args.orcid)
    data = read_authors(args.input)
    data['authors'] = add_orcids(data['authors'], orcids)
    write_authors(args.output, data)

if __name__ == '__main__':
    main()
