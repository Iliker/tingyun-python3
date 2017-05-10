from __future__ import print_function

""" Define army dispatch center for kinds of corps
"""

import sys
import os


class Dispatcher(object):
    """Define the commands dispatcher executor

    """
    def __init__(self, argv=None):
        """
        :return:
        """
        self.argv = argv or sys.argv[:]
        self.commands = {}

    def load_tingyun_entrypoint(self):
        """Load the entrypoint defined in setup
        :return:
        """
        try:
            import pkg_resources
        except ImportError:
            return

        for entrypoint in pkg_resources.iter_entry_points(group='tingyun.commander:launch_commanding_elevation'):
            __import__(entrypoint.module_name)

    def help_text(self, command=None):
        """The top level message from dispatcher
        :param command:  command instance
        :return:
        """
        if command is None:
            print("Support commands are:  ")

            for name, cmd in self.commands.iteritems():
                print("    %s %s" % (cmd.name, cmd.options))
        else:
            print("Command Usage:")
            print("    %s %s " % (command.name, command.options))
            print("       %s" % command.description)

    def _load_commands(self):
        """load the commands from the commands box.
        :return: the mapping of commands names with Command object
        """
        cmd_box = os.path.join(__path__[0], 'commands')
        try:
            commands = [f[:-3] for f in os.listdir(cmd_box) if not f.startswith('_') and f.endswith('.py')]
        except OSError:
            commands = []

        for cmd in commands:
            name = "tingyun.commander.commands.%s" % cmd
            __import__(name)
            self.commands[cmd] = sys.modules[name].Command()

    def execute(self):
        """
        :return:
        """
        self._load_commands()

        second_cmd = 'help'
        if len(self.argv) > 1:
            second_cmd = self.argv[1]

        second_cmd = "_".join(second_cmd.split("-"))
        if second_cmd == 'help' or second_cmd not in self.commands.keys():
            self.help_text()
            return

        try:
            self.commands[second_cmd].execute(self.argv[2:])
        except Exception as err:
            print(err)
            self.help_text(self.commands[second_cmd])


def launch_commanding_elevation():
    """ Define corps dispatch center entrance.
        Dispatch orders
    :return:
    """
    dsp = Dispatcher()
    dsp.load_tingyun_entrypoint()
    dsp.execute()
