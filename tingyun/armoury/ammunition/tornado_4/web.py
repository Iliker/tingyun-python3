# -*- coding: utf-8 -*-

"""define some detector for tornado4 web module
"""

import logging
import sys

from tingyun.armoury.ammunition.tornado_4.name_parser import object_name
from tingyun.armoury.ammunition.tornado_4.wrappers import wrap_function_wrapper, function_wrapper
from tingyun.armoury.ammunition.function_tracker import FunctionTracker
from tingyun.armoury.ammunition.tornado_4.utils import obtain_tracker_from_request
from tingyun.armoury.ammunition.tornado_4.utils import record_exception, TrackerTransferContext

console = logging.getLogger(__name__)


@function_wrapper
def _do_method_trace(wrapped, instance, args, kwargs):
    tracker = obtain_tracker_from_request(instance.request)
    if not tracker:
        return wrapped(*args, **kwargs)

    # 用户可能会重写RequestHandler中的_excute方法， 导致无法正确抓取metricName
    name = object_name(wrapped)
    http_methods = name.split(".")
    if len(http_methods) >= 2 and http_methods[-1] == instance.request.method.lower():
        tracker.set_tracker_name(name, priority=3)

    with FunctionTracker(tracker, name=name):
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

    result = wrapped(*args, **kwargs)

    for method in instance.SUPPORTED_METHODS:
        method = str(method).lower()
        func = getattr(instance, method, None)

        # 如果使用coroutine装饰过，会被附加上_previous_object属性,那么则跳过
        if func and not hasattr(func, "_previous_object"):
            setattr(instance, method, _do_method_trace(func))

    if parse_class_name(instance.prepare) != 'RequestHandler':
        instance.prepare = _do_method_trace(instance.prepare)

    if parse_class_name(instance.on_finish) != 'RequestHandler':
        instance.on_finish = _do_method_trace(instance.on_finish)

    return result


def trace_handler_request_exception(wrapped, instance, args, kwargs):
    """
    """
    tracker = obtain_tracker_from_request(instance.request)

    with TrackerTransferContext(tracker):
        record_exception(sys.exc_info())
        return wrapped(*args, **kwargs)


def trace_handler_execute(wrapped, instance, args, kwargs):
    """
    """
    handler = instance
    request = handler.request

    if not request:
        console.warning("No request instance got from handler. this maybe agent potential design issues. "
                        "if this continue, please report to us.")
        return wrapped(*args, **kwargs)

    tracker = obtain_tracker_from_request(request)
    if not tracker:
        return wrapped(*args, **kwargs)

    if request.method not in handler.SUPPORTED_METHODS:
        name = object_name(wrapped)
    else:
        name = object_name(getattr(handler, request.method.lower()))

    tracker.set_tracker_name(name, priority=3)
    with TrackerTransferContext(tracker):
        return wrapped(*args, **kwargs)


def trace_handler_flush(wrapped, instance, args, kwargs):
    """
    :return:
    """
    request = instance.request
    if not request:
        console.warning("No request instance got from handler, this maybe agent potential design issues.")
        return wrapped(*args, **kwargs)

    tracker = obtain_tracker_from_request(request)
    if not tracker:
        return wrapped(*args, **kwargs)

    tracker.deal_response('%s ok' % getattr(instance, '_status_code') or 500, {})
    return wrapped(*args, **kwargs)


def detect_web(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "RequestHandler._execute", trace_handler_execute)
    wrap_function_wrapper(module, "RequestHandler._handle_request_exception", trace_handler_request_exception)
    wrap_function_wrapper(module, "RequestHandler.__init__", trace_handler_init)
    wrap_function_wrapper(module, "RequestHandler.flush", trace_handler_flush)

