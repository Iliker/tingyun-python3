from __future__ import print_function
import os

from tingyun.config.settings import global_settings
from tingyun.logistics.mapper import ENV_CONFIG_FILE, CONFIG_ITEM
from tingyun.logistics.exceptions import CommandlineParametersException

try:
    import ConfigParser  # for python2.x
except ImportError:
    import configparser as ConfigParser  # for python3.x

_config_parser = ConfigParser.RawConfigParser()


class Command(object):
    """
    """
    def __init__(self):
        """
        """
        self.name = "check-config"  # order format with commandline
        self.options = '[filename]'
        self.description = "Default point to environment %s" % ENV_CONFIG_FILE

    def internal_tips(self, msgs, level="Errors"):
        """
        :return:
        """
        print("----------------------%s------------------------" % level)
        for msg in msgs:
            print("  %s\n" % msg)

        print("----------------------End---------------------------\n")

    def execute(self, args):
        """
        :param args:
        :return:
        """
        errors = []
        warnings = []
        config_file = os.environ.get(ENV_CONFIG_FILE, "")

        if (len(args) > 0) and len(args) != 1:
            raise CommandlineParametersException()

        if 1 == len(args):
            config_file = args[0]

        env_msg = ''
        if 0 == len(args):
            env_msg = "please set the environment variable(%s) for agent config file." % ENV_CONFIG_FILE

        if not os.path.exists(config_file):
            errors.append("Config file is not specified. Or " + env_msg)
            self.internal_tips(errors)
            raise CommandlineParametersException()

        if not _config_parser.read(config_file):
            errors.append("Errors: unable to read the config file. please check the file permission.")
            self.internal_tips(errors)
            raise CommandlineParametersException()

        # check the config detail.
        print("Use config file: %s" % config_file)
        default_settings = global_settings()
        multi_attr = {"action_tracer.log_sql": default_settings.action_tracer.log_sql}
        for item in CONFIG_ITEM:
            ret = self._process_setting(item["section"], item["key"], 'get', item["mapper"])
            if ret[0] < 0:
                errors.append(ret[2])
                break

            if 0 == ret[0] and 'log_file' != item["key"] and 'license_key' != item["key"]:
                if item["key"] in multi_attr:
                    v = multi_attr[item["key"]]
                else:
                    v = getattr(default_settings, item["key"]) if 'log_level' != item["key"] else "logging.DEBUG"
                warnings.append(ret[2] + " Use default value [%s] instead." % v)
                continue

            if 'log_file' == item["key"] and not ret[1]:
                warnings.append("config option <log_file> is not defined, agent log will output to stderr.")
                continue

            if 'log_file' == item["key"] and ret[1]:
                try:
                    with open(ret[1], "a+") as fd:
                        fd.write("agent check log file config input message.\n")
                except Exception as _:
                    warnings.append("Current user[%s] not allowed to access the log file[%s]."
                                    % (os.environ["USER"], ret[1]))

            if 'license_key' == item["key"] and not ret[1]:
                errors.append("config option <license_key> is not defined, agent will not work well.")
                continue

        if warnings:
            self.internal_tips(warnings, "Warning")

        if errors:
            self.internal_tips(errors)
            raise CommandlineParametersException()

        if not errors:
            print("\nValidate agent config file success!!")

    def _process_setting(self, section, option, getter='get', mapper=None):
        """
        Return: [errorCode, value, errMsg]

        """
        try:
            map_value = ""
            value = getattr(_config_parser, getter)(section, option)
            if mapper:
                    map_value = mapper(value)

            # use the default value in settings
            if map_value is None:
                return [0, None, "%s=%s, %s is not supported." % (option, value, value)]

            return [1, value, ""]

        except ConfigParser.NoSectionError:
            return [-1, None, "Section [%s] is not specified." % section]
        except ConfigParser.NoOptionError:
            return [0, None, "Option <%s> is not exist." % option]
        except Exception as err:
            return [-1, None, err]
