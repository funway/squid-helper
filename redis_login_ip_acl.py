#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, logging, argparse, time
import redis

DESCRIPTION = """\
Access Control (ACL) helper for squid 3.4+. 
该程序将用户的login ip缓存在redis数据库中，以prefix:username为key，以第一次登录时间为score的一个有序集合。
每个用户的login ip有序集合的ttl默认为1小时，可以由ttl参数设置。
可以通过acl取[login ip]有序集中的前N个，或者后N个，来限制用户从多个ip登录。
acl参数count默认为前1个，即在ttl时间内，同一个账户只允许第一个登录ip访问
count如果设为-2，即表示在ttl时间内，同一个账户只允许最新两个登录的ip访问
-------------------------------------------------
Usage in squid.conf:
    external_acl_type redis_login_ip cache=0 children-max=1 ipv4 %LOGIN %SRC /etc/squid/redis_login_ip_acl.py -p fp_loginip -t 1800 -l DEBUG -f /var/log/squid/loginip.log
    acl in_loginip_limit external redis_login_ip 1
    http_access deny !in_loginip_limit

Input line from squid:
    username ip [count]
Output line send back to squid:
    OK
    or ERR message="xxx"
    or BH message="xxx"
key-value in redis:
    prefix:username ==> [sorted set of login ip]
-------------------------------------------------
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

class LoginIpAcl(object):
    # 默认的count参数，如果squid input line中没有定义的话
    defaultCount = 1

    def __init__(self, host = 'localhost', port = 6379, prefix = '', ttl = 3600):
        super(LoginIpAcl, self).__init__()
        self.host = host
        self.port = port
        self.prefix = prefix
        self.ttl = ttl
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
                sys.stdout.write('BH message="get a empty line from squid"\n')
                sys.stdout.flush()
                continue

            # parse the input line
            try:
                inputs = line.split(' ', 2)
                username = inputs[0]
                ip = inputs[1]
                count = int(inputs[2]) if len(inputs) > 2 else LoginIpAcl.defaultCount
            except Exception, e:
                self.logger.warning('get a unresolved line from squid [%s]' % line)
                sys.stdout.write('BH message="get a unresolved line from squid"\n')
                sys.stdout.flush()
                continue

            key = self.prefix + username
            try: 
                # 以当前时间戳为score，将ip加入到key的有序集合，如果已存在则不添加
                if None == self.redis.zrank(key, ip):
                    self.redis.zadd(key, time.time(), ip)
                    # 设置key的ttl
                    if -1 == self.redis.ttl(key):
                        self.redis.expire(key, self.ttl)   

                # 根据输入的count参数获取login ip有序集合的子集
                iplist = self.redis.zrange(key, 0, count - 1) if count > 0 else self.redis.zrange(key, count, -1)
                self.logger.info('get valid iplist %s' % iplist)
            except Exception, e:
                self.logger.error(e)
                raise e

            # 判断输入的ip是否在该子集
            if ip in iplist:
                self.logger.info('ip %s is valid' % ip)
                sys.stdout.write('OK\n')
                sys.stdout.flush()
            else:
                self.logger.info('ip %s not in valid iplist' % ip)
                sys.stdout.write('ERR message="ip %s not in valid iplist %s"\n' % (ip, iplist))
                sys.stdout.flush()
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
    parser.add_argument('-P', '--port', 
        help = 'The port of redis. Default is 6379.', 
        default = 6379, 
        type = int)
    parser.add_argument('-p', '--prefix', 
        help = 'The key\'s prefix in redis. Default is empty.', 
        default = '')
    parser.add_argument('-t', '--ttl', 
        help = 'The life time in seconds for one user\'s ip set. Default is 3600.', 
        default = 3600, 
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
    redisPrefix = args.prefix + ':' if args.prefix else ''
    redisTTL = args.ttl
    if args.logfile:
        logfile = args.logfile + '.' + str(os.getpid())
        loglevel = LOGGING_LEVEL[args.loglevel]
    else:
        logfile = '/dev/null'
        loglevel = LOGGING_LEVEL['SILENT']

    # setup logging config
    logging.basicConfig(level = loglevel, filename = logfile, format = LOGGING_FORMAT)

    # get a DigestAuth instance and run it
    loginIpAcl = LoginIpAcl(host = redisHost, port = redisPort, prefix = redisPrefix, ttl = redisTTL)
    loginIpAcl.run4ever()
    
    pass

def test():

    pass

if __name__ == '__main__':
    main()
    # test()    
