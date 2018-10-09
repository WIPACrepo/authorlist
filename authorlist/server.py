"""
Website core.

Define routes and start up the server.
"""
from __future__ import print_function

import os
import json
from collections import defaultdict
import itertools
from datetime import datetime

import unidecode
import tornado.web
import tornado.ioloop

from .state import State

#from .handlers import IceCubeHander, PINGUHander, Gen2Hander

def get_template_path():
    return os.path.join(os.path.dirname(__file__),'templates')

def get_static_path():
    return os.path.join(os.path.dirname(__file__),'static')

class WebServer:
    def __init__(self, json, port=8888, debug=True):
        self.port = port
        
        collabs = {
            'icecube': 'IceCube',
            'pingu': 'IceCube-PINGU',
            'icecube-gen2': 'IceCube-Gen2',
        }
        self.app = tornado.web.Application([
            (r'/', MainHandler, {'collabs': collabs}),
#            (r'/icecube', IceCubeHandler, {'state': State(json, collab='icecube')}),
#            (r'/pingu', PINGUHandler, {'state': State(json, collab='pingu')}),
#            (r'/icecube-gen2', Gen2Handler, {'state': State(json, collab='icecube-gen2')}),
        ], template_path=get_template_path(),
           template_whitespace='all' if debug else 'oneline',
           static_path=get_static_path(),
           debug=debug)

    def start(self):
        self.app.listen(self.port)
        tornado.ioloop.IOLoop.current().start()


class MainHandler(tornado.web.RequestHandler):
    def initialize(self, collabs):
        self.collabs = collabs

    def get(self):
        return self.render('main.html', collabs=self.collabs)
        


PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'

def today():
    return datetime.utcnow().date().isoformat()


class MainHandler2(tornado.web.RequestHandler):
    def initialize(self, authors, institutions, thanks, acknowledgements):
        self.authors = authors
        self.institutions = institutions
        self.thanks = thanks
        self.acknowledgements = acknowledgements

    def get(self):
        self.write("""
        <html>
            <head>
                <title>Authorlist</title>
            </head>
            <body>
                <h1>Authorlist form</h1>
                <form action="/" method="post">
                    <div>Collaboration:
                        <select name="collaboration">
                            <option value="IceCube">IceCube</option>
                            <option value="IceCube-Gen2">IceCube-Gen2</option>
                            <option value="PINGU">PINGU</option>
                        </select>
                    </div>
                    <div>Date: <input type="text" name="date" /></div>
                    <input type="submit" />
                </form>
            </body>
        </html>""")

    def post(self):
        collab = self.get_argument('collaboration', '')
        date = self.get_argument('date', '')
        if not date:
            date = today()

        authors = defaultdict(list)
        if (collab == 'IceCube-Gen2' and date != '' and date < GEN2_START_DATE or
            collab == 'PINGU' and date != '' and date < PINGU_START_DATE):
            pass
        else:
            collab_lower = collab.lower()
            for a in self.authors:
                if a['collab'] != collab_lower:
                    continue
                if date == '':
                    if a['to'] != '':
                        continue
                elif a['from'] > date or (a['to'] != '' and a['to'] < date):
                    continue
                authors[a['authname']].append(a)

        def ordering(name):
            parts = unidecode.unidecode(name).replace("'",'').split()
            ret = []
            for i,p in enumerate(reversed(parts)):
                if i == 0:
                    ret.append(p)
                elif p[-1] == '.':
                    ret += parts[:i+1]
                    break
                else:
                    ret[0] = p + ret[0]
            return [x.lower() for x in ret]
        sorted_authors = sorted(authors, key=ordering)

        instname = {}
        for a in itertools.chain(*authors.values()):
            if a['instname']:
                instname[a['instname']] = self.institutions[a['instname']]
        #def ordering_inst(name):
        #    return instname[name]['city']
        #sorted_inst = sorted(instname, key=ordering_inst)
        sorted_inst = sorted(instname)
        
        thanks = {}
        for a in itertools.chain(*authors.values()):
            if a['thanks']:
                thanks[a['thanks']] = self.thanks[a['thanks']]
        sorted_thanks = sorted(thanks)

        self.write("""
        <html>
            <head>
                <title>Authorlist</title>
            </head>
            <body>
                <h1>Authorlist form</h1>
                <form action="/" method="post">
                    <div>Collaboration:
                        <select name="collaboration">
                            <option value="IceCube" """+(' selected' if collab == 'IceCube' else '')+""">IceCube</option>
                            <option value="IceCube-Gen2" """+(' selected' if collab == 'IceCube-Gen2' else '')+""">IceCube-Gen2</option>
                            <option value="PINGU" """+(' selected' if collab == 'PINGU' else '')+""">PINGU</option>
                        </select>
                    </div>
                    <div>Date: <input type="text" name="date" value='"""+date+"""'/></div>
                    <input type="submit" />
                </form>
                <br><br>
                <h2>"""+collab+' - '+(date if date else 'Current')+'</h2><div>')
        comma = False
        for authname in sorted_authors:
            if comma:
                self.write(', ')
            self.write(authname)

            self.write('<sup>')
            comma2 = False
            for a in sorted(authors[authname], key=lambda a:sorted_inst.index(a['instname'])):
                if a['instname']:
                    if comma2:
                        self.write(',')
                    i = sorted_inst.index(a['instname'])
                    self.write('{}'.format(i+1))
                    comma2 = True
            for a in authors[authname]:
                if a['thanks']:
                    if comma2:
                        self.write(',')
                    i = sorted_thanks.index(a['thanks'])
                    self.write('{}'.format(chr(ord('a')+i)))
                    comma2 = True
            self.write('</sup>')
            comma = True
        self.write(' ({} authors)'.format(len(sorted_authors)))
        self.write('</div><div style="margin-top:2em">')
        for i,inst in enumerate(sorted_inst):
            self.write('<div>{}. '.format(i+1))
            self.write(instname[inst]['cite'])
            self.write('</div>')
        self.write('</div><div style="margin-top:2em">')
        for i,t in enumerate(sorted_thanks):
            self.write('<div>{}. '.format(chr(ord('a')+i)))
            self.write(thanks[t])
            self.write('</div>')
        self.write("""</div></body></html>""")
        
