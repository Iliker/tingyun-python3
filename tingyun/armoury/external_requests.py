
"""this module is defined to detect the requests module
"""

import sys
import logging
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.external_tracker import wrap_external_trace, process_cross_trace, parse_parameters
from tingyun.armoury.ammunition.external_tracker import MALFORMED_URL_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import CONNECT_EXCEPTION_ERROR_CODE, TIMEOUT_EXCEPTION_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import CLIENT_PROTOCOL_ERROR_CODE, ILLEGAL_RESPONSE_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import OTHER_ERROR_CODE

# not exist at v2.0.0
try:
    from requests.exceptions import ConnectTimeout
except ImportError:
    class ConnectTimeout(Exception):
        pass

try:
    from requests.exceptions import ReadTimeout
except ImportError:
    class ReadTimeout(Exception):
        pass

try:
    from requests.exceptions import ContentDecodingError
except ImportError:
    class ContentDecodingError(Exception):
        pass

try:
    from requests.exceptions import StreamConsumedError
except ImportError:
    class StreamConsumedError(Exception):
        pass

try:
    from requests.exceptions import InvalidSchema
except ImportError:
    class InvalidSchema(Exception):
        pass

try:
    from requests.exceptions import InvalidURL
except ImportError:
    class InvalidURL(Exception):
        pass

try:
    from requests.exceptions import URLRequired
except ImportError:
    class URLRequired(Exception):
        pass


try:
    from requests.exceptions import ChunkedEncodingError
except ImportError:
    class ChunkedEncodingError(Exception):
        pass

try:
    from requests.exceptions import MissingSchema
except ImportError:
    class MissingSchema(Exception):
        pass

try:
    from requests.exceptions import InvalidSchema
except ImportError:
    class InvalidSchema(Exception):
        pass

try:
    from requests.exceptions import ConnectionError
except ImportError:
    class ConnectionError(Exception):
        pass

try:
    from requests.exceptions import SSLError
except ImportError:
    class SSLError(Exception):
        pass


console = logging.getLogger(__name__)


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
    except ReadTimeout:
        error_code = TIMEOUT_EXCEPTION_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='requests')
        raise
    except (ConnectTimeout, ConnectionError, SSLError):
        error_code = CONNECT_EXCEPTION_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='requests')
        raise
    except (InvalidURL, URLRequired):
        error_code = MALFORMED_URL_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='requests')
        raise
    except (InvalidSchema, MissingSchema):
        error_code = CLIENT_PROTOCOL_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='requests')
        raise
    except (ChunkedEncodingError, ContentDecodingError, StreamConsumedError):
        error_code = ILLEGAL_RESPONSE_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='requests')
        raise
    except Exception:
        error_code = OTHER_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='requests')
        raise

    if int(getattr(rtv, 'status_code', 0)) != 200:
        tracker.record_external_error(url, error_code, getattr(rtv, 'status_code', 500), sys.exc_info(), params,
                                      module_name='requests')

    return rtv


def detect_requests_sessions(module):
    """
    :param module:
    :return:
    """
    def request_url(instance, method, url, *args, **kwargs):
        """
        """
        return url

    def parse_params(method, url, *args, **kwargs):
        _kwargs = kwargs
        _args = (method, url) + args
        protocol = 'http' if 'https' not in url else 'https'

        if 'headers' in _kwargs:
            ty_headers, external_id = process_cross_trace(_kwargs['headers'], protocol)
            _kwargs['headers'] = ty_headers
        else:
            ty_headers, external_id = process_cross_trace(None, protocol)
            _kwargs['headers'] = ty_headers

        return external_id, _args, _kwargs

    wrap_external_trace(module, 'Session.request', 'requests', request_url, params=parse_params,
                        exception_wrapper=wrap_exception)


