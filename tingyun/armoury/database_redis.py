# -*- coding: utf-8 -*-

"""define redis weapon for detect the redis operation information.

"""

from tingyun.armoury.ammunition.function_tracker import wrap_function_trace
from tingyun.armoury.ammunition.redis_tracker import wrap_redis_trace

rewrite_command = ['setex', 'lrem', 'zadd']
basic_command = [
    'append', 'bgrewriteaof', 'bgsave', 'bitcount', 'bitop', 'bitpos', 'blpop', 'brpop', 'brpoplpush', 'client_getname',
    'client_kill', 'client_list', 'client_setname', 'config_get', 'config_resetstat', 'config_rewrite', 'config_set',
    'connection_pool', 'dbsize', 'debug_object', 'decr', 'delete', 'dump', 'echo', 'eval', 'evalsha', 'execute_command',
    'exists', 'expire', 'expireat', 'flushall', 'flushdb', 'from_url', 'get', 'getbit', 'getrange', 'getset', 'hdel',
    'hexists', 'hget', 'hgetall', 'hincrby', 'hincrbyfloat', 'hkeys', 'hlen', 'hmget', 'hmset', 'hscan', 'hscan_iter',
    'hset', 'hsetnx', 'hvals', 'incr', 'incrby', 'incrbyfloat', 'info', 'keys', 'lastsave', 'lindex', 'linsert', 'llen',
    'lock', 'lpop', 'lpush', 'lpushx', 'lrange', 'lrem', 'lset', 'ltrim', 'mget', 'move', 'mset', 'msetnx',
    'object', 'parse_response', 'persist', 'pexpire', 'pexpireat', 'pfadd', 'pfcount', 'pfmerge', 'ping', 'zunionstore',
    'pipeline', 'psetex', 'pttl', 'publish', 'pubsub', 'randomkey', 'register_script', 'rename', 'zscore',
    'renamenx', 'response_callbacks', 'restore', 'rpop', 'rpoplpush', 'rpush', 'rpushx', 'sadd', 'save',
    'scan', 'scan_iter', 'scard', 'script_exists', 'script_flush', 'script_kill', 'script_load', 'sdiff', 'zrevrank',
    'sdiffstore', 'set', 'set_response_callback', 'setbit', 'setex', 'setnx', 'setrange', 'shutdown', 'zscan',
    'sinter', 'sinterstore', 'sismember', 'slaveof', 'slowlog_get', 'slowlog_len', 'slowlog_reset', 'zscan_iter',
    'smembers', 'smove', 'sort', 'spop', 'srandmember', 'srem', 'sscan', 'sscan_iter', 'strlen', 'substr', 'zrevrange',
    'sunion', 'sunionstore', 'time', 'transaction', 'ttl', 'type', 'unwatch', 'watch', 'zadd', 'zcard',
    'zcount', 'zincrby', 'zinterstore', 'zlexcount', 'zrange', 'zrangebylex', 'zrangebyscore', 'zrank',
    'zrem', 'zremrangebylex', 'zremrangebyrank', 'zremrangebyscore', 'zrevrangebyscore',
    ]


def detect_connection(module):
    """
    :param module:
    :return:
    """
    if hasattr(module, 'Connection') and hasattr(module.Connection, 'connect'):
        wrap_function_trace(module, "Connection.connect", name="connect")


def detect_client_operation(module):
    """
    :param module:
    :return:
    """
    def parse_connect_params(instance, *args, **kwargs):
        """连接参数在client的connection_pool变量中
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            kw = instance.connection_pool.connection_kwargs
            host, port, db = kw.get('host'), kw.get('port'), kw.get('db')
        except AttributeError:
            host, port, db = "Unknown", "Unknown", 0

        return host, port, db or 0

    if hasattr(module, 'StrictRedis'):
        for command in basic_command:
            if hasattr(module.StrictRedis, command):
                wrap_redis_trace(module, "StrictRedis.%s" % command, command, server=parse_connect_params)

        if hasattr(module, 'Redis'):
            for command in rewrite_command:
                if hasattr(module.Redis, command):
                    wrap_redis_trace(module, "Redis.%s" % command, command, server=parse_connect_params)

    elif hasattr(module, 'Redis'):
        for command in basic_command:
            if hasattr(module.Redis, command):
                wrap_redis_trace(module, "Redis.%s" % command, command, server=parse_connect_params)
