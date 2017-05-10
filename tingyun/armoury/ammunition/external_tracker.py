# -*- coding: utf-8 -*-

"""
"""

import time
import random
import logging

from tingyun.armoury.ammunition.timer import Timer
from tingyun.logistics.warehouse.external_node import ExternalNode
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.basic_wrapper import FunctionWrapper, wrap_object

console = logging.getLogger(__name__)


# defined error type for trace the external request errors.
MALFORMED_URL_ERROR_CODE = 900
UNKNOWN_HOST_ERROR_CODE = 901
CONNECT_EXCEPTION_ERROR_CODE = 902
TIMEOUT_EXCEPTION_ERROR_CODE = 903
CLIENT_PROTOCOL_ERROR_CODE = 904
CLIENT_ABORT_ERROR_CODE = 905
ILLEGAL_RESPONSE_ERROR_CODE = 906
SSL_EXCEPTION_ERROR_CODE = 908
OTHER_ERROR_CODE = 1000


class ExternalTrace(Timer):
    """define the external trace common api.

    """
    def __init__(self, tracker, library, url, params=None, external_id=None):
        super(ExternalTrace, self).__init__(tracker)

        self.library = library
        self.url = url.split('?')[0]
        self.params = parse_parameters(url, params)
        self.protocol = "http"
        self.protocol = "https" if "https" in url else self.protocol
        self.protocol = "thrift" if "thrift" in url else self.protocol
        self.external_id =  external_id

        signed_param = []
        for p in self.params:
            if tracker.settings and p in tracker.settings.external_url_params_captured.get(self.url, ""):
                signed_param.append("%s=%s&" % (p, self.params[p]))

        if 0 != len(signed_param):
            self.url = "%s?%s" % (self.url, ''.join(signed_param).rstrip('&'))

    def create_node(self):
        tracker = current_tracker()
        if tracker:
            tracker.external_time = self.duration

        return ExternalNode(library=self.library, url=self.url, children=self.children, protocol=self.protocol,
                            start_time=self.start_time, end_time=self.end_time, duration=self.duration,
                            exclusive=self.exclusive, external_id=self.external_id)

    def terminal_node(self):
        return True


def external_trace_wrapper(wrapped, library, url, params=None, exception_wrapper=None):
    """External id 必须保存到当前节点，否则多个跨应用同时进行时，会使用同一个external id
    :param wrapped:
    :param library:
    :param url:
    :param params: just use for cross trace and error trace with replaced headers.
    :param exception_wrapper:
    :return:
    """

    def dynamic_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        _url = url
        if callable(url):
            if instance is not None:
                _url = url(instance, *args, **kwargs)
            else:
                _url = url(*args, **kwargs)

        if callable(params):
            external_id, _args, _kwargs = params(*args, **kwargs)
        else:
            external_id, _args, _kwargs = None, args, kwargs

        with ExternalTrace(tracker, library, _url, kwargs, external_id):
            if not callable(params):
                if callable(exception_wrapper):
                    return exception_wrapper(wrapped, _url, params, *_args, **_kwargs)

                return wrapped(*args, **kwargs)
            else:
                if callable(exception_wrapper):
                    ret = exception_wrapper(wrapped, _url, _kwargs.get("params"), *_args, **_kwargs)
                else:
                    ret = wrapped(*_args, **_kwargs)

                try:
                    # for requests/urllib3
                    if hasattr(ret, 'headers'):
                        tracker._called_traced_data = eval(ret.headers.get("X-Tingyun-Tx-Data", '{}'))
                        console.debug("Get cross trace data with requests/urllib3, %s", tracker._called_traced_data)

                    # for httplib2, note: the httplib2 will trans the upper case to lower case
                    if isinstance(ret, tuple):
                        tracker._called_traced_data = eval(ret[0].get("x-tingyun-tx-data", '{}'))
                        console.debug("Get cross trace data with httplib2, %s", tracker._called_traced_data)
                except Exception as err:
                    console.debug(err)

                return ret

    def literal_wrapper(wrapped, instance, args, kwargs):
        tracker = current_tracker()

        if tracker is None:
            return wrapped(*args, **kwargs)

        with ExternalTrace(tracker, library, url, kwargs):
            return wrapped(*args, **kwargs)

    if callable(url):
        return FunctionWrapper(wrapped, dynamic_wrapper)

    return FunctionWrapper(wrapped, literal_wrapper)


def wrap_external_trace(module, object_path, library, url, params=None, exception_wrapper=None):
    wrap_object(module, object_path, external_trace_wrapper, (library, url, params, exception_wrapper))


def process_cross_trace(headers, protocol='http', msg_type='X-Tingyun-Id'):
    """
    """
    if headers is None:
        headers = {}

    tracker = current_tracker()
    if not tracker or not tracker.enabled:
        return headers, ''

    if not tracker.settings.transaction_tracer.enabled:
        return headers, ''

    # 用当前时间戳用作EXTERNAL_ID
    current_time = int(time.time() * 1000)
    external_id = str(current_time + random.randint(1, 1000))
    headers[msg_type] = tracker.settings.x_tingyun_id % (tracker._tingyun_id, tracker.generate_trace_id(),
                                                         external_id, current_time)
    return headers, external_id


def parse_parameters(_url, parameters):
    """
    :param _url: request url, which maybe contain get parameters
    :param parameters: keyword parameters
    :return:
    """
    if parameters and not isinstance(parameters, dict):
        return {}

    params_tmp = _url.split("?")
    _params = params_tmp[1] if 2 == len(params_tmp) else ""
    kv_params = [p for p in _params.split("&") if p.strip() and 2 == len(p.split("="))]

    actual_params = {}
    for kv in kv_params:
        k, v = kv.split('=', 1)
        if not k.strip() or not v.strip():
            continue

        actual_params[k.strip()] = v.strip()

    if parameters and isinstance(parameters, dict):
        actual_params.update(parameters)

    return actual_params
