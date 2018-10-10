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

from .handlers import IceCubeHandler, PINGUHandler, Gen2Handler

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
            (r'/icecube', IceCubeHandler, {'state': State(json, collab='icecube')}),
            (r'/pingu', PINGUHandler, {'state': State(json, collab='pingu')}),
            (r'/icecube-gen2', Gen2Handler, {'state': State(json, collab='icecube-gen2')}),
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
