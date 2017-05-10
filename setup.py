# -*- coding: utf-8 -*-
from __future__ import print_function

with_setuptools = False

try:
    from setuptools import setup
    with_setuptools = True
except ImportError:
    from distutils.core import setup

from distutils.core import Extension
from distutils.command.build_ext import build_ext
from distutils.errors import (CCompilerError, DistutilsExecError, DistutilsPlatformError)

import os
import sys

version = __import__('tingyun').get_version()
_copyright = '(C) Copyright 2007-2017 networkbench Inc. All rights reserved.'
packages, package_data = [], {}
root_dir = os.path.dirname(__file__)
tingyun_dir = 'tingyun'
if root_dir != '':
    os.chdir(root_dir)


def split(dir_path, result=None):
    """
    """
    if result is None:
        result = []
    head, tail = os.path.split(dir_path)
    if head == '':
        return [tail] + result
    if head == dir_path:
        return result
    return split(head, [tail] + result)


def process_packages():
    """collect the packages info into package_data
    :return:
    """
    for dir_path, dir_name, file_name in os.walk(tingyun_dir):
        dir_name[:] = [d for d in dir_name if not d.startswith('.') and d != '__pycache__']
        parts = split(dir_path)
        package_name = '.'.join(parts)
        if '__init__.py' in file_name:
            packages.append(package_name)
        elif file_name:
            relative_path = []
            while '.'.join(parts) not in packages:
                relative_path.append(parts.pop())
            relative_path.reverse()
            path = os.path.join(*relative_path)
            package_files = package_data.setdefault('.'.join(parts), [])
            package_files.extend([os.path.join(path, f) for f in file_name])


# package the setup data for build python package
process_packages()
kwargs = dict(
    name="tingyun-agent-python",
    version=version,
    description="Python application performance monitor client,It's main usage is working with python web application.",
    long_description="Application performance monitor client, which is base on tingyun platform. Agent can monitor "
                     "python web framework/modules performance, such as Django, Tornado, database, external call etc."
                     "In the premise of using less resources, our agent can achieve a variety of module tracking.",
    author="tingyun.com",
    author_email="python@tingyun.com ",
    license=_copyright,
    platforms=['unix', 'linux', 'MacOS'],
    url="http://www.tingyun.com",
    packages=packages,
    package_data={'tingyun': ['tingyun.ini', 'tingyun/tingyun.ini', 'LICENSE', 'packages/requests/cacert.pem']},
    scripts=['scripts/tingyun-admin'],
    classifiers=[
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
    ],
)

if with_setuptools:
    kwargs['entry_points'] = {'console_scripts': ['tingyun-admin = tingyun.commander:launch_commanding_elevation']}

if sys.platform == 'win32':
    build_ext_errors = (CCompilerError, DistutilsExecError,  DistutilsPlatformError, IOError)
else:
    build_ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)


class BuildExtFailed(Exception):
    pass


class TinYunBuildExtension(build_ext):
    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildExtFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except build_ext_errors:
            raise BuildExtFailed()


def _run_setup(with_extension):
    """
    :param with_extension:
    :return:
    """
    setup_kwargs = dict(kwargs)

    if with_extension:
        setup_kwargs['ext_modules'] = [
            Extension("tingyun.packages.wrapt._wrappers", ["tingyun/packages/wrapt/_wrappers.c"])
        ]

    setup_kwargs['cmdclass'] = dict(build_ext=TinYunBuildExtension)
    setup(**setup_kwargs)


def do_run_setup_install():
    """
    :return:
    """
    with_extensions = True

    # skip the pypy.
    if hasattr(sys, 'pypy_version_info'):
        with_extensions = False
        print('========================================================')

    try:
        _run_setup(with_extensions)
    except Exception as _:
        print(80 * '*')

        print("""
                                  =========================================
                                               WARNING
                                  =========================================
                The optional C extension components of the Python agent could not be compiled.
              Maybe the C compiler is not installed on the system。 The Python agent will be installed without
              the C extensions. ."""
        )

        print("INFO: Trying to build without extensions.")
        print(80 * '*')

        _run_setup(with_extension=False)
        print(80 * '*')
        print("INFO: Only pure Python agent was installed.")

        print(80 * '*')

# Actually run the setup for agent.
do_run_setup_install()
