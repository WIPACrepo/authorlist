"""
Start an authorlist server.

Responsible for taking arguments, daemonizing, etc.
"""

from functools import partial

from daemonize import Daemonize

from authorlist.server import WebServer

def runner(args):
    w = WebServer(port=args.port, json=args.json)
    w.start()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist website')
    parser.add_argument('json',help='authorlist json file')
    parser.add_argument('-p','--port',type=int,default=8888,help='port to listen on')
    parser.add_argument('-n','--no-daemon',dest='daemon',default=True,action='store_false',help='do not daemonize')
    args = parser.parse_args()

    if args.daemon:
        pid = '/tmp/authorlist.pid'
        d = Daemonize(app='authorlist', pid=pid, action=partial(runner, args))
        d.start()
    else:
        runner(args)

if __name__ == '__main__':
    main()