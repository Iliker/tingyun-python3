# -*- coding: utf-8 -*-

"""communication proxy to dispatcher

"""
import logging
import threading
from tingyun.battlefield.dispatcher import dispatcher_instance
from tingyun.config.settings import global_settings

console = logging.getLogger(__name__)


class Proxy(object):
    """
    """
    _lock = threading.Lock()
    _instances = {}

    def __init__(self, dispatcher, app_name, link_app_name=None):
        """
        :param dispatcher:
        :param app_name:
        :return:
        """
        self.enabled = True
        self._app_name = app_name
        self.previous_time = 0  # 上一次性能追踪节点的时间戳，毫秒
        self._link_app_name = link_app_name if link_app_name else []

        if not app_name:
            self._app_name = global_settings().app_name

        if not dispatcher:
            dispatcher = dispatcher_instance()
            console.debug("init application with new dispatcher.")

        self._dispatcher = dispatcher

    @staticmethod
    def singleton_instance(name):
        """one application according to name
        """
        if not name:
            name = global_settings().app_name

        names = str(name).split(';')
        app_name = names[0]
        link_name = names[1:]

        controller = dispatcher_instance()
        instance = Proxy._instances.get(app_name, None)

        if not instance:
            with Proxy._lock:
                instance = Proxy._instances.get(app_name, None)
                if not instance:
                    instance = Proxy(controller, app_name, link_name)
                    Proxy._instances[app_name] = instance

                    console.info("Create new proxy with application name: %s", name)

        return instance

    @property
    def global_settings(self):
        """get the global settings or server settings
        :return:
        """
        return global_settings()

    @property
    def settings(self):
        """
        :return:
        """
        return self._dispatcher.application_settings(self._app_name)

    def activate(self):
        """
        :return:
        """
        self._dispatcher.active_application(self._app_name, self._link_app_name)

    def record_tracker(self, tracker_node):
        """
        """
        self._dispatcher.record_tracker(self._app_name, tracker_node)


def proxy_instance(name=None):
    return Proxy.singleton_instance(name)
