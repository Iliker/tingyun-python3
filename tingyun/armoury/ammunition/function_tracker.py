
"""all the function in the battle traced will use this function tracker.

"""
import logging
import functools
import traceback

from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.warehouse.function_node import FunctionNode
from tingyun.armoury.ammunition.timer import Timer
from tingyun.logistics.basic_wrapper import FunctionWrapper, wrap_object
from tingyun.logistics.object_name import callable_name

console = logging.getLogger(__name__)


class FunctionTracker(Timer):
    """
    """
    def __init__(self, tracker, name, group=None, label=None, params=None):
        super(FunctionTracker, self).__init__(tracker)

        self.name = name
        self.group = group or 'Function'
        self.label = label
        self.params = params

        self.stack_trace = None

    def create_node(self):
        """create function trace node
        """
        return FunctionNode(group=self.group, name=self.name, children=self.children, start_time=self.start_time,
                            end_time=self.end_time, duration=self.duration, exclusive=self.exclusive,
                            params=self.params, stack_trace=self.stack_trace)

    def finalize_data(self):
        """create all the data if need
        :return:
        """
        settings = self.tracker.settings

        if settings.action_tracer.enabled and self.duration >= settings.action_tracer.stack_trace_threshold:
            if self.tracker.stack_trace_count < settings.stack_trace_count:
                self.stack_trace = traceback.extract_stack()
                self.tracker.stack_trace_count += 1


def function_trace_wrapper(wrapped, name=None, group=None, label=None, params=None):

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        _name = name
        _params = params
        _label = label
        _group = group

        if callable(name):
            if instance is not None:
                _name = name(instance, *args, **kwargs)
            else:
                _name = name(*args, **kwargs)
        elif name is None:
            _name = callable_name(wrapped)

        if callable(group):
            if instance is not None:
                _group = group(instance, *args, **kwargs)
            else:
                _group = group(*args, **kwargs)

        with FunctionTracker(tracker, _name, _group, _label, _params):
            return wrapped(*args, **kwargs)

    def literal_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        _name = name or callable_name(wrapped)

        with FunctionTracker(tracker, _name, group, label, params):
            return wrapped(*args, **kwargs)

    if callable(name) or callable(group) or callable(label) or callable(params):
        return FunctionWrapper(wrapped, dynamic_wrapper)

    return FunctionWrapper(wrapped, literal_wrapper)


def wrap_function_trace(module, object_path, name=None, group=None, label=None, params=None):
    return wrap_object(module, object_path, function_trace_wrapper, (name, group, label, params))


def function_trace_decorator(name=None, group=None):
    """
    :param name: the name of the function named to
    :param group: the group of the function belong to. default `Function`
    :return:
    """
    return functools.partial(function_trace_wrapper, name=name, group=group)
