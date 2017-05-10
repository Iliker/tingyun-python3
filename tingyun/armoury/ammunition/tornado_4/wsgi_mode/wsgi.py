
"""define module for tornado wsgi entrance. but not support tornado core functions

"""

import logging
from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper

console = logging.getLogger(__name__)


def detect_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    try:
        import tornado
        version = tornado.version
    except Exception:
        version = "xx"

    if hasattr(module, "WSGIAdapter"):
        wsgi_application_wrapper(module.WSGIAdapter, '__call__', ('Tornado', version))
    else:
        console.warning("WSGIAdapter not exist in tornado 3.x, and we are not support 3.x version now.")
