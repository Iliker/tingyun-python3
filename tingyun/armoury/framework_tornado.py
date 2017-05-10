
"""
"""

import logging

from tingyun.armoury.ammunition.external_tracker import wrap_external_trace
from tingyun.armoury.ammunition.tornado_tracker.httpserver import connection_on_headers_wrapper
from tingyun.armoury.ammunition.tornado_tracker.httpserver import connect_on_request_body_wrapper
from tingyun.armoury.ammunition.tornado_tracker.httpserver import connection_finish_request_wrapper
from tingyun.armoury.ammunition.tornado_tracker.httpserver import iostream_close_callback_wrapper
from tingyun.armoury.ammunition.tornado_tracker.web import trace_request_exception, trace_wsgi_app_entrance
from tingyun.armoury.ammunition.tornado_tracker.web import trace_request_execute, trace_request_init


console = logging.getLogger(__name__)


def detect_wsgi_server_entrance(module):
    """
    :param module:
    :return:
    """
    # todo: we give up to detect the WSGIAdapter(v4.x)/WSGIApplication/WSGIContainer just because:
    # todo: 1. WSGIAdapter & WSGIApplication, we have detect the tornado application.__call__, so there is no need to
    # todo:    detect again.
    # todo: 2. WSGIContainer, give up to detect the entrance will suffer one situation, which can not capture the
    # todo:    request metric if tornado server run a WSGI app that we are not support.
    return
    # import tornado
    #
    # version = getattr(tornado, "version", "xx")
    #
    # # new feature in tornado 4.x
    # if hasattr(module, 'WSGIAdapter'):
    #     wsgi_application_wrapper(module.WSGIAdapter, "__call__", ("Tornado", version))
    #
    # # equivalent to WSGIAdapter call
    # if hasattr(module, "WSGIApplication"):
    #     # wsgi_application_wrapper(module.WSGIApplication, "__call__", ("Tornado", version))
    #     module.Application.__call__ = trace_wsgi_app_entrance(module.Application.__call__)
    #
    # def wsgi_container_wrapper(*args, **kwargs):
    #     """
    #     """
    #     def instance_parameters(wsgi_application, *args, **kwargs):
    #         return wsgi_application, args, kwargs
    #
    #     application, _args, _kwargs = instance_parameters(*args, **kwargs)
    #     application = wsgi_app_wrapper_entrance(application)
    #
    #     _args = (application, ) + _args
    #     return _args, _kwargs
    #
    # # Makes a WSGI-compatible function runnable on Tornado's HTTP server.
    # if hasattr(module, "WSGIContainer"):
    #     trace_in_function(module.WSGIContainer, "__init__", wsgi_container_wrapper)


def detect_wsgi_app_entrance(module):
    """
    """
    # in tornado 4.x.x, the application.__call__ will not be called directly.
    module.Application.__call__ = trace_wsgi_app_entrance(module.Application.__call__)

    if hasattr(module, "RequestHandler"):
        module.RequestHandler.__init__ = trace_request_init(module.RequestHandler.__init__)
        module.RequestHandler._handle_request_exception = trace_request_exception(module.RequestHandler._handle_request_exception)
        module.RequestHandler._execute = trace_request_execute(module.RequestHandler._execute)

    # for tornado 4.x
    # if hasattr(module, "_RequestDispatcher"):
    #     module._RequestDispatcher.headers_received = connection_on_headers_wrapper(module._RequestDispatcher.headers_received)
    #     module._RequestDispatcher.data_received = connect_on_request_body_wrapper(module._RequestDispatcher.data_received)
    #     module._RequestDispatcher.finish = connection_finish_request_wrapper(module._RequestDispatcher.finish)


def detect_tornado_main_process(module):
    """all of the data handled in HTTPConnection class, include build header/body/finish
    :param module:
    :return:
    """
    # for tornado 3.x
    if hasattr(module, "HTTPConnection"):
        module.HTTPConnection._on_headers = connection_on_headers_wrapper(module.HTTPConnection._on_headers)
        module.HTTPConnection._on_request_body = connect_on_request_body_wrapper(module.HTTPConnection._on_request_body)
        module.HTTPConnection._finish_request = connection_finish_request_wrapper(module.HTTPConnection._finish_request)


def detect_iostream(module):
    """
    :param module:
    :return:
    """

    if hasattr(module, "BaseIOStream"):
        module.BaseIOStream._maybe_run_close_callback = iostream_close_callback_wrapper(module.BaseIOStream._maybe_run_close_callback)


def detect_simple_httpclient(module):
    """
    :param module:
    :return:
    """
    def parse_url(instance, request, *args, **kwargs):
        return request

    wrap_external_trace(module, 'SimpleAsyncHTTPClient.fetch', 'simple_httpclient', parse_url)


def detect_curl_httpclient(module):
    """
    :param module:
    :return:
    """
    def parse_url(instance, request, *args, **kwargs):
        return request

    wrap_external_trace(module, 'CurlAsyncHTTPClient.fetch', 'curl_httpclient', parse_url)
