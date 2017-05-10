"""this module used to wrap the specify method to RedisTrace

"""

from tingyun.armoury.ammunition.timer import Timer
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.warehouse.redis_node import RedisNode
from tingyun.logistics.basic_wrapper import wrap_object, FunctionWrapper


class RedisTrace(Timer):
    """
    """
    def __init__(self, tracker, host, port, db, command):
        """
        :return:
        """
        super(RedisTrace, self).__init__(tracker)
        self.host = host
        self.port = port
        self.db = db
        self.command = command

    def create_node(self):
        """
        :return:
        """
        tracker = current_tracker()
        if tracker:
            tracker.redis_time = self.duration

        return RedisNode(command=self.command, children=self.children, start_time=self.start_time, host=self.host,
                         end_time=self.end_time, duration=self.duration, exclusive=self.exclusive, port=self.port,
                         db=self.db)

    def terminal_node(self):
        return True


def redis_trace_wrapper(wrapped, command, server=None):
    """
    :return:
    """
    def dynamic_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()
        if tracker is None:
            return wrapped(*args, **kwargs)

        if instance:
            _command = command(instance, *args, **kwargs)
        else:
            _command = command(*args, **kwargs)

        if callable(server) and instance:
            host, port, db = server(instance, *args, **kwargs)
        else:
            host, port, db = "Unknown", 0, 0

        with RedisTrace(tracker, host, port, db, _command):
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()
        if tracker is None:
            return wrapped(*args, **kwargs)

        if callable(server) and instance:
            host, port, db = server(instance, *args, **kwargs)
        else:
            host, port, db = "Unknown", 0, 0

        with RedisTrace(tracker, host, port, db, command):
            return wrapped(*args, **kwargs)

    if callable(command):
        return FunctionWrapper(wrapped, dynamic_wrapper)

    return FunctionWrapper(wrapped, literal_wrapper)


def wrap_redis_trace(module, object_path, command, server=None):
    wrap_object(module, object_path, redis_trace_wrapper, (command, server))
