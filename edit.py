"""
Edit the authorlist json file.
"""
from __future__ import print_function

import json
import io
from pprint import pprint
import readline
from datetime import datetime

from authorlist import collabs
from authorlist.handlers import author_ordering

def parse_date(d):
    if d.startswith('9999'):
        return ''
    return d[0:4]+'-'+d[4:6]+'-'+d[6:]

def filt(data, author, inst, collab):
    """Generator for filtering authors"""
    if author:
        author = author.lower()
    if inst:
        inst = inst.lower()
    if collab:
        collab = collab.lower()
    for a in data['authors']:
        if (((not author) or author in a['authname'].lower())
            and ((not inst) or any(inst in i.lower() for i in a['instnames'])
                 or any(inst in data['institutions'][i]['cite'].lower() for i in a['instnames']))
            and ((not collab) or collab == a['collab'])):
            yield (True, a)
        else:
            yield (False, a)

def check(data):
    for a in data['authors']:
        if 'instnames' in a:
            for inst in a['instnames']:
                if inst not in data['institutions']:
                    print(a['authname'],inst)
                    raise Exception('bad instname')
        if 'thanks' in a:
            for t in a['thanks']:
                if t not in data['thanks']:
                    print(a['authname'],t)
                    raise Exception('bad thanks')
        if 'instnames' not in a and 'thanks' not in a:
            print(a['authname'])
            raise Exception('no instname or thanks')

def save(args, data):
    check(data)
    data['authors'].sort(key=author_ordering)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f)
    else:
        pprint(data)

def input_select(prompt, values):
    """Allow only certain values for input"""
    if isinstance(values, (list,tuple)):
        values = {v:v for v in values}
    options = list(values)
    width = len(str(len(values)))
    template = '   [{:0>'+str(width)+'}] {:<20} {}'
    while True:
        print(prompt, '- choose one:')
        for i,k in enumerate(options):
            print(template.format(i, k, values[k]))
        choice = input('Choice: ')
        try:
            return options[int(choice)]
        except Exception:
            print('Invalid choice')

def input_date(prompt, notbefore='0001-01-01', infinite=False):
    """Read in a valid date"""
    notbefore = datetime.strptime(notbefore, '%Y-%m-%d')
    while True:
        dstr = input(prompt)
        if not dstr and infinite:
            return ''
        try:
            d = datetime.strptime(dstr, '%Y-%m-%d')
            if d <= notbefore:
                raise Exception()
        except Exception:
            print('invalid date')
            continue
        return dstr

def list_current(args, data):
    authors = []
    for t,a in filt(data, args.author, args.inst, args.collab):
        if t:
            authors.append(a)
    pprint(authors)

def add(args, data):
    print('Add new author')
    author = {}
    author['authname'] = input('Name: ')
    author['collab'] = input_select('Collaboration', values=collabs)

    author['from'] = input_date('From: ')
    author['to'] = input_date('To: ', notbefore=author['from'], infinite=True)

    insts = {inst:data['institutions'][inst]['cite'] for inst in data['institutions']
             if author['collab'] in data['institutions'][inst]['collabs']}
    instnames = []
    while True:
        ret = input('Select institution? (Y/N): ').lower()
        if ret.startswith('n'):
            break
        elif ret.startswith('y'):
            inst = input_select('Institution', values=insts)
            instnames.append(inst)
    if instnames:
        author['instnames'] = instnames

    thanks_names = []
    while True:
        ret = input('Select thanks? (Y/N): ').lower()
        if ret.startswith('n'):
            break
        elif ret.startswith('y'):
            thank = input_select('Thanks', data['thanks'])
            thanks_names.append(thank)
    if thanks_names:
        author['thanks'] = thanks_names

    data['authors'].append(author)

    save(args, data)

def edit(args, data):
    authors = []
    for t,author in filt(data, args.author, args.inst, args.collab):
        if t:
            print('')
            pprint(author)
            do_edit = False
            do_delete = False
            while True:
                ret = input('Edit author (Y/N/D): ').lower()
                if not ret or ret.startswith('n'):
                    break
                elif ret.startswith('y'):
                    do_edit = True
                    break
                elif ret.startswith('d'):
                    ret = input('Confirm delete author (Y/N): ').lower()
                    if ret.startswith('n'):
                        break
                    elif ret.startswith('y'):
                        do_delete = True
                        break
            if do_delete:
                continue # skip append
            if do_edit:
                while True:
                    print('')
                    print('From: ',author['from'])
                    ret = input('Edit from date (Y/N): ').lower()
                    if ret.startswith('n'):
                        break
                    elif ret.startswith('y'):
                        author['from'] = input_date('From: ')
                        break
                while True:
                    print('')
                    print('To: ',author['to'])
                    ret = input('Edit to date (Y/N): ').lower()
                    if ret.startswith('n'):
                        break
                    elif ret.startswith('y'):
                        author['to'] = input_date('To: ', notbefore=author['from'], infinite=True)
                        break

        authors.append(author)
    data['authors'] = authors

    save(args, data)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist editor')

    subparsers = parser.add_subparsers(help='sub-command help')
    parser_list = subparsers.add_parser('list', help='list current authorlist')
    parser_list.add_argument('-i','--input',help='input json file')
    parser_list.add_argument('--author', help='author name to filter by')
    parser_list.add_argument('--inst', help='institution name to filter by')
    parser_list.add_argument('--collab', help='collaboration name to filter by')
    parser_list.set_defaults(func=list_current)

    parser_add = subparsers.add_parser('add', help='add an author')
    parser_add.add_argument('-i','--input',help='input json file')
    parser_add.add_argument('-o','--output',help='output json file')
    parser_add.set_defaults(func=add)

    parser_edit = subparsers.add_parser('edit', help='edit an author')
    parser_edit.set_defaults(func=edit)
    parser_edit.add_argument('-i','--input',help='input json file')
    parser_edit.add_argument('-o','--output',help='output json file')
    parser_edit.add_argument('--author', help='author name to filter by')
    parser_edit.add_argument('--inst', help='institution name to filter by')
    parser_edit.add_argument('--collab', help='collaboration name to filter by')

    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)
    data['authors'].sort(key=author_ordering)

    args.func(args, data)


if __name__ == '__main__':
    main()
