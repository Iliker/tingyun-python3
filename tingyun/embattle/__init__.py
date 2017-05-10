
""" Prepare all need strategic materials to take advantage for the war
"""
from tingyun.embattle.inspection import take_control


def initialize(config_file=None):
    """ Can be triggered by application frame.
    :param config_file: config file for corps
    :return:
    """
    status = take_control(config_file).execute()
    return status
