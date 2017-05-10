
"""define model just for tornado wsgi adapter mode
"""

import sys
import logging

from tingyun.logistics.object_name import callable_name
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.basic_wrapper import wrap_function_wrapper, function_wrapper
from tingyun.armoury.ammunition.function_tracker import FunctionTracker


console = logging.getLogger(__name__)
wrapted_func_cache = []


@function_wrapper
def _do_method_trace(wrapped, instance, args, kwargs):
    tracker = current_tracker()

    with FunctionTracker(tracker, name=callable_name(wrapped)):
        return wrapped(*args, **kwargs)


def trace_handler_execute(wrapped, instance, args, kwargs):
    """
    """
    handler = instance
    request = handler.request

    tracker = current_tracker()
    if not tracker:
        return wrapped(*args, **kwargs)

    if request.method not in handler.SUPPORTED_METHODS:
        name = callable_name(wrapped)
    else:
        name = callable_name(getattr(handler, request.method.lower()))

    tracker.set_tracker_name(name, priority=3)
    with FunctionTracker(tracker, name=callable_name(wrapped)):
        return wrapped(*args, **kwargs)


def trace_handler_request_exception(wrapped, instance, args, kwargs):
    """
    """
    tracker = current_tracker()
    if not tracker:
        return wrapped(*args, **kwargs)

    tracker.record_exception(*sys.exc_info())

    return wrapped(*args, **kwargs)


def trace_handler_init(wrapped, instance, args, kwargs):
    """
    """
    def parse_class_name(method):
        """parse the class name of the method belong to
        """
        for cls in method.__self__.__class__.__mro__:
            if method.__name__ in cls.__dict__:
                return cls.__name__
        return None

    methods = ['head', 'get', 'post', 'delete', 'patch', 'put', 'options']
    for method in methods:
        func = getattr(instance, method, None)
        func_name = callable_name(func)
        if func_name not in wrapted_func_cache:
            console.debug("Wrap http method `%s` with instance %s", method, callable_name(instance))
            setattr(instance, method, _do_method_trace(func))
            wrapted_func_cache.append(func_name)

    if parse_class_name(instance.prepare) != 'RequestHandler':
        instance.prepare = _do_method_trace(instance.prepare)

    if parse_class_name(instance.on_finish) != 'RequestHandler':
        instance.on_finish = _do_method_trace(instance.on_finish)

    return wrapped(*args, **kwargs)


def detect_handlers(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "RequestHandler._execute", trace_handler_execute)
    wrap_function_wrapper(module, "RequestHandler._handle_request_exception", trace_handler_request_exception)
    wrap_function_wrapper(module, "RequestHandler.__init__", trace_handler_init)
