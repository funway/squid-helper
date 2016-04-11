#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, logging, argparse
import redis

DESCRIPTION = """\
Digest authentication helper for squid 3.4+.
-----------------------------------------------
It get a line input from squid by sys.stdin, then fetch the auth info from redis-server, \
and finally send the info back to squid by sys.stdout.

Input line from squid:
    "username":"realm" [key-extras]
Output line send back to squid:
    OK ha1="xxx"
    or ERR message="xxx"
    or BH message="xxx"
key-value in redis:
    realm:username ==> ha1
-----------------------------------------------
"""

__version__ = '0.1.0'

LOGGING_FORMAT = '%(asctime)s - pid[%(process)d] - %(levelname)5s - %(name)s: %(message)s'
LOGGING_LEVEL = {
    'NOTSET': logging.NOTSET,
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
    'SILENT': logging.CRITICAL + 1
}

class DigestAuth(object):
    """docstring for DigestAuth"""
    def __init__(self, host = 'localhost', port = 6379):
        super(DigestAuth, self).__init__()
        self.host = host
        self.port = port
        self.logger = logging.getLogger(self.__class__.__name__)
        try:
            self.redis = redis.StrictRedis(host = self.host, port = self.port)
            self.redis.ping()
        except Exception, e:
            self.logger.error(e)
            raise e
        pass

    def run4ever(self):
        while True:
            # read a line from stdin
            line = sys.stdin.readline()

            # remove '\n' from line
            line = line.strip()

            self.logger.info('squid >> %s' % line)

            if line == '':
                self.logger.warning('get a empty line from squid')
                sys.stdout.write('BH message="digest_redis_auth: get a empty line from squid"\n')
                sys.stdout.flush()
                continue

            # parse the line into username & realm
            try:
                inputs = line.split('"')
                username = inputs[1]
                realm = inputs[3]
            except Exception, e:
                self.logger.warning('get a unresolved line from squid [%s]' % line)
                sys.stdout.write('BH message="digest_redis_auth: get a unresolved line from squid"\n')
                sys.stdout.flush()
                continue

            # get ha1 from redis-server with key[realm:username]
            try:
                ha1 = self.redis.get(realm + ':' + username)
                self.logger.info('redis[%s:%s] = %s' % (realm, username, ha1))
            except Exception, e:
                self.logger.error(e)
                raise e

            if ha1:
                sys.stdout.write('OK ha1="%s"\n' % ha1)
                sys.stdout.flush()
            else:
                # it seems that squid-3.5 has a problem with ERR response. 
                # so i have to use BH code to send back to squid
                sys.stdout.write('BH message="digest_redis_auth: no such user"\n')
                sys.stdout.flush()
            pass
        pass

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description = DESCRIPTION
        )
    parser.add_argument('-H', '--host', 
        help = 'The host of redis. Default is localhost.', 
        default = 'localhost')
    parser.add_argument('-p', '--port', 
        help = 'The port of redis. Default is 6379.', 
        default = 6379, 
        type = int)
    parser.add_argument('-f', '--logfile', 
        help = 'The file path for log. Default is None, no log to output.\
        To avoid potential problems from multiprocess logging, It will suffix the logfile with pid.', 
        default = None)
    parser.add_argument('-l', '--loglevel',
        metavar = 'LOGLEVEL',
        help = 'The log level for log {CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET}. Default is WARNING.', 
        default = 'WARNING', 
        choices = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'])
    parser.add_argument('--version',
        action = 'version',
        version = '%(prog)s ' + __version__)

    args = parser.parse_args()
    redisHost = args.host
    redisPort = args.port
    if args.logfile:
        logfile = args.logfile + '.' + str(os.getpid())
        loglevel = LOGGING_LEVEL[args.loglevel]
    else:
        logfile = '/dev/null'
        loglevel = LOGGING_LEVEL['SILENT']

    # setup logging config
    logging.basicConfig(level = loglevel, filename = logfile, format = LOGGING_FORMAT)

    # get a DigestAuth instance and run it
    digestAuth = DigestAuth(host = redisHost, port = redisPort)
    digestAuth.run4ever()
    
    pass

def test():

    pass

if __name__ == '__main__':
    main()
    # test()    
