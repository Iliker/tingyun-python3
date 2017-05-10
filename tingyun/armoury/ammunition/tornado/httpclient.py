# -*- coding: utf-8 -*-

""" 捕获fetch_impl参数中回调函数的参数, 用于获取相应的http header
"""

import logging
from tingyun.armoury.ammunition.tornado_4.utils import obtain_current_tracker
from tingyun.logistics.basic_wrapper import FunctionWrapper, wrap_function_wrapper

console = logging.getLogger(__name__)


def trace_http_fetch_callback(wrapped, instance, args, kwagrs):
    """不捕获其执行时间，仅用于获取http传回的跨应用数据
    :return:
    """
    tracker = obtain_current_tracker()
    if not tracker:
        console.debug("Do not get tracker from current thread, this's maybe finish before.")

    def parse_reponse(response, *_args, **_kwargs):
        """http client(不论是异步还是同步) fetch 发生调用时, 会调用handle_response(response)作为回调函数
        response 为 HTTPResponse 实例
        :return:
        """
        return response, _args, _kwargs

    response, _args, _kwargs = parse_reponse(*args, **kwagrs)
    if hasattr(response, 'headers'):
        tracker._called_traced_data = eval(response.headers.get("X-Tingyun-Tx-Data", '{}'))

    return wrapped(response, _args, _kwargs)


def trace_fetch_impl(wrapped,  instance, args, kwargs):
    """
    :return:
    """
    def parse_callback_func(request, callback, *args, **kwargs):
        """
        :return:
        """
        return request, callback, args, kwargs

    request, callback_func, _args, _kwargs = parse_callback_func(*args, **kwargs)

    return wrapped(request, FunctionWrapper(callback_func, trace_http_fetch_callback), *_args, **_kwargs)


def detect_simple_httpclient(module):
    """
    :return:
    """
    # wrap_function_wrapper(module.Flask, 'fetch_impl', trace_fetch_impl)
