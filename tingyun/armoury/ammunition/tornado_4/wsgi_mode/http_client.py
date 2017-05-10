
"""just for tornado synchronize request
"""

from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.logistics.basic_wrapper import wrap_function_wrapper
from tingyun.armoury.ammunition.external_tracker import ExternalTrace


def parse_request_url(*args, **kwargs):
    """
    """
    from tornado.httpclient import HTTPRequest

    def _parse_request(request, *args, **kwargs):
        return request

    request = _parse_request(*args, **kwargs)
    if isinstance(request, HTTPRequest):
        url = request.url
    else:
        url = request

    return url


def trace_tornado_http_request(wrapped, instance, args, kwargs):
    """
    """
    tracker = current_tracker()
    if not tracker:
        return wrapped(*args, **kwargs)

    _url = parse_request_url(*args, **kwargs)

    with ExternalTrace(tracker, "HTTPClient", _url):
        return wrapped(*args, **kwargs)


def detect_http_client(module):
    """
    :param module:
    :return:
    """
    wrap_function_wrapper(module, 'HTTPClient.fetch', trace_tornado_http_request)
