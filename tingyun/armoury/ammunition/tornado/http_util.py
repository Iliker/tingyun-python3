# -*- coding: utf-8 -*-

import time
import logging
from tingyun.armoury.ammunition.tornado_4.utils import obtain_current_tracker
from tingyun.armoury.ammunition.tornado.wrappers import wrap_function_wrapper
from tingyun.armoury.ammunition.tornado.util import is_websocket, generate_tracer
from tingyun.armoury.ammunition.external_tracker import process_cross_trace

console = logging.getLogger(__name__)


def trace_http_server_headers_received(wrapped, instance, args, kwargs):
    """ instance为HTTPServerRequest实例, 大部分应用都是实现web.Application实例，此时如果有读到数据，则既可会初始化Handler，
    所以从此刻开始算请求开始比，在httpserver._ServerRequestAdapter.headers_received开始算较精确

    另外一种是，用户使用adapter模式时，会从httpserver._ServerRequestAdapter.headers_received开始初始化Handler
    :return:
    """
    # 收到头信息后即刻初始化HTTPServerRequest，所以需要先调用原始函数才能对探针进行操作
    result = wrapped(*args, **kwargs)
    tracker = None if is_websocket(instance) else generate_tracer(instance)

    if tracker:
        tracker.start_time = getattr(instance, "_start_time", int(time.time()))

    return result


def trace_http_headers_init_(wrapped, instance, args, kwargs):
    """
    :return:
    """
    result = wrapped(*args, **kwargs)
    tracker = obtain_current_tracker()
    if tracker and hasattr(instance, 'X-Tingyun-Tx-Data'):
        tracker._called_traced_data = eval(instance.headers.get("X-Tingyun-Tx-Data", '{}'))

    process_cross_trace(instance)
    return result


def detect_http_util(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, "HTTPServerRequest.__init__", trace_http_server_headers_received)
    wrap_function_wrapper(module, "HTTPHeaders.__init__", trace_http_headers_init_)
