"""
Dirty compare script to fire up server and compare dates with the original list at
http://staff.fysik.su.se/~walck/icecube/authors/IsKub.php
"""

import sys
import difflib
import requests

import latexcodec

try:
    from html import unescape as unescape
except ImportError:
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape

def get_orig(date):
    url = 'http://staff.fysik.su.se/~walck/icecube/authors/IsKub.php'
    date = date.replace('-','')
    r = requests.post(url, data={'p':date}, auth=('icecube','skua'))
    start = r.text.find('Collaboration:')
    end = r.text.find('authors)')
    if start == -1 or end == -1:
        print(r.text)
        raise Exception()
    text = r.text[start+14:end+9]
    try:
        text = text.encode('ascii')
    except Exception:
        pass
    return process(text.decode('latex'))

def get_mine(date):
    url = 'http://localhost:19372/'
    r = requests.post(url, data={'collaboration':'IceCube','date':date})
    start = r.text.find('</h2><div>')
    end = r.text.find('authors)')
    return process(r.text[start+10:end+9])

def process(input):
    ret = []
    for x in unescape(input).rsplit('(',1)[0].strip().split(', '):
        if '<SUP>' in x:
            x = x.split('<SUP>')[0]
        if '<sup>' in x:
            x = x.split('<sup>')[0]
        x = x.replace(u'\xa0', u' ').strip()
        if x:
            ret.append(x)
    return ret

date = '2016-08-10' if len(sys.argv) < 2 else sys.argv[1]

orig = get_orig(date)
mine = get_mine(date)

print('orig',len(orig))
print('mine',len(mine))

for line in difflib.context_diff(orig,mine):
    print(line)

print('in orig, not in mine:')
for name in orig:
    if name not in mine:
        print(name)

print('in mine, not in orig:')
for name in mine:
    if name not in orig:
        print(name)
