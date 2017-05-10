"""define some wrapper for memcache client `pymemcache`
"""

import logging
from tingyun.armoury.ammunition.memcache_tracker import wrap_memcache_trace


console = logging.getLogger(__name__)
methods = ['add', 'append', 'cas', 'decr', 'delete', 'delete_many', 'delete_multi', 'flush_all', 'get',
           'get_many', 'get_multi', 'gets', 'gets_many', 'incr', 'prepend', 'replace', 'set', 'set_many', 'set_multi',
           'stats']


def detect_base_client(module):
    """
    :param module:
    :return:
    """
    def parse_connect_params(instance, *args, **kwargs):
        """
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        host, port = "Unknown", "Unknown"

        if hasattr(instance, 'server') and 2 == len(instance.server):
            host, port = instance.server[0], instance.server[1]

        return host or 'Unknown', port or 'Unknown'

    for m in methods:
        if hasattr(module.Client, m):
            wrap_memcache_trace(module, 'Client.%s' % m, m, server=parse_connect_params)
            console.debug("Wrap the base client method %s", m)


def detect_pooled_client(module):
    """for Pooled client
    :param module:
    :return:
    """
    if not hasattr(module, "PooledClient"):
        console.info("Pooled Client not in this version.")
        return

    def parse_connect_params(instance, *args, **kwargs):
        """
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        host, port = "Unknown", "Unknown"

        if hasattr(instance, 'server') and 2 == len(instance.server):
            host, port = instance.server[0], instance.server[1]

        return host, port

    for m in methods:
        if hasattr(module.PooledClient, m):
            wrap_memcache_trace(module, 'PooledClient.%s' % m, m, server=parse_connect_params)
            console.debug("Wrap the base pooled client method %s", m)


def detect_has_client(module):
    """this is a client for communicating with a cluster of memcached servers
    :param module:
    :return:
    """
    def parse_connect_params(instance, *args, **kwargs):
        """
        :param instance:
        :param args:
        :param kwargs:
        :return:
        """
        host, port = "Unknown", "Unknown"

        try:
            if hasattr(instance, 'clients') and 1 == len(instance.clients):
                key = instance.clients.keys()[0]
                host_port = str(key).split(":")
                host, port = host_port[0], host_port[1]
        except (AttributeError, IndexError) as err:
            console.warning("Parse host and port for pymongo hash client error %s", err)

        return host, port

    for m in methods:
        if hasattr(module.HashClient, m):
            wrap_memcache_trace(module, 'HashClient.%s' % m, m, server=parse_connect_params)
            console.debug("Wrap the hash client method %s", m)
