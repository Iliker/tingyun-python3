
"""this module is defined to wrap the thrift.
"""

import sys
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.external_tracker import wrap_external_trace, parse_parameters
from tingyun.armoury.ammunition.external_tracker import ILLEGAL_RESPONSE_ERROR_CODE, UNKNOWN_HOST_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import OTHER_ERROR_CODE


try:
    from thrift.transport.TTransport import TTransportException
except ImportError:
    class TTransportException(Exception):
        pass

try:
    from thrift.protocol.TProtocol import TProtocolException
except ImportError:
    class TProtocolException(Exception):
        pass


def wrap_exception(wrapped, action_url, parameters, *args, **kwargs):
    """
    """

    tracker = current_tracker()
    if tracker is None:
        return wrapped(*args, **kwargs)

    url = action_url if not callable(action_url) else action_url(*args, **kwargs)
    params = parameters if not callable(parameters) else parameters(*args, **kwargs)

    http_status = 500
    error_code = 0
    params = parse_parameters(url, params)

    try:
        return wrapped(*args, **kwargs)
    except TTransportException:
        error_code = UNKNOWN_HOST_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='thrift')
        raise
    except TProtocolException:
        error_code = ILLEGAL_RESPONSE_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='thrift')
        raise
    except Exception:
        error_code = OTHER_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='thrift')
        raise


def detect_tsocket(module):
    """
    :param module:
    :return:
    """
    def tsocket_url(tsocket, *args, **kwargs):
        # _unix_socket is passed in when TSocket initialized
        # when wrap the specified func, the tsocket is instance.
        url = 'thrift://%s:%s' % (tsocket.host, tsocket.port)

        if tsocket._unix_socket is None:
            url = 'thrift://%s:%s' % (tsocket.host, tsocket.port)

        return url

    wrap_external_trace(module, 'TSocket.open', 'thrift', tsocket_url, exception_wrapper=wrap_exception)


def detect_tsslsocket(module):
    """
    :param module:
    :return:
    """
    def tsocket_ssl_url(tsocket, *args, **kwargs):
        # _unix_socket is passed in when TSSSocket initialized
        # when wrap the specified func, the TSSSocket is instance.
        url = 'thrift//%s:%s' % (tsocket.host, tsocket.port)

        if tsocket._unix_socket is None:
            url = 'thrift//%s:%s' % (tsocket.host, tsocket.port)

        return url

    wrap_external_trace(module, 'TSSLSocket.open', 'thrift', tsocket_ssl_url, exception_wrapper=wrap_exception)
