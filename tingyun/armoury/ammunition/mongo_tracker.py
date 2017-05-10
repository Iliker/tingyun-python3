# -*- coding: utf-8 -*-

"""this module used to wrap the specify armory to trace

"""

import logging

from tingyun.armoury.ammunition.timer import Timer
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.warehouse.mongo_node import MongoNode
from tingyun.logistics.basic_wrapper import wrap_object, FunctionWrapper

console = logging.getLogger(__name__)


class MongoTracker(Timer):
    """
    """

    def __init__(self, tracker, host, port, schema, method):
        """
        :return:
        """
        super(MongoTracker, self).__init__(tracker)
        self.host = host
        self.port = port
        self.method = method
        self.schema = schema or "NULL"

    def create_node(self):
        """
        :return:
        """
        tracker = current_tracker()
        if tracker:
            tracker.mongo_time = self.duration

        return MongoNode(method=self.method, children=self.children, start_time=self.start_time, schema=self.schema,
                         end_time=self.end_time, duration=self.duration, exclusive=self.exclusive, host=self.host,
                         port=self.port)

    def terminal_node(self):
        return True


def mongo_trace_wrapper(wrapped, schema, method, server=None):
    """
    :return:
    """

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()
        if tracker is None:
            return wrapped(*args, **kwargs)

        _method = method
        if callable(method):
            if instance is not None:
                _method = method(instance, *args, **kwargs)
            else:
                _method = method(*args, **kwargs)

        if callable(server):
            host, port, schema = server(instance, *args, **kwargs)
        else:
            host, port, schema = "Unknown", "Unknown", "Unknown"

        with MongoTracker(tracker, host, port, schema, _method):
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()
        if tracker is None:
            return wrapped(*args, **kwargs)

        if callable(server):
            host, port, schema = server(instance, *args, **kwargs)
        else:
            host, port, schema = "Unknown", "Unknown", "Unknown"

        with MongoTracker(tracker, host, port, schema, method):
            return wrapped(*args, **kwargs)

    if callable(method):
        return FunctionWrapper(wrapped, dynamic_wrapper)

    return FunctionWrapper(wrapped, literal_wrapper)


def wrap_mongo_trace(module, object_path, schema, method, server=None):
    wrap_object(module, object_path, mongo_trace_wrapper, (schema, method, server))
