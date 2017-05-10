# -*- coding: utf-8 -*-

"""the module wrapt main entrance

"""

import logging

from tingyun.armoury.ammunition.mongo_tracker import wrap_mongo_trace
from tingyun.armoury.ammunition.function_tracker import wrap_function_trace

console = logging.getLogger(__name__)
_methods = ['create_index', 'distinct', 'drop', 'drop_index', 'drop_indexes', 'ensure_index', 'find',
            'find_and_modify', 'find_one', 'group', 'index_information', 'inline_map_reduce', 'insert', 'map_reduce',
            'options', 'reindex', 'remove', 'rename', 'save', 'update', 'insert_one', 'insert', 'find_one_and_replace',
            'find_one_and_delete', 'find_one_and_update', 'aggregate']


def detect_connection(module):
    """
    :param module:
    :return:
    """
    if hasattr(module, "Connection"):
        wrap_function_trace(module, 'Connection.__init__', name='%s:Connection.__init__' % module.__name__)


def detect_mongo_client(module):
    """
    :param module:
    :return:
    """
    if hasattr(module, "MongoClient"):
        wrap_function_trace(module, "MongoClient.__init__", name="%s.MongoClient.__init__" % module.__name__)


def detect_collection(module):
    """
    :param module:
    :return:
    """
    def parse_connect_params(collection, *args, **kwargs):
        """collection有个属性database指向Database, Database有个属性client指向MongoClient，MongoClient中有个属性
        _topology_settings指向， 该类有个属性_seeds存储ip跟地址信息
        :param collection:
        :param args:
        :param kwargs:
        :return: (ip, port, collect)
        """
        host, port, db_name = "Unknown", 0, "Unknown"
        if hasattr(collection, "full_name"):
            db_name = collection.full_name

        try:
            # 如果使用默认host、port参数，该包会使用[('localhost', 27017)]，否则为集合set([(host, port)])
            server = collection.database.client._topology_settings._seeds
            if isinstance(server, set):
                server = list(server)

            host, port = server[0]
        except Exception as err:
            console.debug("Can not get the host and port for MongoDB %s", err)

        return host or "Unknown", port or 0, db_name or "Unknown"

    if not hasattr(module, "Collection"):
        console.info("module(%s) has not Collection object.", module)
        return

    for m in _methods:
        if not hasattr(module.Collection, m):
            console.info("Collection has not %s method", m)
            continue

        wrap_mongo_trace(module, "Collection.%s" % m, schema="", method=m, server=parse_connect_params)
