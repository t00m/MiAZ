#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Environment module.

# File: env.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Environment variables module
"""

import os
from os.path import abspath
import sys
import tempfile
import multiprocessing

if sys.platform != 'linux':
    print("Your OS is not supported.")
    print("Please, use any recent GNU/Linux distribution")

ENV = {}

# Process
# ~ ENV['PS'] = {}
# ~ pid = os.getpid()
# ~ ENV['PS']['PID'] = os.getpid()
# ~ ENV['PS']['NAME'] = open('/proc/%d/comm' % pid, 'r').read().strip()

# Configuration
ENV['CONF'] = {}
ENV['CONF']['ROOT'] = abspath(sys.modules[__name__].__file__ + "/../..")
ENV['CONF']['USER_DIR'] = os.path.expanduser('~')
ENV['CONF']['TMPNAME'] = next(tempfile._get_candidate_names())
ENV['CONF']['MAX_WORKERS'] = multiprocessing.cpu_count()  # Avoid MemoryError

ENV['APP'] = {}
ENV['APP']['name'] = "My AZ Organizer"
ENV['APP']['shortname'] = "MiAZ"
ENV['APP']['description'] = "MyAZ is a personal document organizer"
ENV['APP']['license'] = 'GPL v3'
ENV['APP']['license_long'] = "The code is licensed under the terms of the  GPL v3\n\
        so you're free to grab, extend, improve and fork the \
        code\nas you want"
ENV['APP']['copyright'] = "Copyright \xa9 2022-2023 Tomás Vírseda"
ENV['APP']['author'] = 'Tomás Vírseda'
ENV['APP']['author_email'] = 'tomasvirseda@gmail.com'
ENV['APP']['documenters'] = ["Tomás Vírseda <tomasvirseda@gmail.com>"]
ENV['APP']['website'] = 'https://github.com/t00m/MiAZ'

# Local paths
ENV['LPATH'] = {}
ENV['LPATH']['ROOT'] = os.path.join(ENV['CONF']['USER_DIR'], ".%s" % ENV['APP']['shortname'].lower())
ENV['LPATH']['ETC'] = os.path.join(ENV['LPATH']['ROOT'], 'etc')
ENV['LPATH']['VAR'] = os.path.join(ENV['LPATH']['ROOT'], 'var')
ENV['LPATH']['WORK'] = os.path.join(ENV['LPATH']['VAR'], 'work')
ENV['LPATH']['DB'] = os.path.join(ENV['LPATH']['VAR'], 'db')
ENV['LPATH']['PLUGINS'] = os.path.join(ENV['LPATH']['VAR'], 'plugins')
ENV['LPATH']['LOG'] = os.path.join(ENV['LPATH']['VAR'], 'log')
ENV['LPATH']['TMP'] = os.path.join(ENV['LPATH']['VAR'], 'log')
ENV['LPATH']['OPT'] = os.path.join(ENV['LPATH']['ROOT'], 'opt')
ENV['LPATH']['THEMES'] = os.path.join(ENV['LPATH']['OPT'], 'themes')
ENV['LPATH']['TMP_SOURCE'] = os.path.join(ENV['LPATH']['TMP'], 'source')
ENV['LPATH']['TMP_TARGET'] = os.path.join(ENV['LPATH']['TMP'], 'target')
# ~ ENV['LPATH']['WWW'] = os.path.join(ENV['LPATH']['VAR'], 'www')
# ~ ENV['LPATH']['EXPORT'] = os.path.join(ENV['LPATH']['VAR'], 'export')
# ~ ENV['LPATH']['CACHE'] = os.path.join(ENV['LPATH']['VAR'], 'cache')
# ~ ENV['LPATH']['DISTRIBUTED'] = os.path.join(ENV['LPATH']['CACHE'], TMPNAME, 'distributed')
# ~ ENV['LPATH']['TMP'] = os.path.join(ENV['LPATH']['VAR'], 'tmp', TMPNAME)


# Global paths
ENV['GPATH'] = {}
ENV['GPATH']['ROOT'] = ENV['CONF']['ROOT']
ENV['GPATH']['DATA'] = os.path.join(ENV['GPATH']['ROOT'], 'data')
ENV['GPATH']['DOCS'] = os.path.join(ENV['GPATH']['DATA'], 'docs')
ENV['GPATH']['ICONS'] = os.path.join(ENV['GPATH']['DATA'], 'icons')
ENV['GPATH']['RESOURCES'] = os.path.join(ENV['GPATH']['DATA'], 'resources')
ENV['GPATH']['ONLINE'] = os.path.join(ENV['GPATH']['RESOURCES'], 'online')
ENV['GPATH']['IMAGES'] = os.path.join(ENV['GPATH']['ONLINE'], 'images')
ENV['GPATH']['COMMON'] = os.path.join(ENV['GPATH']['RESOURCES'], 'common')
ENV['GPATH']['TEMPLATES'] = os.path.join(ENV['GPATH']['COMMON'], 'templates')
ENV['GPATH']['THEMES'] = os.path.join(ENV['GPATH']['RESOURCES'], 'themes')
ENV['GPATH']['APPDATA'] = os.path.join(ENV['GPATH']['COMMON'], 'appdata')
ENV['GPATH']['RES'] = os.path.join(ENV['GPATH']['DATA'], 'res')

ENV['FILE'] = {}
ENV['FILE']['CONF'] = os.path.join(ENV['LPATH']['ETC'], 'MyAZ.conf')
ENV['FILE']['VERSION'] = os.path.join(ENV['GPATH']['DOCS'], 'VERSION')
ENV['FILE']['APPICON'] = os.path.join(ENV['GPATH']['ICONS'], 'MiAZ.svg')


# App Info
ENV['APP']['version'] = open(ENV['FILE']['VERSION']).read().strip()

ENV['SYS'] = {}
try:
    ENV['SYS']['DESKTOP'] = os.environ['XDG_SESSION_DESKTOP']
except KeyError:
    ENV['SYS']['DESKTOP'] = None
