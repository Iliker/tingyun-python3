
"""this module define the sampler controller for sampler the data.
"""
import logging

console = logging.getLogger(__name__)


class SamplerController(object):
    """
    """
    def __init__(self, sampler, *args):
        """
        :param sampler:
        :param args:
        :return:
        """
        self.name = args[0]
        self.sampler = sampler
        self.args = args
        self.instance = None

    def start(self):
        """
        :return:
        """
        if self.instance is None:
            self.instance = self.sampler(self.args)

        if hasattr(self.instance, 'start'):
            self.instance.start()
            return

    def stop(self):
        if hasattr(self.instance, 'stop'):
            self.instance.stop()
        else:
            self.instance = None

    def metrics(self, *args):
        if self.instance is None:
            return []

        return self.instance(*args)
