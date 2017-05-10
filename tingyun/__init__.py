
# Note: alpha/beta version should not be delivered to customer
#       only ('alpha', 'beta', 'rc', 'final') used
#       {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
VERSION = (1, 3, 0, 'final', 0)


def get_version():
    """
    :return:
    """
    from tingyun.version import get_version
    return get_version(VERSION)
