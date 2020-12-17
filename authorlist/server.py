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

from . import collabs

from .handlers import IceCubeHandler, PINGUHandler, Gen2Handler, APIAuthorHandler

def get_template_path():
    return os.path.join(os.path.dirname(__file__),'templates')

def get_static_path():
    return os.path.join(os.path.dirname(__file__),'static')

class WebServer:
    def __init__(self, json, port=8888, debug=True):
        self.port = port

        states = {
            'icecube': State(json, collab='icecube'),
            'icecube-pingu': State(json, collab='pingu'),
            'icecube-gen2': State(json, collab='icecube-gen2'),
        }
        
        self.app = tornado.web.Application([
            (r'/', MainHandler, {'collabs': collabs}),
            (r'/icecube', IceCubeHandler, {'state': states['icecube']}),
            (r'/pingu', PINGUHandler, {'state': states['icecube-pingu']}),
            (r'/icecube-gen2', Gen2Handler, {'state': states['icecube-gen2']}),
            (r'/api/authors', APIAuthorHandler, {'states': states}),
        ], template_path=get_template_path(),
           template_whitespace='all' if debug else 'oneline',
           autoescape=None,
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
