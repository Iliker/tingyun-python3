"""this module used to implements the api for control the agent's actions include data collect and upload

"""

import atexit
import sys
import os
import time
import logging
import threading

from tingyun.config.settings import global_settings
from tingyun.packages import six
from tingyun.logistics.mapper import CONSTANCE_OUT_DATE_CONFIG, CONSTANCE_INVALID_DATA_TOKEN
from tingyun.logistics.mapper import CONSTANCE_INVALID_LICENSE_KEY
from tingyun.armoury.sampler.memory_usage import memory_usage_sampler
from tingyun.armoury.sampler.cpu_usage import cpu_usage_sampler
from tingyun.battlefield.application import Application

console = logging.getLogger(__name__)


class Dispatcher(object):
    """it is a agent core function center, include control function about the agent
    """
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self, config=None):
        """
        """
        console.info("Start python agent with version %s", global_settings().agent_version)
        self._last_harvest = 0.0

        self._harvest_thread = threading.Thread(target=self._harvest_loop, name="TingYunHarvestThread")
        self._harvest_thread.setDaemon(True)  # should take caution to the doc
        self._harvest_shutdown = threading.Event()

        self._config = config if config is not None else global_settings()
        self._lock = threading.Lock()
        self._process_shutdown = False
        self._applications = {}  # used to store the actived applications
        self.__max_tracker = 5000
        self.__data_sampler = []

        if self._config.enabled:
            atexit.register(self._atexit_shutdown)

            # Register our exit event to the uwsgi shutdown hooks.
            if 'uwsgi' in sys.modules:
                import uwsgi
                uwsgi_original_atexit_callback = getattr(uwsgi, 'atexit', None)

                def uwsgi_atexit_callback():
                    self._atexit_shutdown()
                    if uwsgi_original_atexit_callback:
                        uwsgi_original_atexit_callback()

                uwsgi.atexit = uwsgi_atexit_callback

    @staticmethod
    def singleton_instance():
        """
        :return: singleton instance
        """
        if Dispatcher._instance:
            return Dispatcher._instance

        instance = None
        with Dispatcher._instance_lock:
            if not Dispatcher._instance:
                instance = Dispatcher(global_settings())
                Dispatcher._instance = instance

                console.info('Creating instance of agent dispatcher')

        if instance:
            instance.register_data_sampler(memory_usage_sampler, ('memory.usage',))
            instance.register_data_sampler(cpu_usage_sampler, ('cpu.usage',))
            instance.active_dispatcher()

        return instance

    def global_settings(self):
        """
        :return:
        """
        return global_settings()

    def application_settings(self, app_name):
        """
        :param app_name:
        :return:
        """
        application = self._applications.get(app_name, None)
        if application:
            return application.application_config

    def _harvest_loop(self):
        """the real metric data harvest thread
        :rtype : None
        """
        console.info("start harvest thread with id %s", os.getpid())

        self.__next_harvest = time.time()
        last_harvest = time.time()
        try:
            while 1:
                # it's not a bug, just for deal the special situation
                if self._harvest_shutdown.isSet():  # python2.6 earlier api
                    self._do_harvest(last_harvest, time.time(), shutdown=True)
                    console.info("exit the controller first loop.")
                    return

                # we are not going to report in 1 min strictly, because the application or data maybe too large,
                # so extend the time appropriately according to the last report situation
                now = time.time()
                while self.__next_harvest <= now:
                    self.__next_harvest += 60.0

                self._harvest_shutdown.wait(self.__next_harvest - now)

                if self._harvest_shutdown.isSet():  # force do last harvest
                    self._do_harvest(last_harvest, time.time(), shutdown=True)
                    console.info("exit controller harvest loop at shutdown signal with last harvest.")
                    return

                self._do_harvest(last_harvest, time.time())
                last_harvest = time.time()
        except Exception as err:
            console.warning("error occurred %s", err)
            if self._process_shutdown:  # python interpreter exit
                console.critical('''Unexpected exception in main harvest loop when process being shutdown. This can occur
                                 in rare cases due to the main thread cleaning up and destroying objects while the
                                 background harvest thread is still running. If this message occurs rarely,
                                 it can be ignored. If the message occurs on a regular basis,
                                 then please report it to Ting Yun support for further investigation.''')
            else:  # other error.
                console.critical('''Unexpected exception in main harvest loop. Please report this problem to Ting Yun
                                support for further investigation''')

    def _do_harvest(self, last_harvest, current_harvest, shutdown=False):
        """do the really harvest action
        :param shutdown: sign the agent status, shutdown or not
        :return:
        """
        self._last_harvest = time.time()

        for name, application in six.iteritems(self._applications):

            # if application is not register to server. test it in application.
            #

            try:
                console.debug("Harvest data for application %s", name)

                # reset session with follow situation:
                #   config changed or data token invalid
                #   license key error occurred when communicate with data collector
                ret = application.harvest(last_harvest, current_harvest, shutdown)
                if ret and (CONSTANCE_OUT_DATE_CONFIG == ret[0] or CONSTANCE_INVALID_DATA_TOKEN == ret[0] or
                            CONSTANCE_INVALID_LICENSE_KEY == ret[0]):
                    console.info("Error occurred from server, dispatcher will stop session threading and restart it.%s",
                                 ret)

                    application.stop_connecting()
                    application.activate_session()

            except Exception as err:
                console.exception("Errors occurred when harvest application %s, %s", name, err)

        console.info("Spend %.2fs to harvest all applications.", time.time() - self._last_harvest)

    def active_dispatcher(self):
        """active a background controller thread if agent is enabled in settings
        """
        console.info('Start Agent controller main thread in process %s', os.getpid())
        if not self._config.enabled:
            console.info("agent is disabled,  agent controller not started.")
            return

        try:
            if self._harvest_thread.isAlive():
                console.info("agent controller was started, skip active it now.")
            else:
                console.info("Starting harvest thread now...")
                self._harvest_thread.start()

        except Exception as err:
            self._process_shutdown = True
            self.close_dispatcher()
            console.fatal("This exception indicates maybe internal agent python code error. please report to us"
                          " for further investigation. thank u.")
            console.fatal("Agent will stop work in this thread %s, %s", os.getpid(), err)

    def register_data_sampler(self, sampler, *args):
        """
        :param sampler:
        :return:
        """

        with self._lock:
            self.__data_sampler.append((sampler, args))

    def active_application(self, app_name, link_app=""):
        """active the core application for collecting or report
        :param app_name: the application name. Note, current stage only one application supported
        :param link_app: the application linked application
        :return: None
        """
        # this should be local settings
        if not self._config.enabled:
            console.info("Agent was disabled in configure file.")
            return

        if self._applications.get(app_name, None):
            console.debug("Application(%s) activated before.", app_name)
            return

        active_app = None
        with self._lock:
            app = self._applications.get(app_name, None)

            if not app:
                try:
                    app = Application(app_name, link_app)
                    self._applications[app_name] = app
                    active_app = True
                except Exception as err:
                    console.error("Init application failed, %s", err)

                for s in self.__data_sampler:
                    app.register_data_sampler(s[0], s[1])
            else:
                console.warning("Application triggered initial with app name: %s, pid: %s", app_name, os.getpid())

        if active_app:
            app.activate_session()

    def _atexit_shutdown(self):
        """define for python interpreter exit event
        :return:
        """

        self._process_shutdown = True
        self.close_dispatcher()

    def close_dispatcher(self, timeout=None):
        """shutdown the controller through the event signal
        """
        if timeout is None:
            timeout = self._config.shutdown_timeout

        if not self._harvest_shutdown.isSet():
            return

        # stop the connecting thread, if has.
        for name, application in six.iteritems(self._applications):
            console.info("Interpreter shutdown, terminal app connect threading now.")
            application.stop_connecting()

        self._harvest_shutdown.set()
        self._harvest_thread.join(timeout)

        console.info('Tingyun agent is Shutdown...')

    def record_tracker(self, app_name, tracker_node):
        """
        """
        application = self._applications.get(app_name, None)
        if application is None:
            console.warning("Application %s not exist, maybe some network issue cause this. if this is not expected,\
                             please contact us for help.", app_name)
            return

        # server disabled or agent not registered, skip to record the tracker data
        if not application.active:
            console.debug("Agent not registered to agent server, skip to record tracker data.")
            return

        if not application.application_config.enabled:
            console.debug("Agent disabled by server side, skip to record tracker data.")
            return

        application.record_tracker(tracker_node)


def dispatcher_instance():
    """
    :return: the singleton dispatcher object
    """
    dispatcher = Dispatcher.singleton_instance()
    return dispatcher
