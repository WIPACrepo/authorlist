"""
Handlers for different collaborations.
"""
from __future__ import print_function

import os
from datetime import datetime
import codecs

import unidecode
import latexcodec
import tornado.web

PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'

def today():
    return datetime.utcnow().date().isoformat()

class CollabHandler(tornado.web.RequestHandler):
    def initialize(self, state, collab=None):
        self.state = state
        self.collab = collab

    def get(self):
        return self.common()

    def common(self, date=''):
        if not date:
            date = today()

        authors = self.state.authors(date)
        insts = self.state.institutions(date)
        thanks = self.state.thanks(date)
        acks = self.state.acknowledgements(date)

        # sort authors using English unicode sorting rules
        def ordering(a):
            name = a['authname']
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
        authors = sorted(authors, key=ordering)

        # sort institutions
        def ordering_inst(name):
            if insts[name]['city']:
                name = insts[name]['city']
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
        sorted_insts = sorted(insts, key=ordering_inst)

        # sort thanks
        sorted_thanks = sorted(thanks)

        # format the authorlist
        formatting = self.get_argument('formatting','web')
        authors_text = []
        for author in authors:
            element = author['authname']
            sup_inst = []
            sup_thanks = []
            if 'instnames' in author and author['instnames']:
                for inst in author['instnames']:
                    sup_inst.append(sorted_insts.index(inst)+1)
            if 'thanks' in author and author['thanks']:
                for t in author['thanks']:
                    sup_thanks.append(chr(ord('a') + sorted_thanks.index(t)))
            sup = ['{}'.format(s) for s in sorted(sup_inst)]+sorted(sup_thanks)
            if sup and formatting == 'web':
                element += '<sup>{}</sup>'.format(','.join(sup))
            authors_text.append(element)
        authors_text = ', '.join(authors_text)

        kwargs = {
            'title': self.collab,
            'date': date,
            'formatting': formatting,
            'formatting_options': {
                'web': 'web',
                'arxiv': 'arXiv',
                'epjc': 'European Physical Journal C. (EPJC)',
                'revtex4': 'Physical Review Letters (RevTex4)',
                'aastex': 'Astrophysical Journal (AASTeX)',
                'aa': 'Journal Astronomy & Astrophysics (A & A)',
            },
            'wrap': False,
            'intro_text':'',
        }
        if formatting == 'web':
            kwargs.update({
                'authors': authors_text,
                'insts': insts,
                'sorted_insts': sorted_insts,
                'thanks': thanks,
                'sorted_thanks': sorted_thanks,
                'acks': acks,
            })
        elif formatting == 'arxiv':
            kwargs['format_text'] = authors_text.encode('latex')
            kwargs['wrap'] = True
        elif formatting == 'epjc':
            text = """\\documentclass[twocolumn,epjc3]{svjour3}

\\journalname{Eur. Phys. J. C}

\\begin{document}

\\title{IceCube Author List for EPJC """
            text += date.replace('-','')
            text += """}
\\onecolumn
\\author{"""
            first = True
            for author in authors:
                if first:
                    first = False
                else:
                    text += '\\and '
                text += codecs.encode(author['authname'], 'ulatex')
                source = []
                if 'instnames' in author and author['instnames']:
                    source.extend(author['instnames'])
                if 'thanks' in author and author['thanks']:
                    source.extend(chr(ord('a') + sorted_thanks.index(t)) for t in author['thanks'])
                if source:
                    text += '\\thanksref{' + codecs.encode(','.join(source), 'ulatex') + '}'
                text += '\n'
            text += '}\n\\authorrunning{IceCube Collaboration}\n'
            for i,name in enumerate(sorted_thanks):
                text += '\\thankstext{' + chr(ord('a') + i) + '}{'
                text += codecs.encode(thanks[name], 'ulatex') + '}\n'
            if sorted_insts:
                text += '\\institute{'
                first = True
                for name in sorted_insts:
                    if first:
                        first = False
                    else:
                        text += '\\and '
                    text += codecs.encode(insts[name]['cite'], 'ulatex')
                    text += ' \\label{' + name + '}\n'
                text += '}\n'
            text += """\\date{Received: date / Accepted: date}
\\maketitle
\\twocolumn
\\begin{acknowledgements}
"""
            text += '\n'.join(codecs.encode(a, 'ulatex') for a in acks[1:])
            text += """
\\end{acknowledgements}

\\end{document}"""
            kwargs['format_text'] = text
            kwargs['intro_text'] = """This style for European Physical Journal C.
                You will need svjour3.cls etc from
                <a href="http://www.e-publications.org/springer/support/epjc/svjour3-epjc.zip">EPJC-pages</a>
                (zip file).
                """
        elif formatting == 'revtex4':
            text = """\\documentclass[aps,prl,superscriptaddress]{revtex4-1}

\\begin{document}

\\title{IceCube Author List for Rev{\TeX} """
            text += date.replace('-','') + '}\n\n'
            for name in sorted_insts:
                text += '\\affiliation{'
                text += codecs.encode(insts[name]['cite'], 'ulatex')
                text += '}\n'
            text += '\n'
            for author in authors:
                text += '\\author{'
                text += codecs.encode(author['authname'], 'ulatex')
                text += '}\n'
                if 'instnames' in author:
                    for name in author['instnames']:
                        text += '\\affiliation{'
                        text += codecs.encode(insts[name]['cite'], 'ulatex')
                        text += '}\n'
                if 'thanks' in author:
                    for name in author['thanks']:
                        text += '\\thanks{'
                        text += codecs.encode(thanks[name], 'ulatex')
                        text += '}\n'
            text += """\\date{\\today}

\\collaboration{IceCube Collaboration}
\\noaffiliation

\\maketitle

\\begin{acknowledgements}
"""
            text += '\n'.join(codecs.encode(a, 'ulatex') for a in acks[1:])
            text += """
\\end{acknowledgements}

\\end{document}"""
            kwargs['format_text'] = text
            kwargs['intro_text'] = """This style e.g. for Physical Review Letters.
                You will need revtex4.cls and revsymb.sty as well as possibly
                some *.rtx files from the
                <a href="http://www.ctan.org/tex-archive/macros/latex/contrib/revtex/">CTAN library</a>.
                """
        elif formatting == 'aastex':
            text = """\\documentclass[preprint2]{aastex}

\\shorttitle{IceCube Author List}
\\shortauthors{"""
            text += codecs.encode(authors[0]['authname'], 'ulatex')
            text += """ et al.}
\\begin{document}

\\title{IceCube Author List for AAS{\TeX} """
            text += date.replace('-','') + '}\n\n'
            text += '\\author{\nIceCube Collaboration\n'
            for author in authors:
                text += codecs.encode(author['authname'], 'ulatex')
                source = []
                if 'instnames' in author:
                    source.extend(str(1+sorted_insts.index(t)) for t in author['instnames'])
                if 'thanks' in author:
                    source.extend(str(1+len(sorted_insts)+sorted_thanks.index(t)) for t in author['thanks'])
                if source:
                    text += '\\altaffilmark{'+','.join(source)+'}'
                text += ',\n'
            text += '}\n'
            for i,name in enumerate(sorted_insts):
                text += '\\altaffiltext{'+str(1+i)+'}{'
                text += codecs.encode(insts[name]['cite'], 'ulatex')
                text += ' }\n'
            for i,name in enumerate(sorted_thanks):
                text += '\\altaffiltext{'+str(1+len(sorted_insts)+i)+'}{'
                text += codecs.encode(thanks[name], 'ulatex') + '}\n'
            text += """
\\acknowledgements

"""
            text += '\n'.join(codecs.encode(a, 'ulatex') for a in acks[1:])
            text += """

\\end{document}"""
            kwargs['format_text'] = text
            kwargs['intro_text'] = """This style e.g. for Astrophysical Journal.
                You will need aastex.cls from
                <a href="http://aas.org/aastex/aastex-downloads">AASTeX-pages</a>
                or from the <a href="http://www.ctan.org/tex-archive/macros/latex/contrib/aastex/">CTAN library</a>.
                The documentclass preprint2 do not cope with authors lists
                extending to the second page but you may use preprint for
                one-column format.
                """
        elif formatting == 'aa':
            text = """\\documentclass[longauth]{aa}
\\usepackage{txfonts}
\\begin{document}
\\title{IceCube Author List for A \& A """
            text += date.replace('-','')
            text += """}
\\author{
IceCube Collaboration:
"""
            first = True
            for author in authors:
                if first:
                    first = False
                else:
                    text += '\\and '
                text += codecs.encode(author['authname'], 'ulatex')
                source = []
                if 'instnames' in author and author['instnames']:
                    source.extend(author['instnames'])
                if 'thanks' in author and author['thanks']:
                    source.extend(chr(ord('a') + sorted_thanks.index(t)) for t in author['thanks'])
                if source:
                    text += '\\inst{' + ','.join('\\ref{'+codecs.encode(s, 'ulatex')+'}' for s in source) + '}'
                text += '\n'
            text += '}\n'
            if sorted_insts or sorted_thanks:
                text += '\\institute{'
                first = True
                for name in sorted_insts:
                    if first:
                        first = False
                    else:
                        text += '\\and '
                    text += codecs.encode(insts[name]['cite'], 'ulatex')
                    text += ' \\label{' + name + '} \n'
                for i,name in enumerate(sorted_thanks):
                    if first:
                        first = False
                    else:
                        text += '\\and '
                    text += codecs.encode(thanks[name], 'ulatex')
                    text += '\\label{' + chr(ord('a') + i) + '} \n'
                text += '}\n'
            text += """\\abstract { } { } { } { } { }
\\keywords{keword 1 -- keyword 2 -- keyword 3}
\\maketitle
\\begin{acknowledgements}
"""
            text += '\n'.join(codecs.encode(a, 'ulatex') for a in acks[1:])
            text += """
\\end{acknowledgements}
\\end{document}"""
            kwargs['format_text'] = text
            kwargs['intro_text'] = """For the Journal Astronomy & Astrophysics.
                You will need <a href="http://ftp.edpsciences.org/pub/aa/aa.cls">aa.cls</a>
                but also consult the journal pages for more author instructions.
                """

        return self.render('collab.html', **kwargs)


class IceCubeHandler(CollabHandler):
    def initialize(self, *args, **kwargs):
        kwargs['collab'] = 'IceCube'
        super(IceCubeHandler, self).initialize(*args, **kwargs)

    def post(self):
        date = self.get_argument('date', default='')
        if not date:
            date = today()
        return self.common(date)

class PINGUHandler(CollabHandler):
    def initialize(self, *args, **kwargs):
        kwargs['collab'] = 'IceCube-PINGU'
        super(PINGUHandler, self).initialize(*args, **kwargs)

    def post(self):
        date = self.get_argument('date', default='')
        if not date:
            date = today()
        elif date < PINGU_START_DATE:
            date = PINGU_START_DATE
        return self.common(date)

class Gen2Handler(CollabHandler):
    def initialize(self, *args, **kwargs):
        kwargs['collab'] = 'IceCube-Gen2'
        super(Gen2Handler, self).initialize(*args, **kwargs)

    def post(self):
        date = self.get_argument('date', default='')
        if not date:
            date = today()
        elif date < GEN2_START_DATE:
            date = GEN2_START_DATE
        return self.common(date)




###############################

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
        
