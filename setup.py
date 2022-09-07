#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Setup MiAZ project.
# File: setup.py.
# Author: Tomás Vírseda
# License: GPL v3
# Description: setup.py tells you that the module/package you are about
# to install has been packaged and distributed with Distutils, which is
# the standard for distributing Python Modules.
"""

import os
import glob
from setuptools import setup

from MiAZ.env import ENV

#with open('pypi/README.rst', 'r') as f:
#    LONG_DESCRIPTION = f.read()


def add_data(root_data):
    """Add data files from a given directory."""
    dir_files = []
    resdirs = set()
    for root, dirs, files in os.walk(root_data):
        resdirs.add(os.path.realpath(root))

    resdirs.remove(os.path.realpath(root_data))

    for directory in resdirs:
        files = glob.glob(directory+'/*')
        relfiles = []
        for thisfile in files:
            if not os.path.isdir(thisfile):
                relfiles.append(os.path.relpath(thisfile))

        num_files = len(files)
        if num_files > 0:
            dir_files.append((os.path.relpath(directory), relfiles))

    return dir_files

#DATA_FILES =  ['VERSION']
DATA_FILES += add_data('MiAZ/data')

setup(
    name=ENV['APP']['shortname'],
    version=ENV['APP']['version'],
    author=ENV['APP']['author'],
    author_email=ENV['APP']['author_email'],
    url=ENV['APP']['website'],
    description='A static website generator based on Asciidoctor sources.',
    long_description=LONG_DESCRIPTION,
    download_url='https://github.com/t00m/KB4IT/archive/master.zip',
    license=ENV['APP']['license'],
    packages=['kb4it', 'kb4it.core', 'kb4it.services'],
    # distutils does not support install_requires, but pip needs it to be
    # able to automatically install dependencies
    install_requires=['mako==1.1.4'],
    include_package_data=True,
    data_files=DATA_FILES,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Documentation',
        'Topic :: Software Development :: Documentation',
        'Topic :: Utilities'
    ],
    entry_points={
        'console_scripts': [
            'kb4it = kb4it.core.main:main',
            ],
        },
)
