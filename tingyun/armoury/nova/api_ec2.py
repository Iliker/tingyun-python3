
"""Define this module for openstack nova model

"""

from tingyun.armoury.trigger.wsgi_entrance import wsgi_application_wrapper, TARGET_NOVA_APP


def ec2_keystone_wsgi_entrance(module):
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

    wsgi_application_wrapper(module.EC2KeystoneAuth, '__call__', ('nova', version, TARGET_NOVA_APP))


def requestify_wsgi_entrance(module):
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

    wsgi_application_wrapper(module.Requestify, '__call__', ('nova', version, TARGET_NOVA_APP))


def authorizer_wsgi_entrance(module):
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

    wsgi_application_wrapper(module.Authorizer, '__call__', ('nova', version, TARGET_NOVA_APP))


def executor_wsgi_entrance(module):
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

    wsgi_application_wrapper(module.Executor, '__call__', ('nova', version, TARGET_NOVA_APP))
