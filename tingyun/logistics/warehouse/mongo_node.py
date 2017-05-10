# -*- coding: utf-8 -*-

"""this module define the  mongodb trace data node

"""

from collections import namedtuple
from tingyun.logistics.attribution import TimeMetric, node_start_time, node_end_time

_MONGO_NODE = namedtuple("_MONGO_NODE", ['schema', 'method', 'children', 'start_time', 'end_time', 'duration',
                                         'exclusive', 'host', 'port'])


class MongoNode(_MONGO_NODE):
    """
    """
    def parse_db(self, schema):
        """从schema表中解析出数据库、collection、operation
        :param schema:
        :return: (db, collection, operation)
        """
        db, collection, operation = "Unknown", "Unknown", "Unknown"

        parts = str(schema).split(".", 1)
        if 2 != len(parts):
            return db, collection, operation
        else:
            db = parts[0]

        parts = str(parts[1]).split("/", 1)
        if len(parts) >= 2:
            collection = parts[0]
            operation = parts[1]
        else:
            collection = parts[0] if len(parts) >= 1 else "Unknown"

        return db, collection, operation

    def time_metrics(self, root, parent):
        """
        :param root:
        :param parent:
        :return:
        """
        method = str(self.method).upper()
        db, collection, _ = self.parse_db(self.schema)

        name = 'GENERAL/MongoDB/%s:%s%%2F%s/All' % (self.host, self.port, db)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = 'GENERAL/MongoDB/NULL/All'
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        if root.type == 'WebAction':
            name = "GENERAL/MongoDB/NULL/AllWeb"
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)
        else:
            name = "GENERAL/MongoDB/NULL/AllBackgound"
            yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = "GENERAL/MongoDB/%s:%s%%2F%s%%2F%s/%s" % (self.host, self.port, db, collection, method)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

        name = "MongoDB/%s:%s%%2F%s%%2F%s/%s" % (self.host, self.port, db, collection, method)
        yield TimeMetric(name=name, scope=root.path, duration=self.duration, exclusive=self.exclusive)

    def trace_node(self, root):
        """
        :param root:
        :return:
        """
        method = str(self.method).upper()
        params = {}
        children = []
        call_count = 1
        class_name = ""
        method_name = root.name
        root.trace_node_count += 1
        start_time = node_start_time(root, self)
        end_time = node_end_time(root, self)
        db, collection, _ = self.parse_db(self.schema)
        metric_name = "MongoDB/%s:%s%%2F%s%%2F%s/%s" % (self.host, self.port, db, collection, method)
        call_url = metric_name

        return [start_time, end_time, metric_name, "", call_count, class_name, method, params, children]
