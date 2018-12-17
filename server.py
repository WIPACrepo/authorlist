"""
Start an authorlist server.

Responsible for taking arguments, daemonizing, etc.
"""
import os
import logging
from functools import partial

from authorlist.daemon import Daemon
from authorlist.server import WebServer

def runner(args):
    logger = logging.getLogger('daemon')
    logfmt = '%(asctime)s %(levelname)s %(name)s %(module)s:%(lineno)s - %(message)s'
    logging.basicConfig(level=args.loglevel, filename=args.logfile, format=logfmt)

    w = WebServer(port=args.port, json=args.json)
    w.start()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist website')
    parser.add_argument('action',nargs='?',help='(start,stop) daemon server')
    parser.add_argument('-j','--json',help='authorlist json file')
    parser.add_argument('-p','--port',type=int,default=8888,help='port to listen on')
    parser.add_argument('-n','--no-daemon',dest='daemon',default=True,action='store_false',help='do not daemonize')
    parser.add_argument('--logfile',default='log',help='filename for logging')
    parser.add_argument('-l','--loglevel',default='info',help='log level')
    args = parser.parse_args()

    levels = ['error','warning','info','debug']
    if args.loglevel.lower() not in levels:
        raise Exception('invalid loglevel')
    args.loglevel = getattr(logging, args.loglevel.upper())

    if args.daemon:
        pid = os.path.join(os.getcwd(),'authorlist.pid')
        d = Daemon(pidfile=pid, chdir=os.getcwd(),
                   runner=partial(runner, args))
        if (not args.action) or args.action == 'start':
            d.start()
        elif args.action == 'stop':
            d.stop()
        elif args.action == 'restart':
            d.restart()
        elif args.action == 'kill':
            d.kill()
        else:
            raise Exception('unknown action')
    else:
        runner(args)

if __name__ == '__main__':
    main()
