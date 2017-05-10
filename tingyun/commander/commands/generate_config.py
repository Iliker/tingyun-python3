from __future__ import print_function

import os
from tingyun.logistics.exceptions import CommandlineParametersException


class Command(object):
    """
    """
    def __init__(self):
        """
        """
        self.name = "generate-config"  # order format with commandline
        self.options = '[license_key] filename'
        self.description = "Generate the config file with license(optional) with filename"

    def execute(self, args):
        """generate default configuration to specified path.
        :param args:
        :return:
        """
        if len(args) < 1:
            raise CommandlineParametersException()

        from tingyun import __file__ as package_root

        package_root = os.path.dirname(package_root)
        config_file = os.path.join(package_root, 'tingyun.ini')
        default_config = open(config_file, 'r')
        content = default_config.read()

        if 2 == len(args):
            output_file = open(args[1], "w")
        else:
            output_file = open(args[0], "w")

        if 2 == len(args):
            content = content.replace('** YOUR-LICENSE-KEY **', args[0])
            print("""
                        ================ Messages ==============
                  You use license key: %s, to generate config file: %s
                  """ % (args[0], args[1]))
        elif 1 == len(args):
            print("""
                        ================ Messages ==============
                  You use license key: , to generate config file: %s.
                  Before you use the python agent, you should type the license key into config file
                  """ % args[0])

        output_file.write(content)
        output_file.close()
        default_config.close()
