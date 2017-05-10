
"""this module defined to get the cpu usage/Utilization
"""

import os
import logging
from tingyun.logistics.attribution import TimeMetric
from tingyun.armoury.sampler.system_info import cpu_count

console = logging.getLogger(__name__)


class CpuUsage(object):
    """
    """
    def __init__(self, *args):
        """
        :return:
        """
        self.__times = None
        self.__cpu_count = 0

    def start(self):
        """
        :return:
        """
        try:
            self.__times = os.times()
        except Exception as _:
            self.__times = None

        self.__cpu_count = cpu_count()

    def stop(self):
        """
        :return:
        """
        self.__times = None

    def __call__(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return:
        """
        duration = 60
        if len(args) != 0:
            duration = args[0]

        if self.__times is None:
            return

        now = os.times()
        cpu_use_time = (now[0] + now[1]) - (self.__times[0] + self.__times[1])
        self.__times = now

        cpu_use_metric = "GENERAL/CPU/NULL/UserTime"
        yield [TimeMetric(name=cpu_use_metric, scope=cpu_use_metric, duration=int(cpu_use_time),
                          exclusive=int(cpu_use_time)), ]

        if not self.__cpu_count:
            console.debug("Cpu count is 0, skip count the cpu utilization")
            return

        cpu_utilization_metric = 'GENERAL/CPU/NULL/UserUtilization'
        utilization = int((cpu_use_time / duration / self.__cpu_count) * 100)
        yield [TimeMetric(name=cpu_utilization_metric, scope=cpu_utilization_metric,
                          duration=utilization, exclusive=utilization), ]


cpu_usage_sampler = CpuUsage
