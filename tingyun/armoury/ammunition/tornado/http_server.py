# -*- coding: utf-8 -*-

import logging

import time
from tingyun.logistics.basic_wrapper import wrap_function_wrapper
from tingyun.armoury.ammunition.tornado.util import finish_tracker, obtain_tracker_from_request

console = logging.getLogger(__name__)


def trace_tracker_export(wrapped, instance, args, kwargs):
    """
    """
    # request将以两种方式存在,一种是常规的tornado.Application  另外一种是WSGIContainer模式下,此时为非代理模式访问
    request = instance.request or instance.delegate.request
    if not request:
        console.warning("Errors, when finish the tracer when finish the tracer, this maybe some issue of design,"
                        "if this continue, pleae report to us, thank u.")
        return wrapped(*args, **kwargs)

    tracker = obtain_tracker_from_request(request)
    if not tracker:
        console.debug("Can not get trace from request, tracer maybe finished before.")
        return wrapped(*args, **kwargs)

    try:
        return wrapped(*args, **kwargs)
    finally:
        if getattr(request, "_finish_time", 0):
            tracker.end_time = getattr(request, "_finish_time", int(time.time()))

        finish_tracker(tracker)


def detect_http_server(module):
    """请求出口,  由于采用计数方式计算整个事务的生命周期,该出口调用时, 整个请求并未结束
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "_ServerRequestAdapter.finish", trace_tracker_export)
    wrap_function_wrapper(module, "_ServerRequestAdapter.on_connection_close", trace_tracker_export)
