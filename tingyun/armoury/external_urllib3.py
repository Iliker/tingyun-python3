
"""

"""

import sys
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.external_tracker import wrap_external_trace, process_cross_trace, parse_parameters

from tingyun.armoury.ammunition.external_tracker import MALFORMED_URL_ERROR_CODE, UNKNOWN_HOST_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import CONNECT_EXCEPTION_ERROR_CODE, TIMEOUT_EXCEPTION_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import CLIENT_PROTOCOL_ERROR_CODE, ILLEGAL_RESPONSE_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import OTHER_ERROR_CODE, SSL_EXCEPTION_ERROR_CODE


try:
    from urllib3.exceptions import TimeoutError
except ImportError:
    class TimeoutError(Exception):
        pass

try:
    from urllib3.exceptions import SSLError
except ImportError:
    class SSLError(Exception):
        pass

try:
    from urllib3.exceptions import DecodeError
except ImportError:
    class DecodeError(Exception):
        pass

try:
    from urllib3.exceptions import ResponseError
except ImportError:
    class ResponseError(Exception):
        pass


try:
    from urllib3.exceptions import ReadTimeoutError
except ImportError:
    class ReadTimeoutError(Exception):
        pass

try:
    from urllib3.exceptions import ConnectTimeoutError
except ImportError:
    class ConnectTimeoutError(Exception):
        pass

try:
    from urllib3.exceptions import ProtocolError
except ImportError:
    class ProtocolError(Exception):
        pass


try:
    from urllib3.exceptions import ResponseNotChunked
except ImportError:
    class ResponseNotChunked(Exception):
        pass

try:
    from urllib3.exceptions import HostChangedError
except ImportError:
    class HostChangedError(Exception):
        pass

try:
    from urllib3.exceptions import LocationParseError
except ImportError:
    class LocationParseError(Exception):
        pass

try:
    from urllib3.exceptions import LocationValueError
except ImportError:
    class LocationValueError(Exception):
        pass


try:
    from urllib3.exceptions import ProxyError
except ImportError:
    class ProxyError(Exception):
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
        rtv = wrapped(*args, **kwargs)
    except SSLError:
        error_code = SSL_EXCEPTION_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except (DecodeError, ResponseError, ResponseNotChunked):
        error_code = ILLEGAL_RESPONSE_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except (ConnectTimeoutError, ProxyError):
        error_code = CONNECT_EXCEPTION_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except ProtocolError:
        error_code = CLIENT_PROTOCOL_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except (HostChangedError, LocationParseError):
        error_code = UNKNOWN_HOST_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except LocationValueError:
        error_code = MALFORMED_URL_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except (TimeoutError, ReadTimeoutError):
        error_code = TIMEOUT_EXCEPTION_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise
    except Exception:
        error_code = OTHER_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib3')
        raise

    if int(getattr(rtv, 'status', 0)) != 200:
        tracker.record_external_error(url, error_code, getattr(rtv, 'status', 500), sys.exc_info(), params,
                                      module_name='urllib3')

    return rtv


def detect(module):
    """
    """
    def url_url_open(instance, method, url, *args, **kwargs):
        return url

    def parse_params(method, url, redirect=True, **kw):
        _args = (method, url)
        _kwargs = kw
        protocol = 'http' if 'https' not in url else 'https'

        if not kw:
            _kwargs = {}

        ty_headers, external_id = process_cross_trace(_kwargs.get("headers", None), protocol)
        _kwargs["redirect"] = redirect
        _kwargs["headers"] = ty_headers

        return external_id, _args, _kwargs

    wrap_external_trace(module, 'PoolManager.urlopen', 'urllib3', url_url_open, params=parse_params,
                        exception_wrapper=wrap_exception)
