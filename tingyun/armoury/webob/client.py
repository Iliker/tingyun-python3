
"""Define this module for openstack nova model

"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper, TARGET_NOVA_APP


def send_request_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    version = 'xx'
    try:
        import webob
        version = getattr(webob, "__version__", 'xx')
    except Exception as _:
        pass

    wsgi_application_wrapper(module.SendRequest, '__call__', ('nova', version, TARGET_NOVA_APP))
