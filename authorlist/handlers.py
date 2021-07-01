"""
Handlers for different collaborations.
"""
from __future__ import print_function

import os
from collections import defaultdict
from datetime import datetime
import codecs
import csv
import re
from io import StringIO

import unidecode
import latexcodec
from pylatexenc.latexencode import UnicodeToLatexEncoder, UnicodeToLatexConversionRule, RULE_REGEX
import tornado.web
from tornado.escape import xhtml_escape

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

def filter_thanks(thanks):
    for phrase in ('also at', 'now at', 'also', 'on leave of absense from', 'affiliated with', 'present address'):
        if thanks.startswith(phrase):
            return (phrase, thanks[len(phrase)+1:])
    return ('', thanks)

class Latex:
    def __init__(self):
        conversion_rules = [
            # our custom rules
            UnicodeToLatexConversionRule(RULE_REGEX, [
                # double \\ needed, see UnicodeToLatexConversionRule
                ( re.compile(r'\u1ec5'), r'\\~{\\^{{e}}}' ),
            ]),
            # plus all the default rules
            'defaults'
        ]
        self.u = UnicodeToLatexEncoder(conversion_rules=conversion_rules,
                                       replacement_latex_protection='braces-almost-all')
    def encode(self, text):
        return self.u.unicode_to_latex(text)
utf8tolatex = Latex().encode


class AuthorListRenderer:
    FORMATTING = {
        'web': 'web',
        'web-institution': 'web by institution',
        'arxiv': 'arXiv',
        'epjc': 'European Physical Journal C. (EPJC)',
        'revtex4': 'Physical Review Letters (RevTex4)',
        'aastex': 'Astrophysical Journal (AASTeX)',
        'aascsv': 'Astrophysical Journal (csv)',
        'aa': 'Journal Astronomy & Astrophysics (A & A)',
        'elsevier': 'Astroparticle Physics (Elsevier)',
        'jhep': 'Journal of High Energy Physics (JHEP/JCAP)',
        'science': 'Science',
        'inspire': 'INSPIRE author.xml',
    }

    def __init__(self, state):
        self.state = state

    def render(self, collab, date, formatting):
        if collab not in ('IceCube', 'IceCube-PINGU', 'IceCube-Gen2'):
            raise tornado.web.HTTPError(400, reason='bad collaboration')
        if formatting not in self.FORMATTING:
            raise tornado.web.HTTPError(400, reason='bad formatting type')

        self.collab = collab
        self.date = date
        self.formatting = formatting
        self.authors = self.state.authors(date)
        self.insts = self.state.institutions(date)
        self.thanks = self.state.thanks(date)
        self.acks = self.state.acknowledgements(date)

        self.authors = sorted(self.authors, key=author_ordering)

        # sort institutions
        def ordering_inst(name):
            sort_name = name
            if self.insts[name]['city']:
                sort_name = self.insts[name]['city']
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
            if self.insts[name]['city']:
                ret.append(self.insts[name]['cite'])
            return [x.lower() for x in ret]
        self.sorted_insts = sorted(self.insts, key=ordering_inst)

        # sort thanks
        self.sorted_thanks = list(self.thanks) #sorted(thanks)


        kwargs = {
            'title': collab,
            'date': date,
            'formatting': formatting,
            'formatting_options': AuthorListRenderer.FORMATTING,
            'wrap': False,
            'intro_text':'',
        }
        kwargs.update(getattr(self, '_'+formatting.replace('-','_'))())
        return kwargs

    def _web(self):
        # format the authorlist
        authors_text = []
        for author in self.authors:
            element = author['authname']
            sup_inst = []
            sup_thanks = []
            if 'instnames' in author and author['instnames']:
                for inst in author['instnames']:
                    sup_inst.append(self.sorted_insts.index(inst)+1)
            if 'thanks' in author and author['thanks']:
                for t in author['thanks']:
                    sup_thanks.append(chr(ord('a') + self.sorted_thanks.index(t)))
            sup = ['{}'.format(s) for s in sorted(sup_inst)]+sorted(sup_thanks)
            if sup and self.formatting == 'web':
                element += '<sup>{}</sup>'.format(','.join(sup))
            authors_text.append(element)
        authors_text = ', '.join(authors_text)

        return {
            'authors': authors_text,
            'insts': self.insts,
            'sorted_insts': self.sorted_insts,
            'thanks': self.thanks,
            'sorted_thanks': self.sorted_thanks,
            'acks': self.acks,
        }

    def _web_institution(self):
        authors_by_inst = defaultdict(list)
        for author in self.authors:
            for instname in author['instnames']:
                text = author['authname']
                if 'orcid' in author and author['orcid']:
                    text += f'<a class="orcid" target="_blank" href="https://orcid.org/{author["orcid"]}"><img alt="ORCID logo" src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png" width="16" height="16" />https://orcid.org/{author["orcid"]}</a>'
                authors_by_inst[instname].append(text)
        return {
            'authors_by_inst': authors_by_inst,
            'insts': self.insts,
            'sorted_insts': self.sorted_insts,
        }

    def _arxiv(self):
        authors_text = []
        for author in self.authors:
            element = author['authname']
            sup_inst = []
            sup_thanks = []
            if 'instnames' in author and author['instnames']:
                for inst in author['instnames']:
                    sup_inst.append(self.sorted_insts.index(inst)+1)
            if 'thanks' in author and author['thanks']:
                for t in author['thanks']:
                    sup_thanks.append(chr(ord('a') + self.sorted_thanks.index(t)))
            sup = ['{}'.format(s) for s in sorted(sup_inst)]+sorted(sup_thanks)
            if sup and self.formatting == 'web':
                element += '<sup>{}</sup>'.format(','.join(sup))
            authors_text.append(element)
        authors_text = ', '.join(authors_text)

        return {
            'format_text': utf8tolatex(authors_text),
            'wrap': True,
        }

    def _epjc(self):
        text = """\\documentclass[twocolumn,epjc3]{svjour3}
\\usepackage[T5,T1]{fontenc}
\\journalname{Eur. Phys. J. C}

\\begin{document}

\\title{"""+self.collab+""" Author List for EPJC """
        text += self.date.replace('-','')
        text += """}
\\onecolumn
\\author{"""
        first = True
        for author in self.authors:
            if first:
                first = False
            else:
                text += '\\and '
            text += utf8tolatex(author['authname'])
            source = []
            if 'instnames' in author and author['instnames']:
                source.extend(sorted(author['instnames'], key=self.sorted_insts.index))
            if 'thanks' in author and author['thanks']:
                source.extend(chr(ord('a') + self.sorted_thanks.index(t)) for t in sorted(author['thanks'], key=self.sorted_thanks.index))
            if source:
                text += '\\thanksref{' + utf8tolatex(','.join(source)) + '}'
            text += '\n'
        text += '}\n\\authorrunning{'+self.collab+' Collaboration}\n'
        for i,name in enumerate(self.sorted_thanks):
            text += '\\thankstext{' + chr(ord('a') + i) + '}{'
            text += utf8tolatex(self.thanks[name]) + '}\n'
        if self.sorted_insts:
            text += '\\institute{'
            first = True
            for name in self.sorted_insts:
                if first:
                    first = False
                else:
                    text += '\\and '
                text += utf8tolatex(self.insts[name]['cite'])
                text += ' \\label{' + name + '}\n'
            text += '}\n'
        text += """\\date{Received: date / Accepted: date}
\\maketitle
\\twocolumn
\\begin{acknowledgements}
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks[1:])
        text += """
\\end{acknowledgements}

\\end{document}"""

        intro_text = """This style for European Physical Journal C.
You will need svjour3.cls etc from
<a href="http://www.e-publications.org/springer/support/epjc/svjour3-epjc.zip">EPJC-pages</a>
(zip file).
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _revtex4(self):
        text = """\\documentclass[aps,prl,superscriptaddress]{revtex4-1}
\\usepackage[T5,T1]{fontenc}
\\begin{document}

\\title{"""+self.collab+""" Author List for Rev{\TeX} """
        text += self.date.replace('-','') + '}\n\n'
        for name in self.sorted_insts:
            text += '\\affiliation{'
            text += utf8tolatex(self.insts[name]['cite'])
            text += '}\n'
        text += '\n'
        for author in self.authors:
            text += '\\author{'
            text += utf8tolatex(author['authname'])
            text += '}\n'
            if 'thanks' in author:
                for name in sorted(author['thanks'], key=self.sorted_thanks.index):
                    text += '\\thanks{'
                    text += utf8tolatex(self.thanks[name])
                    text += '}\n'
            if 'instnames' in author:
                for name in sorted(author['instnames'], key=self.sorted_insts.index):
                    text += '\\affiliation{'
                    text += utf8tolatex(self.insts[name]['cite'])
                    text += '}\n'
        text += """\\date{\\today}

\\collaboration{"""+self.collab+""" Collaboration}
\\noaffiliation

\\maketitle

\\begin{acknowledgements}
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks[1:])
        text += """
\\end{acknowledgements}

\\end{document}"""

        intro_text = """This style e.g. for Physical Review Letters.
You will need revtex4.cls and revsymb.sty as well as possibly
some *.rtx files from the
<a href="http://www.ctan.org/tex-archive/macros/latex/contrib/revtex/">CTAN library</a>.
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _aastex(self):
        ### New ApJ 6.3 formatting
        text = """\\documentclass[twocolumn]{aastex63}
\\usepackage[T5,T1]{fontenc}
\\begin{document}

\\title{"""+self.collab+""" Author List for AAS{\TeX} """
        text += self.date.replace('-','') + '}\n\n'
        for name in self.sorted_insts:
            text += '\\affiliation{'
            text += utf8tolatex(self.insts[name]['cite'])
            text += '}\n'
        text += '\n'
        for author in self.authors:
            text += '\\author'
            if 'orcid' in author and author['orcid']:
                text += f'[{author["orcid"]}]'
            text += '{'
            text += utf8tolatex(author['authname'])
            text += '}\n'
            if 'thanks' in author:
                for name in sorted(author['thanks'], key=self.sorted_thanks.index):
                    text += '\\altaffiliation{'
                    text += utf8tolatex(self.thanks[name])
                    text += '}\n'
            if 'instnames' in author:
                for name in sorted(author['instnames'], key=self.sorted_insts.index):
                    text += '\\affiliation{'
                    text += utf8tolatex(self.insts[name]['cite'])
                    text += '}\n'
            text += '\n'
        text += """\\date{\\today}

\\collaboration{"""+str(len(self.authors))+"}{"+self.collab+""" Collaboration}

\\begin{abstract}

Abstract goes here.

\\end{abstract}

\\section{Introduction}

Text body goes here.

\\section*{Acknowledgements}
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks[1:])
        text += """

\\end{document}"""

        intro_text = """This style e.g. for Astroparticle Journal.
You will need aastex63.cls and aasjournal.bst as well as possibly
some other files from the
<a href="https://2modf33kux3n19iucb17y5dj-wpengine.netdna-ssl.com/wp-content/uploads/2019/06/aastexv63.tar.gz">AASTeX tarball</a>.
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _aascsv(self):
        f = StringIO()
        writer = csv.writer(f, )
        writer.writerow([
            'Is Corresponding Author (enter Yes)', 'Author Order', 'Title', 'Given Name/First Name',
            'Middle Initial(s) or Name', 'Family Name/Surname', 'Email', 'Telephone',
            'Institution', 'Department', 'Address Line 1', 'Address Line 2', 'City',
            'State/Province', 'Zip/Postal Code', 'Country',
        ])
        writer.writerow([
            'Yes', '1', '', self.collab, '', 'Collaboration', 'analysis@icecube.wisc.edu',
            '', '', '', '', '', '', '', '', '',
        ])
        for i,author in enumerate(self.authors):
            inst = self.insts[author['instnames'][0]]
            parts = inst['cite'].split(',')
            if 'Karlsruhe' in parts[0]:
                instname = parts[0].strip()
            elif 'CTSPS' in parts[0]:
                instname = parts[1].strip()
            elif 'Dept' in parts[0] or 'department' in parts[0] or 'Département' in parts[0] or 'Institut' in parts[0] or 'School' in parts[0]:
                instname = parts[1].strip()
            else:
                instname = parts[0].strip()
            if 'Canada' in inst['cite']:
                country = 'Canada'
            else:
                country = parts[-1].strip()
            if 'first' in author:
                first = author['first']
            else:
                first = author['authname'].rsplit('. ',1)[0]+'.'
            if 'last' in author:
                last = author['last']
            else:
                last = author['authname'].rsplit('. ', 1)[-1]
            email = author['email'] if 'email' in author else ''
            row = ['No', str(i+2), '', first, '', last, email, '',
                instname, '', '', '', inst['city'], '', '', country]
            writer.writerow(row)
        text = f.getvalue()
        f.close()

        intro_text = """This style e.g. for Astrophysical Journal author list submission. The csv should be converted to xls by the user, if required."""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _aa(self):
        text = """\\documentclass[longauth]{aa}
\\usepackage{txfonts}
\\usepackage[T5,T1]{fontenc}
\\begin{document}
\\title{"""+self.collab+""" Author List for A \& A """
        text += self.date.replace('-','')
        text += """}
\\author{
"""+self.collab+""" Collaboration:
"""
        first = True
        for author in self.authors:
            if first:
                first = False
            else:
                text += '\\and '
            text += utf8tolatex(author['authname'])
            source = []
            if 'instnames' in author and author['instnames']:
                source.extend(sorted(author['instnames'], key=self.sorted_insts.index))
            if 'thanks' in author and author['thanks']:
                source.extend(chr(ord('a') + self.sorted_thanks.index(t)) for t in sorted(author['thanks'], key=self.sorted_thanks.index))
            if source:
                text += '\\inst{' + ','.join('\\ref{'+utf8tolatex(s)+'}' for s in source) + '}'
            text += '\n'
        text += '}\n'
        if self.sorted_insts or self.sorted_thanks:
            text += '\\institute{'
            first = True
            for name in self.sorted_insts:
                if first:
                    first = False
                else:
                    text += '\\and '
                text += utf8tolatex(self.insts[name]['cite'])
                text += ' \\label{' + name + '} \n'
            for i,name in enumerate(self.sorted_thanks):
                if first:
                    first = False
                else:
                    text += '\\and '
                text += utf8tolatex(self.thanks[name])
                text += '\\label{' + chr(ord('a') + i) + '} \n'
            text += '}\n'
        text += """\\abstract { } { } { } { } { }
\\keywords{keword 1 -- keyword 2 -- keyword 3}
\\maketitle
\\begin{acknowledgements}
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks[1:])
        text += """
\\end{acknowledgements}
\\end{document}"""

        intro_text = """For the Journal Astronomy & Astrophysics.
You will need <a href="http://ftp.edpsciences.org/pub/aa/aa.cls">aa.cls</a>
but also consult the journal pages for more author instructions.
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _elsevier(self):
        text = """\\documentclass[preprint,12pt]{elsarticle}
\\usepackage[T5,T1]{fontenc}
\\journal{Astroparticle Physics}
\\begin{document}
\\begin{frontmatter}
\\title{"""+self.collab+""" Author List for Elsevier """
        text += self.date.replace('-','') + '}\n\n'
        text += '\n'
        for author in self.authors:
            text += '\\author'
            if 'instnames' in author:
                text += '['+(','.join(sorted(author['instnames'], key=self.sorted_insts.index)))+']'
            text += '{'
            text += utf8tolatex(author['authname'])
            if 'thanks' in author and author['thanks']:
                text += '\\fnref{'
                text += ','.join(sorted(author['thanks'], key=self.sorted_thanks.index))
                text += '}'
            text += '}\n'
        for name in self.sorted_insts:
            text += '\\address['+name+']{'
            text += utf8tolatex(self.insts[name]['cite'])
            text += '}\n'
        for name in self.thanks:
            text += '\\fntext['+name+']{'
            text += utf8tolatex(self.thanks[name])
            text += '}\n'
        text += """\\end{frontmatter}

\\section*{acknowledgements}
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks[1:])
        text += """
\\end{document}"""

        intro_text = """This style e.g. for Astroparticle Physics, or other Elsevier journals.
You will need elsarticle from the
<a href="http://www.ctan.org/tex-archive/macros/latex/contrib/elsarticle">CTAN library</a>.
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _jhep(self):
        text = """\\documentclass[preprint,12pt]{article}
\\usepackage{jheppub}
\\usepackage[T5,T1]{fontenc}
\\title{"""+self.collab+""" Author List for JHEP/JCAP """
        text += self.date.replace('-','') + '}\n\n'
        text += '\n'
        for i,author in enumerate(self.authors):
            text += '\\author'
            source = []
            if 'instnames' in author and author['instnames']:
                source.extend(str(self.sorted_insts.index(n)) for n in sorted(author['instnames'], key=self.sorted_insts.index))
            if 'thanks' in author and author['thanks']:
                source.extend(chr(ord('a') + self.sorted_thanks.index(t)) for t in sorted(author['thanks'], key=self.sorted_thanks.index))
            if source:
                text += '[' + ','.join(source) + ']'
            text += '{'
            if i+1 == len(self.authors):
                text += 'and '
            text += utf8tolatex(author['authname'])
            if i+1 < len(self.authors):
                text += ','
            text += '}\n'
        for name in self.sorted_insts:
            text += '\\affiliation['+str(self.sorted_insts.index(name))+']{'
            text += utf8tolatex(self.insts[name]['cite'])
            text += '}\n'
        for name in self.thanks:
            text += '\\affiliation['+chr(ord('a') + self.sorted_thanks.index(name))+']{'
            text += utf8tolatex(self.thanks[name])
            text += '}\n'
        text += """

\\begin{document}
\\maketitle
\\acknowledgments
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks[1:])
        text += """
\\end{document}"""

        intro_text = """This style e.g. for Journal of High Energy Physics, or Journal of Cosmology and Astroparticle Phsics.
You will need jheppub from
<a href="https://jhep.sissa.it/jhep/help/JHEP_TeXclass.jsp">here</a>.
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _science(self):
        text = """\\documentclass[12pt]{article}
\\usepackage{scicite}
\\usepackage{times}
\\usepackage[T5,T1]{fontenc}

\\topmargin 0.0cm
\\oddsidemargin 0.2cm
\\textwidth 16cm
\\textheight 21cm
\\footskip 1.0cm

\\newenvironment{sciabstract}{%
\\begin{quote} \\bf}
{\\end{quote}}

\\title{"""+self.collab+""" Author List for Science """
        text += self.date.replace('-','') + """}

\\author{IceCube Collaboration\\footnote{The full list of collaboration members and their affiliations is included in the supplementary material}
\\footnote{Correspondence to analysis@icecube.wisc.edu}\\\\
}
\\date{}
\\begin{document}
\\baselineskip15pt

\\maketitle

\\begin{sciabstract}

Your abstract goes here

\\end{sciabstract}


Your paper text goes here


\\begin{thebibliography}{10}

\\end{thebibliography}


\\subsection*{Supplementary Materials}
www.sciencemag.org\\\\
Materials and Methods\\\\

\\subsection*{Acknowledgments}

{\\bf Funding:}
"""
        text += '\n'.join(utf8tolatex(a) for a in self.acks)
        text += """\\\\

{\\bf Author contributions:}
The IceCube Collaboration designed, constructed and now operates the IceCube Neutrino Observatory. Data processing and calibration, Monte Carlo simulations of the detector and of theoretical models, and data analyses were performed by a large number of collaboration members, who also discussed and approved the scientific results presented here. The manuscript was reviewed by the entire collaboration before publication, and all authors approved the final version.\\\\

{\\bf Competing interests:} There are no competing interests to declare.\\\\

{\\bf Data and materials availability:}
Additional data and resources are available from the IceCube data archive at \\url{http://www.icecube.wisc.edu/science/data}. For each data sample these include the events, neutrino effective areas, background rates, and other supporting information in machine-readable formats.\\\\

\\pagebreak
\\pagebreak

\\begin{center}
\\Large{
Supplementary Materials for:\\\\
"""+self.collab+""" Author List for Science """
        text += self.date.replace('-','') + """
}
\\end{center}

\\subsection*{IceCube Collaboration$^{\\ast}$:}

"""
        for i,author in enumerate(self.authors):
            source = []
            if 'instnames' in author and author['instnames']:
                source.extend(str(1+self.sorted_insts.index(n)) for n in sorted(author['instnames'], key=self.sorted_insts.index))
            if 'thanks' in author and author['thanks']:
                source.extend(str(1+len(self.sorted_insts) + self.sorted_thanks.index(t)) for t in sorted(author['thanks'], key=self.sorted_thanks.index))
            text += utf8tolatex(author['authname'])
            if source:
                text += '$^{' + ',\: '.join(source) + '}$'
            if i+1 < len(self.authors):
                text += ','
            text += '\n'
        text += '\\\\\n\\\\\n'
        for name in self.sorted_insts:
            text += '$^{'+str(1+self.sorted_insts.index(name))+'}$ '
            text += utf8tolatex(self.insts[name]['cite'])
            text += ' \\\\\n'
        for name in self.thanks:
            text += '$^{'+str(1+len(self.sorted_insts) + self.sorted_thanks.index(name))+'}$ '
            text += utf8tolatex(filter_thanks(self.thanks[name])[1])
            text += ' \\\\\n'
        text += """\\\\
$^\\ast$E-mail: analysis@icecube.wisc.edu

\\section*{Materials and Methods}

\\end{document}"""

        intro_text = """This style for <i>Science</i>. You will need style and bib files from
<a href="https://www.sciencemag.org/authors/preparing-manuscripts-using-latex">here</a>.
"""

        return {
            'format_text': text,
            'intro_text': intro_text,
        }

    def _inspire(self):
        text = """<?xml version="1.0" encoding="UTF-8"?>

<!DOCTYPE collaborationauthorlist SYSTEM "http://inspirehep.net/info/HepNames/tools/authors_xml/author.dtd">
<!--
   """+self.collab+""" author list for INSPIRE.
-->
<collaborationauthorlist xmlns:foaf="http://xmlns.com/foaf/0.1/" \
xmlns:cal="http://inspirehep.net/info/HepNames/tools/authors_xml/">\n\n"""
        text += f'  <cal:creationDate>{self.date}</cal:creationDate>\n'
        text += '  <cal:publicationReference>XXXX-REPLACE-ME-XXXX</cal:publicationReference>\n\n'
        text += f"""  <cal:collaborations>
    <cal:collaboration id="c1">
      <foaf:name>{self.collab}</foaf:name>
    </cal:collaboration>
  </cal:collaborations>

  <cal:organizations>\n"""
        for i,name in enumerate(self.sorted_insts):
            text += '    <foaf:Organization id="a{}">\n'.format(1+i)
            text += '      <foaf:name>{}</foaf:name>\n'.format(xhtml_escape(self.insts[name]['cite']))
            text += '      <cal:orgStatus collaborationid="c1">member</cal:orgStatus>\n'
            text += '    </foaf:Organization>\n'
        for i,name in enumerate(self.thanks):
            text += '    <foaf:Organization id="a{}">\n'.format(1+i+len(self.sorted_insts))
            text += '      <foaf:name>{}</foaf:name>\n'.format(xhtml_escape(filter_thanks(self.thanks[name])[1]))
            text += '      <cal:orgStatus collaborationid="c1">nonmember</cal:orgStatus>\n'
            text += '    </foaf:Organization>\n'
        text += """  </cal:organizations>

  <cal:authors>\n"""
        for author in self.authors:
            if 'last' in author:
                last = author['last']
            else:
                last = author['authname'].rsplit('. ', 1)[-1]
            email = author['email'] if 'email' in author else ''

            text += '    <foaf:Person>\n'
            text += '      <cal:authorNameNative>{}</cal:authorNameNative>\n'.format(author['first']+' '+author['last'])
            if 'first' in author:
                text += '      <foaf:givenName>{}</foaf:givenName>\n'.format(unidecode.unidecode(author['first']))
            text += '      <foaf:familyName>{}</foaf:familyName>\n'.format(unidecode.unidecode(last))
            text += '      <cal:authorNamePaper>{}</cal:authorNamePaper>\n'.format(unidecode.unidecode(author['authname']))
            text += '      <cal:authorCollaboration collaborationid="c1" />\n'
            text += '      <cal:authorAffiliations>\n'
            source = []
            if 'instnames' in author:
                source.extend({'id': 1+self.sorted_insts.index(t)} for t in author['instnames'])
            if 'thanks' in author:
                source.extend({'id': 1+len(self.sorted_insts)+self.sorted_thanks.index(t), 'connection': filter_thanks(self.thanks[t])[0].capitalize()} for t in author['thanks'])
            for s in source:
                text += f'        <cal:authorAffiliation organizationid="a{s["id"]}" '
                if 'connection' in s and s['connection']:
                    text += f'connection="{s["connection"]}" '
                text += '/>\n'
            text += '      </cal:authorAffiliations>\n'
            text += '      <cal:authorids>\n'
            text += f'        <cal:authorid source="INTERNAL">{author["email"]}</cal:authorid>\n'
            if 'orcid' in author and author['orcid']:
                text += f'        <cal:authorid source="ORCID">{author["orcid"]}</cal:authorid>\n'
            text += '      </cal:authorids>\n'
            text += '    </foaf:Person>\n'
        text += """  </cal:authors>
</collaborationauthorlist>\n"""

        intro_text = 'This style for <a href="https://inspirehep.net/help/knowledge-base/authorxml/">INSPIRE authors.xml</a>.'

        return {
            'format_text': xhtml_escape(text),
            'intro_text': intro_text,
        }


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, state, collab=None):
        self.state = state
        self.collab = collab


class CollabHandler(BaseHandler):
    def get(self):
        return self.post()

    def common(self, date=''):
        if not date:
            date = today()

        raw = self.get_argument('raw', default=None)
        formatting = self.get_argument('formatting','web') if raw is None else 'web'

        r = AuthorListRenderer(self.state)
        kwargs = r.render(self.collab, date, formatting)

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

class APIAuthorHandler(tornado.web.RequestHandler):
    def initialize(self, states):
        self.states = states

    def write_error(self, status_code=500, **kwargs):
        """Write out custom error json."""
        data = {
            'code': status_code,
            'error': self._reason,
        }
        self.write(data)
        self.finish()

    def get(self):
        collab = self.get_argument('collab', 'IceCube')
        if collab not in ('IceCube', 'IceCube-PINGU', 'IceCube-Gen2'):
            raise tornado.web.HTTPError(400, reason='bad collaboration')

        date = validate_date(self.get_argument('date', default=''))
        if (not date) or date > today():
            date = today()
        elif collab == 'IceCube' and date < ICECUBE_START_DATE:
            date = ICECUBE_START_DATE
        elif collab == 'IceCube-PINGU' and date < PINGU_START_DATE:
            date = PINGU_START_DATE
        elif collab == 'IceCube-Gen2' and date < GEN2_START_DATE:
            date = GEN2_START_DATE

        r = AuthorListRenderer(self.states[collab.lower()])
        formatting = self.get_arguments('formatting')
        if not formatting:
            formatting = r.FORMATTING

        ret = {}
        for f in formatting:
            ret[f] = r.render(collab, date, f)
        self.write(ret)
