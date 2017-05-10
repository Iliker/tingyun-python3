"""define some wrapper for memcache client `python-binary-memcache`
"""

import logging
from tingyun.armoury.ammunition.memcache_tracker import wrap_memcache_trace

console = logging.getLogger(__name__)
methods = ['add', 'cas', 'decr', 'delete', 'delete_multi', 'delete_multi', 'get',
           'get_multi', 'gets', 'incr', 'replace', 'set', 'set_multi',
           'stats']


def detect_client(module):
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
        if hasattr(instance, '_servers') and len(instance._servers) > 0:
            try:
                host, port = instance._servers[0].host, instance._servers[0].port
            except AttributeError:
                pass

        return host, port

    for m in methods:
        if hasattr(module.Client, m):
            wrap_memcache_trace(module, 'Client.%s' % m, m, server=parse_connect_params)
            console.debug("Wrap the base client method %s", m)
