"""Define this module for openstack nova model

"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper, TARGET_NOVA_APP, TARGET_WEB_APP


def response_wsgi_entrance(module):
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

    wsgi_application_wrapper(module.Response, '__call__', ('nova', version, TARGET_WEB_APP))
