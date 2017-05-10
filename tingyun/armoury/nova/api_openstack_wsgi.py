
"""Define this module for openstack nova model

"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper, TARGET_NOVA_APP


def resource_wsgi_entrance(module):
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

    wsgi_application_wrapper(module.Resource, '__call__', ('nova', version, TARGET_NOVA_APP))
