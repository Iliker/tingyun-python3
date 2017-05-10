
"""

"""

import sys
from tingyun.packages import six
from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.external_tracker import wrap_external_trace, parse_parameters
from tingyun.armoury.ammunition.external_tracker import MALFORMED_URL_ERROR_CODE
from tingyun.armoury.ammunition.external_tracker import OTHER_ERROR_CODE

# python3.4+ has not this module. so do not catch the import error.
from urllib2 import URLError, HTTPError


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
    except HTTPError as err:
        http_status = getattr(err, "code")  # equal to getcode()
        error_code = OTHER_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib2')
        raise

    except URLError:
        error_code = MALFORMED_URL_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib2')
        raise

    except Exception:
        error_code = OTHER_ERROR_CODE
        tracker.record_external_error(url, error_code, http_status, sys.exc_info(), params, module_name='urllib2')
        raise

    http_status = rtv.getcode()
    if http_status is not None and int(http_status) != 200:
        tracker.record_external_error(url, error_code, int(http_status), sys.exc_info(), params, module_name='urllib2')

    return rtv


def detect(module):
    def url_opener_open(instance, fullurl, *args, **kwargs):
        """
        :param instance:
        :param fullurl:
        :param args:
        :param kwargs:
        :return:
        """
        if isinstance(fullurl, six.string_types):
            return fullurl
        else:
            return fullurl.get_full_url()

    wrap_external_trace(module, 'OpenerDirector.open', 'urllib2', url_opener_open, exception_wrapper=wrap_exception)
