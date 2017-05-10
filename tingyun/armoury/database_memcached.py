
"""

"""

from tingyun.armoury.ammunition.memcache_tracker import wrap_memcache_trace

# option: {object_path: $object_path, command: $command}
memcache_attr = {
    "add": {"path": "Client.add", "command": "add"},
    "append": {"path": "Client.append", "command": "append"},
    "cas": {"path": "Client.cas", "command": "cas"},
    "decr": {"path": "Client.decr", "command": "decr"},
    "delete": {"path": "Client.delete", "command": "delete"},
    "delete_multi": {"path": "Client.delete_multi", "command": "delete"},
    "get": {"path": "Client.get", "command": "get"},
    "gets": {"path": "Client.gets", "command": "get"},
    "get_multi": {"path": "Client.get_multi", "command": "get"},
    "incr": {"path": "Client.incr", "command": "incr"},
    "prepend": {"path": "Client.prepend", "command": "prepend"},
    "replace": {"path": "Client.replace", "command": "replace"},
    "set": {"path": "Client.set", "command": "set"},
    "set_multi": {"path": "Client.set_multi", "command": "set"},
}


def detect(module):
    def parse_connect_param(instance, *args, **kwargs):
        """
        :return:
        """
        host, port = "Unknown", "Unknown"
        if hasattr(instance, 'servers') and len(instance.servers) > 0:
            try:
                host, port = instance.servers[0].ip, instance.servers[0].port
            except AttributeError:
                pass

        return host, port

    for attr in memcache_attr:
        if hasattr(module.Client, attr):
            wrap_memcache_trace(module, memcache_attr[attr]['path'], attr, server=parse_connect_param)
