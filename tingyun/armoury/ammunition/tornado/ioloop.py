# -*- coding: utf-8 -*-

import sys

from tingyun.armoury.ammunition.tornado.util import record_exception
from tingyun.armoury.ammunition.tornado.util import TrackerTransferContext
from tingyun.armoury.ammunition.tornado.wrappers import wrap_function_wrapper


def trace_handle_callback_exception(wrapped, instance, args, kwargs):
    """
    """
    record_exception(sys.exc_info())

    return wrapped(*args, **kwargs)


def trace_call_at(wrapped, instance, args, kwargs):
    """
    """
    with TrackerTransferContext(None):
        return wrapped(*args, **kwargs)


def trace_add_handler(wrapped, instance, args, kwargs):
    """
    """
    with TrackerTransferContext(None):
        return wrapped(*args, **kwargs)


def detect_ioloop(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, 'IOLoop.handle_callback_exception', trace_handle_callback_exception)
    wrap_function_wrapper(module, 'PollIOLoop.call_at', trace_call_at)
    wrap_function_wrapper(module, 'PollIOLoop.add_handler', trace_add_handler)
