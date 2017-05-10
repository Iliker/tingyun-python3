
"""this module is defined to detect the httplib2 module
"""

import sys
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.external_tracker import wrap_external_trace, process_cross_trace, parse_parameters
from tingyun.armoury.ammunition.external_tracker import MALFORMED_URL_ERROR_CODE, UNKNOWN_HOST_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import CONNECT_EXCEPTION_ERROR_CODE, TIMEOUT_EXCEPTION_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import CLIENT_PROTOCOL_ERROR_CODE, ILLEGAL_RESPONSE_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import OTHER_ERROR_CODE, SSL_EXCEPTION_ERROR_CODE


try:
    from httplib2 import HttpLib2ErrorWithResponse
except ImportError:
    class HttpLib2ErrorWithResponse(Exception):
        pass

try:
    from httplib2 import RedirectMissingLocation
except ImportError:
    class RedirectMissingLocation(Exception):
        pass

try:
    from httplib2 import FailedToDecompressContent
except ImportError:
    class FailedToDecompressContent(Exception):
        pass

try:
    from httplib2 import RelativeURIError
except ImportError:
    class RelativeURIError(Exception):
        pass

try:
    from httplib2 import ServerNotFoundError
except ImportError:
    class ServerNotFoundError(Exception):
        pass

try:
    from httplib2 import CertificateValidationUnsupported
except ImportError:
    class CertificateValidationUnsupported(Exception):
        pass

try:
    from httplib2 import SSLHandshakeError
except ImportError:
    class SSLHandshakeError(Exception):
        pass

try:
    from httplib2 import CertificateHostnameMismatch
except ImportError:
    class CertificateHostnameMismatch(Exception):
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
        resp, content = wrapped(*args, **kwargs)
    except (CertificateHostnameMismatch, SSLHandshakeError, CertificateValidationUnsupported):
        error_code = SSL_EXCEPTION_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='httplib2')
        raise
    except ServerNotFoundError:
        error_code = UNKNOWN_HOST_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='httplib2')
        raise
    except (RelativeURIError, RedirectMissingLocation):
        error_code = MALFORMED_URL_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='httplib2')
        raise
    except (FailedToDecompressContent, HttpLib2ErrorWithResponse):
        error_code = ILLEGAL_RESPONSE_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='httplib2')
        raise
    except Exception:
        error_code = OTHER_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='httplib2')
        raise

    if int(getattr(resp, 'status', 0)) != 200:
        tracker.record_external_error(url, error_code, getattr(resp, 'status', 500), sys.exc_info(), params,
                                      module_name='httplib2')

    return resp, content


def detect_httplib2_http(module):
    """
    :param module:
    :return:
    """
    def http_url(instance, uri, method="GET", *args, **kwargs):
        """
        :param instance:Http() instance
        :param uri:
        :param method:
        :param args:
        :param kwargs:
        :return:
        """
        return uri

    def parse_params(uri, method="GET", body=None, headers=None, **kwargs):
        """
        """
        _args = (uri, )
        _kwarg = kwargs

        if not kwargs:
            _kwarg = {}

        ty_headers, external_id = process_cross_trace(headers)
        _kwarg["method"] = method
        _kwarg["body"] = body
        _kwarg["headers"] = ty_headers

        return external_id, _args, _kwarg

    return wrap_external_trace(module, "Http.request", 'httplib2', http_url, params=parse_params,
                               exception_wrapper=wrap_exception)


def detect_http_connect_with_timeout(module):
    """
    :param module:
    :return:
    """
    def http_with_timeout_url(instance, *args, **kwargs):
        """
        :param instance: HTTPConnectionWithTimeout instance
        :param args:
        :param kwargs:
        :return:
        """
        url = "http://%s" % instance.host
        if instance.port:
            url = 'http://%s:%s' % (instance.host, instance.port)

        return url

    wrap_external_trace(module, "HTTPConnectionWithTimeout.connect", 'httplib2', http_with_timeout_url)


def detect_https_connect_with_timeout(module):
    """
    :param module:
    :return:
    """
    def https_with_timeout_url(instance, *args, **kwargs):
        """
        :param instance: HTTPSConnectionWithTimeout instance
        :param args:
        :param kwargs:
        :return:
        """
        url = "http://%s" % instance.host
        if instance.port:
            url = 'http://%s:%s' % (instance.host, instance.port)

        return url

    wrap_external_trace(module, "HTTPSConnectionWithTimeout.connect", 'httplib2', https_with_timeout_url)
