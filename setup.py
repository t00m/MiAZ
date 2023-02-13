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

from MiAZ.backend.env import ENV

with open('README.adoc', 'r') as f:
    LONG_DESCRIPTION = f.read()


def add_data(root_data):
    """Add data files from a given directory."""
    dir_files = []
    resdirs = set()
    for root, dirs, files in os.walk(root_data):
        resdirs.add(os.path.realpath(root))

    resdirs.remove(os.path.realpath(root_data))

    for directory in resdirs:
        files = glob.glob(os.path.join(directory, '*'))
        relfiles = []
        for thisfile in files:
            if not os.path.isdir(thisfile):
                relfiles.append(os.path.relpath(thisfile))

        num_files = len(files)
        if num_files > 0:
            dir_files.append((os.path.relpath(directory), relfiles))

    return dir_files

DATA_FILES = add_data('MiAZ/data')
DATA_FILES += ['README.adoc']

setup(
    name=ENV['APP']['shortname'],
    version=open('MiAZ/data/docs/VERSION', 'r').read().strip(),
    author=ENV['APP']['author'],
    author_email=ENV['APP']['author_email'],
    url=ENV['APP']['website'],
    description='A personal document organizer',
    long_description=LONG_DESCRIPTION,
    download_url='https://github.com/t00m/MiAZ/archive/master.zip',
    license=ENV['APP']['license'],
    packages=[
                'MiAZ',
                'MiAZ.backend',
                'MiAZ.frontend',
                'MiAZ.frontend.console',
                'MiAZ.frontend.desktop',
                'MiAZ.frontend.desktop.widgets'
            ],
    # distutils does not support install_requires, but pip needs it to be
    # able to automatically install dependencies
    install_requires=[],
    include_package_data=True,
    data_files=DATA_FILES,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: X11 Applications :: GTK',
        'Environment :: X11 Applications :: Gnome',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Documentation',
        'Topic :: Utilities',
        'Topic :: Desktop Environment :: Gnome',
        'Topic :: Office/Business'
    ],
    entry_points={
        'console_scripts': [
            'miaz = MiAZ.main:main',
            ],
        },
)
