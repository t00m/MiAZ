#!/usr/bin/python3

"""
# File: setup.py.
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup MiAZ project
"""

import os
import glob
import subprocess
from setuptools import setup

cmd_version = 'meson introspect meson.build --projectinfo | jq .version'
o, e = subprocess.Popen([cmd_version], shell=True, stdout=subprocess.PIPE).communicate()
VERSION = o.decode('utf-8').strip().replace('"', '')

with open('data/docs/README', 'r') as f:
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

# ~ DATA_FILES = [('share/MiAZ', add_data('data/resources'))]
DATA_FILES = []
resources = add_data('data/resources')
for node in resources:
    datadir, datafiles = node
    for datafile in datafiles:
        finaldir = os.path.join('share', 'MiAZ', datadir)
        DATA_FILES +=[(finaldir, [datafile])]
# ~ DATA_FILES += ['README.adoc']
DATA_FILES +=[('share/doc/MiAZ', ['data/docs/README'])]
DATA_FILES +=[('share/applications', ['data/resources/com.github.t00m.MiAZ.desktop'])]
DATA_FILES +=[('share/icons/hicolor/48x48/apps/', ['data/resources/icons/scalable/com.github.t00m.MiAZ.svg'])]

setup(
    name='MiAZ',
    version=VERSION,
    author='Tomás Vírseda',
    author_email='tomasvirseda@gmail.com',
    url='https://github.com/t00m/MiAZ',
    description='A personal document organizer',
    long_description=LONG_DESCRIPTION,
    download_url='https://github.com/t00m/MiAZ/archive/master.zip',
    license='GPL v3 or later',
    packages=[
                'MiAZ',
                'MiAZ.backend',
                'MiAZ.frontend',
                'MiAZ.frontend.console',
                'MiAZ.frontend.desktop',
                'MiAZ.frontend.desktop.widgets',
                'MiAZ.frontend.desktop.services'
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
            'miaz = MiAZ.miaz:main',
            ],
        },
)
