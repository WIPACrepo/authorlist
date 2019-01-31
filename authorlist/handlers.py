"""
Handlers for different collaborations.
"""
from __future__ import print_function

import os
from collections import defaultdict
from datetime import datetime
import codecs

import unidecode
import latexcodec
from pylatexenc.latexencode import utf8tolatex
import tornado.web

ICECUBE_START_DATE = '2003-01-01'
PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'

def today():
    return datetime.utcnow().date().isoformat()

def validate_date(d):
    if not d:
        return None
    try:
        datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return None
    return d

def author_ordering(a):
    """sort authors using English unicode sorting rules"""
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

        authors = sorted(authors, key=author_ordering)

        # sort institutions
        def ordering_inst(name):
            sort_name = name
            if insts[name]['city']:
                sort_name = insts[name]['city']
            parts = unidecode.unidecode(sort_name).replace("'",'').split()
            ret = []
            for i,p in enumerate(reversed(parts)):
                if i == 0:
                    ret.append(p)
                elif p[-1] == '.':
                    ret += parts[:i+1]
                    break
                else:
                    ret[0] = p + ret[0]
            if insts[name]['city']:
                ret.append(insts[name]['cite'])
            return [x.lower() for x in ret]
        sorted_insts = sorted(insts, key=ordering_inst)

        # sort thanks
        sorted_thanks = list(thanks) #sorted(thanks)

        # format the authorlist
        raw = self.get_argument('raw', default=None)
        formatting = self.get_argument('formatting','web') if raw is None else 'web'
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
                'web-institution': 'web by institution',
                'arxiv': 'arXiv',
                'epjc': 'European Physical Journal C. (EPJC)',
                'revtex4': 'Physical Review Letters (RevTex4)',
                'aastex': 'Astrophysical Journal (AASTeX)',
                'aa': 'Journal Astronomy & Astrophysics (A & A)',
                'elsevier': 'Astroparticle Physics (Elsevier)',
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
        elif formatting == 'web-institution':
            authors_by_inst = defaultdict(list)
            for author in authors:
                for instname in author['instnames']:
                    authors_by_inst[instname].append(author['authname'])
            kwargs.update({
                'authors_by_inst': authors_by_inst,
                'insts': insts,
                'sorted_insts': sorted_insts,
            })
        elif formatting == 'arxiv':
            kwargs['format_text'] = utf8tolatex(authors_text)
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
                text += utf8tolatex(author['authname'])
                source = []
                if 'instnames' in author and author['instnames']:
                    source.extend(author['instnames'])
                if 'thanks' in author and author['thanks']:
                    source.extend(chr(ord('a') + sorted_thanks.index(t)) for t in author['thanks'])
                if source:
                    text += '\\thanksref{' + utf8tolatex(','.join(source)) + '}'
                text += '\n'
            text += '}\n\\authorrunning{IceCube Collaboration}\n'
            for i,name in enumerate(sorted_thanks):
                text += '\\thankstext{' + chr(ord('a') + i) + '}{'
                text += utf8tolatex(thanks[name]) + '}\n'
            if sorted_insts:
                text += '\\institute{'
                first = True
                for name in sorted_insts:
                    if first:
                        first = False
                    else:
                        text += '\\and '
                    text += utf8tolatex(insts[name]['cite'])
                    text += ' \\label{' + name + '}\n'
                text += '}\n'
            text += """\\date{Received: date / Accepted: date}
\\maketitle
\\twocolumn
\\begin{acknowledgements}
"""
            text += '\n'.join(utf8tolatex(a) for a in acks[1:])
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
                text += utf8tolatex(insts[name]['cite'])
                text += '}\n'
            text += '\n'
            for author in authors:
                text += '\\author{'
                text += utf8tolatex(author['authname'])
                text += '}\n'
                if 'instnames' in author:
                    for name in author['instnames']:
                        text += '\\affiliation{'
                        text += utf8tolatex(insts[name]['cite'])
                        text += '}\n'
                if 'thanks' in author:
                    for name in author['thanks']:
                        text += '\\thanks{'
                        text += utf8tolatex(thanks[name])
                        text += '}\n'
            text += """\\date{\\today}

\\collaboration{IceCube Collaboration}
\\noaffiliation

\\maketitle

\\begin{acknowledgements}
"""
            text += '\n'.join(utf8tolatex(a) for a in acks[1:])
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
            text += utf8tolatex(authors[0]['authname'])
            text += """ et al.}
\\begin{document}

\\title{IceCube Author List for AAS{\TeX} """
            text += date.replace('-','') + '}\n\n'
            text += '\\author{\nIceCube Collaboration\n'
            for author in authors:
                text += utf8tolatex(author['authname'])
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
                text += utf8tolatex(insts[name]['cite'])
                text += ' }\n'
            for i,name in enumerate(sorted_thanks):
                text += '\\altaffiltext{'+str(1+len(sorted_insts)+i)+'}{'
                text += utf8tolatex(thanks[name]) + '}\n'
            text += """
\\acknowledgements

"""
            text += '\n'.join(utf8tolatex(a) for a in acks[1:])
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
                text += utf8tolatex(author['authname'])
                source = []
                if 'instnames' in author and author['instnames']:
                    source.extend(author['instnames'])
                if 'thanks' in author and author['thanks']:
                    source.extend(chr(ord('a') + sorted_thanks.index(t)) for t in author['thanks'])
                if source:
                    text += '\\inst{' + ','.join('\\ref{'+utf8tolatex(s)+'}' for s in source) + '}'
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
                    text += utf8tolatex(insts[name]['cite'])
                    text += ' \\label{' + name + '} \n'
                for i,name in enumerate(sorted_thanks):
                    if first:
                        first = False
                    else:
                        text += '\\and '
                    text += utf8tolatex(thanks[name])
                    text += '\\label{' + chr(ord('a') + i) + '} \n'
                text += '}\n'
            text += """\\abstract { } { } { } { } { }
\\keywords{keword 1 -- keyword 2 -- keyword 3}
\\maketitle
\\begin{acknowledgements}
"""
            text += '\n'.join(utf8tolatex(a) for a in acks[1:])
            text += """
\\end{acknowledgements}
\\end{document}"""
            kwargs['format_text'] = text
            kwargs['intro_text'] = """For the Journal Astronomy & Astrophysics.
                You will need <a href="http://ftp.edpsciences.org/pub/aa/aa.cls">aa.cls</a>
                but also consult the journal pages for more author instructions.
                """
        elif formatting == 'elsevier':
            text = """\\documentclass[preprint,12pt]{elsarticle}
\\journal{Astroparticle Physics}
\\begin{document}
\\begin{frontmatter}
\\title{IceCube Author List for Elsevier """
            text += date.replace('-','') + '}\n\n'
            text += '\n'
            for author in authors:
                text += '\\author'
                if 'instnames' in author:
                    text += '['+(','.join(author['instnames']))+']'
                text += '{'
                text += utf8tolatex(author['authname'])
                if 'thanks' in author:
                    text += '\\fnref{'
                    text += ','.join(author['thanks'])
                    text += '}'
                text += '}\n'
            for name in sorted_insts:
                text += '\\address['+name+']{'
                text += utf8tolatex(insts[name]['cite'])
                text += '}\n'
            for name in thanks:
                text += '\\fntext['+name+']{'
                text += utf8tolatex(thanks[name])
                text += '}\n'
            text += """\\end{frontmatter}

\\section*{acknowledgements}
"""
            text += '\n'.join(utf8tolatex(a) for a in acks[1:])
            text += """
\\end{document}"""
            kwargs['format_text'] = text
            kwargs['intro_text'] = """This style e.g. for Astroparticle Physics, or other Elsevier journals.
                You will need elsarticle from the
                <a href="http://www.ctan.org/tex-archive/macros/latex/contrib/elsarticle">CTAN library</a>.
                """

        if raw:
            kwargs['formatting_options'] = {'web': 'web'}
            return self.render('collab_raw.html', **kwargs)
        else:
            return self.render('collab.html', **kwargs)


class IceCubeHandler(CollabHandler):
    def initialize(self, *args, **kwargs):
        kwargs['collab'] = 'IceCube'
        super(IceCubeHandler, self).initialize(*args, **kwargs)

    def post(self):
        date = validate_date(self.get_argument('date', default=''))
        if (not date) or date > today():
            date = today()
        elif date < ICECUBE_START_DATE:
            date = ICECUBE_START_DATE
        return self.common(date)

class PINGUHandler(CollabHandler):
    def initialize(self, *args, **kwargs):
        kwargs['collab'] = 'IceCube-PINGU'
        super(PINGUHandler, self).initialize(*args, **kwargs)

    def post(self):
        date = validate_date(self.get_argument('date', default=''))
        if (not date) or date > today():
            date = today()
        elif date < PINGU_START_DATE:
            date = PINGU_START_DATE
        return self.common(date)

class Gen2Handler(CollabHandler):
    def initialize(self, *args, **kwargs):
        kwargs['collab'] = 'IceCube-Gen2'
        super(Gen2Handler, self).initialize(*args, **kwargs)

    def post(self):
        date = validate_date(self.get_argument('date', default=''))
        if (not date) or date > today():
            date = today()
        elif date < GEN2_START_DATE:
            date = GEN2_START_DATE
        return self.common(date)
