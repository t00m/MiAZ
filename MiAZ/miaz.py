#!@PYTHON@

# Copyright 2024 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from os.path import abspath
import sys
import pprint
import signal
import locale
import gettext
import argparse
import tempfile
import multiprocessing

from rich.traceback import install
# ~ install(show_locals=True)

sys.path.insert(1, '@pkgdatadir@')

ENV = {}
ENV['APP'] = {}
ENV['APP']['ID'] = '@APP_ID@'
ENV['APP']['VERSION'] = '@VERSION@'
ENV['APP']['PGKDATADIR'] = '@pkgdatadir@'
ENV['APP']['LOCALEDIR'] = '@localedir@'
ENV['APP']['name'] = "AZ Organizer"
ENV['APP']['shortname'] = "MiAZ"
ENV['APP']['description'] = "Personal Document Organizer"
ENV['APP']['license'] = 'GPL v3'
ENV['APP']['license_long'] = "The code is licensed under the terms of the  GPL v3\n\
                  so you're free to grab, extend, improve and fork the \
                  code\nas you want"
ENV['APP']['copyright'] = "Copyright \xa9 2019 Tomás Vírseda"
ENV['APP']['author'] = 'Tomás Vírseda'
ENV['APP']['author_email'] = 'tomasvirseda@gmail.com'
ENV['APP']['documenters'] = ["Tomás Vírseda <tomasvirseda@gmail.com>"]
ENV['APP']['website'] = 'https://github.com/t00m/MiAZ'

# Process
PID = os.getpid()
ENV['PS'] = {}
ENV['PS']['PID'] = PID
ENV['PS']['NAME'] = open('/proc/%d/comm' % PID, 'r').read().strip()

# Configuration
ENV['CONF'] = {}
ENV['CONF']['ROOT'] = ENV['APP']['PGKDATADIR']
ENV['CONF']['USER_DIR'] = os.path.expanduser('~')

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

signal.signal(signal.SIGINT, signal.SIG_DFL)
gettext.install('miaz', ENV['APP']['LOCALEDIR'])

try:
  locale.bindtextdomain('miaz', ENV['APP']['LOCALEDIR'])
  locale.textdomain('miaz')
except:
  log.error('Cannot set locale.')

try:
  gettext.bindtextdomain('miaz', ENV['APP']['LOCALEDIR'])
  gettext.textdomain('miaz')
except:
  log.error('Cannot load translations.')


if __name__ == "__main__":
    from MiAZ.main import main
    main(ENV)
