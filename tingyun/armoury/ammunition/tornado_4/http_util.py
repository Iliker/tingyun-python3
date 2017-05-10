# -*- coding: utf-8 -*-

""" define some detector for tracer entrance
"""

import time
import logging

from tingyun.armoury.ammunition.tornado_4.utils import is_websocket, generate_tracer
from tingyun.armoury.ammunition.tornado_4.wrappers import wrap_function_wrapper
from tingyun.armoury.ammunition.tornado_4.name_parser import object_name

console = logging.getLogger(__name__)


def trace_server_request_init_(wrapped, request, args, kwargs):
    """agent tracer entrance in tornado, will be called  after header but body. Three situations will be called.
        1. a common web.Application instance.
        2.instance passed into httpserver.HTTPServer is a not tornado application.
        3. In wsgi module. some WSGI applications.

    :param request: a `request` Instance of current user request.
    """
    result = wrapped(*args, **kwargs)

    tracker = None if is_websocket(request) else generate_tracer(request)
    if tracker:
        tracker.set_tracker_name(object_name(wrapped), priority=1)
        tracker.start_time = getattr(request, "_start_time", int(time.time()))

    request._nb_tracker = tracker
    return result


def detect_tracker_entrance(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "HTTPServerRequest.__init__", trace_server_request_init_)
