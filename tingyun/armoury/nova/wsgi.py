"""Define this module for nova.wsgi

"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper, TARGET_NOVA_APP


def middleware_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    version = 'xx'
    try:
        import nova
        version = getattr(nova, "__version__", 'xx')
    except Exception as _:
        pass

    wsgi_application_wrapper(module.Middleware, '__call__', ('nova', version, TARGET_NOVA_APP))


def router_wsgi_entrance(module):
    """
    :param module:
    :return:
    """
    version = 'xx'
    try:
        import nova
        version = getattr(nova, "__version__", 'xx')
    except Exception as _:
        pass

    wsgi_application_wrapper(module.Router, '__call__', ('nova', version, TARGET_NOVA_APP))

