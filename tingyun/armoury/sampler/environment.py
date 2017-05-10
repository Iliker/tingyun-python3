"""This module provides functions to collect information about the operating system, Python and hosting environment.

"""

import os
import sys
import platform
from tingyun.armoury.sampler.system_info import cpu_count, memory_total, cpu_info

try:
    import pkg_resources
except ImportError:
    pass


def env_config():
    """
    :return: env, a dict of environment
    """
    env = dict()

    # system information
    env["OS Arch"] = platform.machine()
    env["kernel"] = platform.release()
    env["CPU Cores"] = cpu_count()
    env["Physical Memory"] = "%sMB" % memory_total()
    env["OS Version"] = platform.version()

    # python information
    env["Python Program Name"] = sys.argv[0]
    env["Python Executable"] = sys.executable

    env["Python Home"] = os.environ.get('PYTHONHOME', '')
    env["Python Path"] = os.environ.get('PYTHONPATH', '')

    env["Python Prefix"] = sys.prefix
    env["Python Exec Prefix"] = sys.exec_prefix

    env["Python Version"] = sys.version
    env["Python Platform"] = sys.platform
    env["Python Implementation"] = platform.python_implementation()  # new in python2.6
    env["Python Version"] = platform.python_version()

    env["Python Max Unicode"] = sys.maxunicode
    env["CPU Vendor"], env["CPU Model"], env["CPU mhz"] = cpu_info()

    # Dispatcher information.
    dispatcher = {}
    if not dispatcher and 'mod_wsgi' in sys.modules:
        mod_wsgi = sys.modules['mod_wsgi']
        if hasattr(mod_wsgi, 'process_group'):
            if mod_wsgi.process_group == '':
                dispatcher["Dispatcher"] = 'Apache/mod_wsgi (embedded)'
            else:
                dispatcher["Dispatcher"] = 'Apache/mod_wsgi (daemon)'
        else:
            dispatcher["Dispatcher"] = 'Apache/mod_wsgi'

        if hasattr(mod_wsgi, 'version'):
            dispatcher["Dispatcher Version"] = str(mod_wsgi.version)

    if not dispatcher and 'uwsgi' in sys.modules:
        dispatcher["Dispatcher"] = 'uWSGI'
        uwsgi = sys.modules['uwsgi']

        if hasattr(uwsgi, 'version'):
            dispatcher["Dispatcher Version"] = uwsgi.version

    env.update(dispatcher)

    plugins = []
    tingyun = []

    # Do NOT use six module for the following iteration.
    for name, module in list(sys.modules.items()):
        if name.startswith('tingyun.hooks'):
            tingyun.append("%s." % name)

        elif name.find('.') == -1 and hasattr(module, '__file__'):
            try:
                if 'pkg_resources' in sys.modules:
                    version = pkg_resources.get_distribution(name).version
                    if version:
                        name = '%s(%s).' % (name, version)
            except Exception as _:
                name = '%s.' % name

            plugins.append(name)

    tingyun.extend(plugins)
    env['Plugin List'] = ','.join(tingyun)

    return env


if __name__ == "__main__":
    print("self test: %s" % env_config())
