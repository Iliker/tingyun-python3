
"""This module do some inspect and preparation for armoury and corps

"""
import logging
import os
import sys
import threading
import traceback

try:
    import ConfigParser  # for python2.x
except ImportError:
    import configparser as ConfigParser  # for python3.x

from tingyun.logistics.mapper import ENV_CONFIG_FILE
from tingyun.logistics.exceptions import ConfigurationError
from tingyun.logistics.mapper import map_log_level, map_key_words, map_app_name
from tingyun.config.settings import global_settings
from tingyun.embattle.log_file import initialize_logging
from tingyun.packages.wrapt.importer import register_post_import_hook
from tingyun.embattle.repertoire import defined_repertoire
from tingyun.config.start_log import log_bootstrap

console = logging.getLogger(__name__)


class Embattle(object):
    """
    """
    _lock = threading.Lock()
    _instance = None

    def __init__(self, config_file):
        """
        :param config_file:
        :return:
        """
        self.config_file = config_file
        self.is_embattled = False
        self.valid_embattle = True
        self._config_parser = ConfigParser.RawConfigParser()
        self._settings = global_settings()
        self._inspect_lock = threading.Lock()

        if not config_file:
            self.config_file = os.environ.get(ENV_CONFIG_FILE, None)

        if not self.config_file:
            log_bootstrap('Agent config file is not found, agent start failed.')
            self.valid_embattle = False

        log_bootstrap("get config file %s" % self.config_file)

    @staticmethod
    def singleton_instance(config_file):
        """one application according to name
        """
        instance = Embattle._instance

        if not instance:
            with Embattle._lock:
                instance = Embattle._instance
                if not instance:
                    instance = Embattle(config_file)
                    Embattle._instance = instance

        return instance

    def inspect_prerequisites(self):
        """ Do some prerequisite check for corps operation
        :return:
        """
        log_bootstrap("Inspecting config file %s" % self.config_file, close=True)

        if not self._config_parser.read(self.config_file):
            raise ConfigurationError("Unable to access the config file. %s", self.config_file)

        self._settings.config_file = self.config_file
        self.load_settings()
        self.load_settings('tingyun:exclude', "plugins")
        self.load_settings('tingyun:private', "port")
        self.load_settings('tingyun:private', "host")
        self.load_settings('tingyun:proxy', "proxy_host")
        self.load_settings('tingyun:proxy', "proxy_port")
        self.load_settings('tingyun:proxy', "proxy_user")
        self.load_settings('tingyun:proxy', "proxy_pwd")
        self.load_settings('tingyun:proxy', "proxy_scheme")

        # we can not access the log file and log level from the config parser. it maybe empty.
        initialize_logging(self._settings.log_file, self._settings.log_level)

    def load_settings(self, section='tingyun', option=None, method='get'):
        """ Load the specified settings from the ini config file
        :param section: ini parser section
        :param method: ini parser option operate method
        :return:
        """
        self._settings.config_file = self.config_file

        if option is None:
            self._process_setting(section, 'log_file', method, None)
            self._process_setting(section, 'log_level', method, map_log_level)
            self._process_setting(section, 'license_key', method, None)
            self._process_setting(section, 'enabled', method, map_key_words)
            self._process_setting(section, 'app_name', method, map_app_name)
            self._process_setting(section, 'audit_mode', method, map_key_words)
            self._process_setting(section, 'auto_action_naming', method, map_key_words)
            self._process_setting(section, 'ssl', method, map_key_words)
            self._process_setting(section, 'action_tracer.log_sql', method, map_key_words)
            self._process_setting(section, 'daemon_debug', method, map_key_words, True)
            self._process_setting(section, 'enable_profile', method, map_key_words)
            self._process_setting(section, 'urls_merge', method, map_key_words)
            self._process_setting(section, 'verify_certification', method, map_key_words)

            self._process_setting(section, 'tornado_wsgi_adapter_mode', method, map_key_words)
        else:
            self._process_setting(section, option, method, None, True)

    def _process_setting(self, section, option, method='get', mapper=None, hide=False):
        """ load the settings from config file to the settings objects instance.
        :param section: ini configure file section
        :param option: ini configure file option
        :param method: ini configure file operation method
        :param mapper: the method which mapping key value to the ini config option value
        :param hide: the option value error is can be ignored.
        :return: None
        """
        try:
            value = getattr(self._config_parser, method)(section, option)
            value = value if not mapper else mapper(value)

            # invalid value with mapper func mapping, used default instead
            if value is None:
                return

            target = self._settings
            fields = option.split('.', 1)

            while True:
                if len(fields) == 1:
                    setattr(target, fields[0], value)
                    break
                else:
                    target = getattr(target, fields[0])
                    fields = fields[1].split('.', 1)
        except ConfigParser.NoSectionError:
            if not hide:
                console.debug("No section[%s] in configure file", section)
        except ConfigParser.NoOptionError:
            if not hide:
                console.debug("No option[%s] in configure file", option)
        except Exception as err:
            console.warning("Process config error, section[%s]-option[%s] will use default value instead. %s", err)

    def detector(self, target_module, hook_module, function):
        """
        :param target_module:
        :param hook_module:
        :param function:
        :return:
        """
        def _detect(target_module):
            """
            """
            try:
                getattr(self.importer(hook_module), function)(target_module)
                console.info("Detect hooker %s for target module %s", hook_module, target_module)
            except Exception as _:
                console.warning("error occurred: %s" % traceback.format_exception(*sys.exc_info()))

        return _detect

    def importer(self, name):
        """
        :param name:
        :return:
        """
        __import__(name)
        return sys.modules[name]

    def activate_weapons(self):
        """
        :return:
        """
        exclude = self._settings.plugins
        for name, hooks in defined_repertoire().items():
            if name in exclude:
                console.debug("Ignore the plugin %s", name)
                continue
            for hook in hooks:
                target = hook.get('target', '')
                hook_func = hook.get('hook_func', '')
                hook_module = hook.get('hook_module', '')
                register_post_import_hook(self.detector(target, hook_module, hook_func), target)

    def execute(self):
        """
        :return:
        """
        if not self.valid_embattle:
            return False

        # has been for some prerequisite check for corps operation
        if self.is_embattled:
            console.warning("Agent was initialized before.")
            return False

        with self._inspect_lock:

            if self.is_embattled:
                console.warning('agent was initialized before, skip it now.')
                return False

            log_bootstrap("Stating init agent environment %s." % self._settings)
            self.is_embattled = True

            try:
                self.inspect_prerequisites()
                self.activate_weapons()
            except Exception as err:
                console.error("Errors. when initial the agent system. %s", err)
                return False

            return True


# This must the only entry for holding the corps's embattle
def take_control(config_file=None):
    """
    :param config_file: config file for the corps
    :return:
    """
    return Embattle.singleton_instance(config_file)
