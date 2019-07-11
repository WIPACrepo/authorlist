"""
Start an authorlist server.

Responsible for taking arguments, daemonizing, etc.
"""
import os
import logging
from functools import partial

from authorlist.daemon import Daemon
from authorlist.server import WebServer

CONFIG = {
    'PORT': os.environ.get('PORT', '8888'),
    'JSON': os.environ.get('JSON', None),
    'LOGFILE': os.environ.get('LOGFILE', '-'),
    'LOGLEVEL': os.environ.get('LOGLEVEL', 'info'),
}

def runner(args):
    logger = logging.getLogger('daemon')
    log_args = {
        'level': args.loglevel,
        'format': '%(asctime)s %(levelname)s %(name)s %(module)s:%(lineno)s - %(message)s',
    }
    if args.logfile and args.logfile != '-':
        log_args['filename'] = args.logfile
    logging.basicConfig(**log_args)

    w = WebServer(port=args.port, json=args.json)
    logging.info('server running on port %s', args.port)
    w.start()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Authorlist website')
    parser.add_argument('action',nargs='?',help='(start,stop) daemon server')
    parser.add_argument('-j','--json',default=CONFIG['JSON'],help='authorlist json file')
    parser.add_argument('-p','--port',type=int,default=int(CONFIG['PORT']),help='port to listen on')
    parser.add_argument('-n','--no-daemon',dest='daemon',default=True,action='store_false',help='do not daemonize')
    parser.add_argument('--logfile',default=CONFIG['LOGFILE'],help='filename for logging')
    parser.add_argument('-l','--loglevel',default=CONFIG['LOGLEVEL'],help='log level')
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
