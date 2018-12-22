"""
Edit the authorlist json file.
"""
from __future__ import print_function

import json
import random
import webbrowser
from pprint import pprint
from datetime import datetime

import tornado.ioloop
import tornado.web
from tornado.escape import json_encode, json_decode

from authorlist import collabs
from authorlist.handlers import author_ordering

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

def save(outfile, data):
    check(data)
    data['authors'].sort(key=author_ordering)

    if outfile:
        with open(outfile, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
    else:
        pprint(data)

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, outfile, data):
        self.outfile = outfile
        self.data = data

    def get(self):
        collaborations = set()
        institutions = set()
        for a in self.data['authors']:
            if a['to'] == '':
                collaborations.add(a['collab'])
                if 'instnames' in a:
                    for i in a['instnames']:
                        institutions.add(i)

        collaborations = {c:collabs[c] for c in collaborations}
        institutions = {inst:self.data['institutions'][inst]['cite'] for inst in institutions}
        
        self.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Author List Editor</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.12.6/css/selectize.min.css" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.12.6/css/selectize.default.min.css" />
    <style>
        footer {
            margin-top: 1em;
        }
        section.action article {
            margin: .5em;
        }
        button#id, button#update {
            margin: 1em;
        }
        article div.text, article div.select {
            margin: .5em 0;
            display: flex;
            align-items: center;
        }
        article span.label {
            margin-right: 0.5em;
        }
        article div.select div.selectize-control, article select {
            width: 100%;
        }
        section.results section.author {
            display: none;
            margin: 1em 0;
            border-top: 1px solid black;
            width: 100%;
        }
        section.results section.author.active {
            display: block;
        }
        article section.results div.hidden {
            display: none;
        }
    </style>
</head>
<body>
    <header><h1>Author List Editor</h1></header>
    <main>
        <article>            
            <section class="action">
                <button id="add">Add Author</button>
                <button id="edit">Edit Author</button>
            </section>
            <br>
        </article>
        <footer>
            <button id="submit">Reload</button>
        </footer>
    </main>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.12.6/js/standalone/selectize.min.js"></script>
    <script type="text/javascript">
        var data = """+json_encode(self.data)+""";
        var collaborations = """+json_encode(collaborations)+"""
        var institutions = """+json_encode(institutions)+"""

        function text_format(id, text, value=''){
            return '<div class="text"><span class="label">'+text+':</span><input autocomplete="off" class="'+id+'" type="text" value="'+value+'"></div>';
        }
        function date_format(id, text, value=''){
            return '<div class="text date"><span class="label">'+text+':</span><input autocomplete="off" class="'+id+'" type="date" value="'+value+'"></div>';
        }
        function select_format(id, text, options){
            var html = '<div class="select"><span class="label">'+text+':</span><select class="'+id+'" multiple=1>';
            for(var name in options){
                html += '<option value="'+name+'">'+options[name]+'</option>';
            }
            html += '</select></div>';
            return html;
        }
        function disabled_text_format(id, text, value){
            return '<div class="text"><span class="label">'+text+':</span><input autocomplete="off" disabled class="'+id+'" type="text" value="'+value+'"></div>';
        }
        function disabled_options_format(id, text, options){
            var html = '<div class="select"><span class="label">'+text+':</span><select disabled class="'+id+'" multiple=1>';
            for(var name in options){
                html += '<option selected value="'+name+'">'+options[name]+'</option>';
            }
            html += '</select></div>';
            return html;
        }
        function hidden_options_format(id, text, options){
            var html = '<div class="select hidden"><span class="label">'+text+':</span><select disabled class="'+id+'" multiple=1>';
            for(var name in options){
                html += '<option selected value="'+name+'">'+options[name]+'</option>';
            }
            html += '</select></div>';
            return html;
        }
        Array.prototype.equals = function( array ) {
            return this.length == array.length &&
                   this.every( function(this_i,i) { return this_i == array[i] } )
        };


        $('#add').on('click', function(e) {
            var html = '<section class="author">';
            html += text_format('name', 'Name');
            html += date_format('from', 'From');
            html += date_format('to', 'To');
            html += select_format('collaboration', 'Collaboration', collaborations);
            html += select_format('institution', 'Institution', institutions);
            html += select_format('thanks', 'Thanks', data['thanks']);
            html += '<button id="update">Update</button>';
            html += '</section>';
            $('article').html(html);
            $('select.collaboration').selectize({
                plugins: ['remove_button']
            });
            $('select.institution').selectize({
                plugins: ['remove_button']
            });
            $('select.thanks').selectize({
                plugins: ['remove_button']
            });
            $("#update").on('click', function(e) {
                // get data
                var collabs = $('select.collaboration').val();
                if (collabs == null)
                    collabs = [];
                var insts = $('select.institution').val();
                var thanks = $('select.thanks').val();
                var author;
                for (var i=0;i<collabs.length;i++){
                    author = {
                        'authname': $('input.name').val(),
                        'collab': collabs[i],
                        'from': $('input.from').val(),
                        'to': $('input.to').val()
                    }
                    if (insts != null)
                        author['instnames'] = insts;
                    if (thanks != null)
                        author['thanks'] = thanks;
                    data['authors'].push(author);
                }
                $('#submit').click()
            });
            $('#submit').hide();
        });
        $('#edit').on('click', function(e) {
            var html = '<section class="search">';
            var names = {};
            for (var i=0;i<data['authors'].length;i++) {
                names[data['authors'][i]['authname']] = data['authors'][i]['authname']
            }
            html += select_format('names', 'Filter by name', names);
            html += date_format('date', 'Filter by date');
            html += '</section>';
            html += '<section class="results"></section>';
            $('article').html(html);
            $('select.names').selectize({
                plugins: ['remove_button'],
                closeAfterSelect: true
            });
            var filter = function(e){
                var html = '';
                var names = $('select.names').val();
                var date = $('input.date').val();
                if (names == null && date == '')
                    return;
                var author = null;
                for(var i=0;i<data['authors'].length;i++) {
                    var a = data['authors'][i];
                    if (author != null) {
                        if (a['authname'] == author['authname']
                            && (!('instnames' in a ^ 'instnames' in author) || ('instnames' in a && a['instnames'].equals(author['instnames'])))
                            && (!('thanks' in a ^ 'thanks' in author) || ('thanks' in a && a['thanks'].equals(author['thanks'])))
                            && a['from'] == author['from']
                            && a['to'] == author['to']) {
                            author['collab'].push(a['collab']);
                            continue;
                        }
                        html += '<section class="author';
                        if ((names == null || names.some(n => n == author['authname'])) &&
                            (date == '' || (a['from'] <= date && (a['to'] == '' || a['to'] >= date)))) {
                            html += ' active';
                        }
                        html += '">';
                        html += disabled_text_format('name', 'Name', author['authname']);
                        html += date_format('from', 'From', author['from']);
                        html += date_format('to', 'To', author['to']);
                        var collabs = {};
                        for (var j=0;j<author['collab'].length;j++) {
                            collabs[author['collab'][j]] = collaborations[author['collab'][j]];
                        }
                        var insts = {};
                        if ('instnames' in author) {
                            for (var j=0;j<author['instnames'].length;j++) {
                                insts[author['instnames'][j]] = institutions[author['instnames'][j]];
                            }
                        }
                        var thanks = {};
                        if ('thanks' in author) {
                            for (var j=0;j<author['thanks'].length;j++) {
                                thanks[author['thanks'][j]] = thanks[author['thanks'][j]];
                            }
                        }
                        html += disabled_options_format('collaboration', 'Collaboration', collabs);
                        html += hidden_options_format('institution', 'Institution', insts);
                        html += hidden_options_format('thanks', 'Thanks', thanks);
                        html += '</section>';
                    }
                    
                    author = $.extend({}, a);
                    author['collab'] = [a['collab']]
                }
                html += '<button id="update">Update</button>';
                $('section.results').html(html);
                $("#update").on('click', function(e) {
                    // get data
                    var authors = [];
                    $('section.author').each(function(index, el){
                        var collabs = $(el).find('select.collaboration').val();
                        if (collabs == null)
                            collabs = [];
                        var insts = $(el).find('select.institution').val();
                        var thanks = $(el).find('select.thanks').val();
                        var author;
                        for (var i=0;i<collabs.length;i++){
                            author = {
                                'authname': $(el).find('input.name').val(),
                                'collab': collabs[i],
                                'from': $(el).find('input.from').val(),
                                'to': $(el).find('input.to').val()
                            }
                            if (insts != null)
                                author['instnames'] = insts;
                            if (thanks != null)
                                author['thanks'] = thanks;
                            authors.push(author);
                        }
                    });
                    data['authors'] = authors;
                    $('#submit').click()
                });
            };
            $('select.names').on('change', filter);
            $('input.date').on('change', filter);
            $('#submit').hide();
        });
        $("#submit").on('click', function(e) {
            $.ajax({
              type: "POST",
              url: "/",
              data: JSON.stringify({'data':data}),
              success: function(){ location.reload(true); },
              error: function(xhr, status, e){ alert(status); },
              dataType: "json",
              contentType : "application/json"
            });
        });
    </script>
</body>
</html>
""")

    def post(self):
        args = json_decode(self.request.body)
        if args['data']:
            self.data.update(args['data'])
            save(self.outfile, self.data)
        self.write({})

def make_app(outfile, data):
    kwargs = {'outfile': outfile, 'data': data}
    return tornado.web.Application([
        (r'/', MainHandler, kwargs),
    ], debug=True, autoescape=None)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist editor')
    parser.add_argument('-i','--input',help='input json file')
    parser.add_argument('-o','--output',default=None,help='output json file')

    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)
    data['authors'].sort(key=author_ordering)

    app = make_app(args.output, data)
    while True: # find an unused port we can bind to
        port = random.randint(8888,64000)
        try:
            app.listen(port)
        except Exception:
            continue
        break

    webbrowser.open('http://localhost:{}/'.format(port))
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
