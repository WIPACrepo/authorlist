"""
Authorlist website
"""
from __future__ import print_function

import json
from collections import defaultdict
import itertools
from datetime import datetime

import unidecode
import tornado.web
import tornado.ioloop


PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'

def today():
    return datetime.utcnow().date().isoformat()

def website(authors, institutions, thanks, acknowledgements, port=8888):
    args = {
        'authors': authors,
        'institutions': institutions,
        'thanks': thanks,
        'acknowledgements': acknowledgements,
    }
    app = tornado.web.Application([
        (r'/', MainHandler, args),
    ], debug=True)
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()

class MainHandler(tornado.web.RequestHandler):
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
        

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist website')
    parser.add_argument('json',help='authorlist json file')
    parser.add_argument('-p','--port',type=int,default=8888,help='port to listen on')
    args = parser.parse_args()

    with open(args.json) as f:
        data = json.load(f)

    website(port=args.port, **data)


if __name__ == '__main__':
    main()
