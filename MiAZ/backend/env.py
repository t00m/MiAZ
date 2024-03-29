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
from gettext import gettext as _

ENV = {}

# Desktop environment
ENV['DESKTOP'] = {}
try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
    ENV['DESKTOP']['GTK_ENABLED'] = True
    ENV['DESKTOP']['GTK_VERSION'] = (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION)
    ENV['DESKTOP']['GTK_SUPPORT'] = Gtk.MAJOR_VERSION >= 4 and Gtk.MINOR_VERSION >= 6
except:
    ENV['DESKTOP']['GTK_ENABLED'] = False
    ENV['DESKTOP']['GTK_SUPPORT'] = False

ENV['DESKTOP']['ENABLED'] = ENV['DESKTOP']['GTK_SUPPORT']

# Configuration
ENV['CONF'] = {}
ENV['CONF']['ROOT'] = abspath(sys.modules[__name__].__file__ + "/../..")
ENV['CONF']['USER_DIR'] = os.path.expanduser('~')

# Application
ENV['APP'] = {}
ENV['APP']['name'] = _('AZ Organizer')
ENV['APP']['shortname'] = 'MiAZ'
ENV['APP']['description'] = _('Personal Document Organizer')
ENV['APP']['license'] = 'GPL v3'
ENV['APP']['license_long'] = _("The code is licensed under the terms of the  GPL v3\nso you're free to grab, extend, improve and fork the code as you want")
ENV['APP']['copyright'] = 'Copyright \xa9 2022-2023 Tomás Vírseda'
ENV['APP']['author'] = 'Tomás Vírseda'
ENV['APP']['author_email'] = 'tomasvirseda@gmail.com'
ENV['APP']['documenters'] = ["Tomás Vírseda <tomasvirseda@gmail.com>"]
ENV['APP']['website'] = 'https://github.com/t00m/MiAZ'
ENV['APP']['ID'] = 'com.github.t00m.MiAZ'

# Local paths
ENV['LPATH'] = {}
ENV['LPATH']['ROOT'] = os.path.join(ENV['CONF']['USER_DIR'], ".%s" % ENV['APP']['shortname'])
ENV['LPATH']['ETC'] = os.path.join(ENV['LPATH']['ROOT'], 'etc')
ENV['LPATH']['REPOS'] = os.path.join(ENV['LPATH']['ETC'], 'repos')
ENV['LPATH']['VAR'] = os.path.join(ENV['LPATH']['ROOT'], 'var')
ENV['LPATH']['DB'] = os.path.join(ENV['LPATH']['VAR'], 'db')
ENV['LPATH']['CACHE'] = os.path.join(ENV['LPATH']['VAR'], 'cache')
ENV['LPATH']['LOG'] = os.path.join(ENV['LPATH']['VAR'], 'log')
ENV['LPATH']['TMP'] = os.path.join(ENV['LPATH']['VAR'], 'tmp')
ENV['LPATH']['REPO'] = os.path.join(ENV['LPATH']['TMP'], 'repo')
ENV['LPATH']['OPT'] = os.path.join(ENV['LPATH']['ROOT'], 'opt')
ENV['LPATH']['PLUGINS'] = os.path.join(ENV['LPATH']['OPT'], 'plugins')

# Global paths
ENV['GPATH'] = {}
ENV['GPATH']['ROOT'] = ENV['CONF']['ROOT']
ENV['GPATH']['DATA'] = os.path.join(ENV['GPATH']['ROOT'], 'data')
ENV['GPATH']['DOCS'] = os.path.join(ENV['GPATH']['DATA'], 'docs')
ENV['GPATH']['ICONS'] = os.path.join(ENV['GPATH']['DATA'], 'icons')
ENV['GPATH']['FLAGS'] = os.path.join(ENV['GPATH']['ICONS'], 'flags')
ENV['GPATH']['LOCALE'] = os.path.join(ENV['GPATH']['DATA'], 'po')
ENV['GPATH']['PLUGINS'] = os.path.join(ENV['GPATH']['DATA'], 'plugins')
ENV['GPATH']['RESOURCES'] = os.path.join(ENV['GPATH']['DATA'], 'resources')

# Common file paths
ENV['FILE'] = {}
ENV['FILE']['CONF'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-application.json')
ENV['FILE']['VERSION'] = os.path.join(ENV['GPATH']['DOCS'], 'VERSION')
ENV['FILE']['APPICON'] = os.path.join(ENV['GPATH']['ICONS'], 'MiAZ.svg')
ENV['FILE']['LOG'] = os.path.join(ENV['LPATH']['LOG'], 'MiAZ.log')
ENV['FILE']['GROUPS'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-groups.json')
ENV['FILE']['PURPOSES'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-purposes.json')
ENV['FILE']['CONCEPTS'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-concepts.json')
ENV['FILE']['PEOPLE'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-people.json')
ENV['FILE']['EXTENSIONS'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-extensions.json')
ENV['FILE']['COUNTRIES'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-countries.json')
ENV['FILE']['WHO'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-who.json')

# App Info
ENV['APP']['version'] = open(ENV['FILE']['VERSION']).read().strip()

ENV['SYS'] = {}
try:
    ENV['SYS']['DESKTOP'] = os.environ['XDG_SESSION_DESKTOP']
except KeyError:
    ENV['SYS']['DESKTOP'] = None
