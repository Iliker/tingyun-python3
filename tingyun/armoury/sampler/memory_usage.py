
"""this module defined to get the memory usage information
"""

from tingyun.armoury.sampler.system_info import memory_used
from tingyun.logistics.attribution import TimeMetric


class MemoryUsage(object):
    """
    """
    def __init__(self, *args):
        """
        :return:
        """
        pass

    def start(self):
        """
        :return:
        """
        pass

    def stop(self):
        """
        :return:
        """
        pass

    def __call__(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return:
        """
        metric_name = 'GENERAL/Memory/NULL/PhysicalUsed'
        memory = int(memory_used())

        yield [TimeMetric(name=metric_name, scope=metric_name, duration=memory, exclusive=memory), ]


memory_usage_sampler = MemoryUsage
