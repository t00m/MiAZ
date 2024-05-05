#!@PYTHON@

# Copyright 2024 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from os.path import abspath
import sys
import signal
import locale
import gettext
import argparse
import tempfile
import multiprocessing

sys.path.insert(1, '@pkgdatadir@')

from MiAZ.backend.log import get_logger
from MiAZ.backend.util import which

log = get_logger('MiAZ')

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

# App
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
ENV['GPATH']['DATA'] = os.path.join(ENV['GPATH']['ROOT'], 'resources')
ENV['GPATH']['DOCS'] = os.path.join(ENV['GPATH']['DATA'], 'docs')
ENV['GPATH']['ICONS'] = os.path.join(ENV['GPATH']['DATA'], 'icons', 'scalable')
ENV['GPATH']['FLAGS'] = os.path.join(ENV['GPATH']['ICONS'], 'flags')
ENV['GPATH']['LOCALE'] = os.path.join(ENV['GPATH']['DATA'], 'po')
ENV['GPATH']['PLUGINS'] = os.path.join(ENV['GPATH']['DATA'], 'plugins')
ENV['GPATH']['CONF'] = os.path.join(ENV['GPATH']['DATA'], 'conf')

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


class MiAZ:
    def __init__(self, ENV: dict) -> None:
        self.env = ENV
        self.setup_environment()
        self.log = get_logger('MiAZ')
        self.set_internationalization()
        self.log.info("%s v%s - Start", ENV['APP']['shortname'], ENV['APP']['VERSION'])

    def setup_environment(self):
        """Setup MiAZ user environment"""
        ENV = self.env
        for entry in ENV['LPATH']:
            if not os.path.exists(ENV['LPATH'][entry]):
                os.makedirs(ENV['LPATH'][entry])

    def set_internationalization(self):
        """Sets application internationalization."""
        ENV = self.env
        try:
            locale.bindtextdomain('miaz', ENV['GPATH']['LOCALE'])
            locale.textdomain('miaz')
            # ~ self.log.debug("Gettext: binding to %s", ENV['GPATH']['LOCALE'])
            gettext.bindtextdomain('miaz', ENV['GPATH']['LOCALE'])
            gettext.textdomain('miaz')
        except AttributeError as e:
            # Python built without gettext support does not have
            # bindtextdomain() and textdomain().
            self.log.error(
                "Could not bind the gettext translation domain. Some"
                " translations will not work. Error:\n{}".format(e))

    def run(self):
        """Execute MiAZ in desktop or console mode"""
        ENV = self.env
        if ENV['DESKTOP']['ENABLED']:
            from MiAZ.frontend.desktop.app import MiAZApp
        else:
            from MiAZ.frontend.console.app import MiAZApp
        app = MiAZApp(application_id=ENV['APP']['ID'])
        app.set_env(ENV)
        try:
            app.run()
        except KeyboardInterrupt:
            self.log.error("Application killed by user")
            exit(0)
        self.log.info("%s v%s - End", ENV['APP']['shortname'], ENV['APP']['VERSION'])

def main():
    """This is the entry point when the program is installed via PIP"""
    log.debug("MiAZ installation done via PIP")
    miaz_exec = which('miaz')
    if miaz_exec is None:
        log.error("Are you sure that MiAZ has been installed correctly?")
        log.error("MiAZ executable not found in $PATH")
    miaz_dir = os.path.dirname(miaz_exec)
    ROOT = os.path.abspath(miaz_dir+'/..')
    ENV['APP']['ID'] = 'com.github.t00m.MiAZ'
    ENV['APP']['VERSION'] = '0.0.21'
    ENV['APP']['PGKDATADIR'] = os.path.join(ROOT, 'share/MiAZ/data')
    ENV['APP']['LOCALEDIR'] = os.path.join(ROOT, 'share/MiAZ/locale')
    ENV['CONF']['ROOT'] = ENV['APP']['PGKDATADIR']

    # Global paths
    ENV['GPATH'] = {}
    ENV['GPATH']['ROOT'] = ENV['CONF']['ROOT']
    ENV['GPATH']['DATA'] = os.path.join(ENV['GPATH']['ROOT'], 'resources')
    ENV['GPATH']['DOCS'] = os.path.join(ENV['GPATH']['DATA'], 'docs')
    ENV['GPATH']['ICONS'] = os.path.join(ENV['GPATH']['DATA'], 'icons', 'scalable')
    ENV['GPATH']['FLAGS'] = os.path.join(ENV['GPATH']['ICONS'], 'flags')
    ENV['GPATH']['LOCALE'] = os.path.join(ENV['GPATH']['DATA'], 'po')
    ENV['GPATH']['PLUGINS'] = os.path.join(ENV['GPATH']['DATA'], 'plugins')
    ENV['GPATH']['CONF'] = os.path.join(ENV['GPATH']['DATA'], 'conf')

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
    extra_usage = """"""
    parser = argparse.ArgumentParser(
        prog='MiAZ',
        description='Personal Document Organizer',
        epilog=extra_usage,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # MiAZ arguments
    miaz_options = parser.add_argument_group('MiAZ Options')
    miaz_options.add_argument('-v', '--version', help='Show current version', action='version', version='%s %s' % (ENV['APP']['shortname'], ENV['APP']['VERSION']))

    params = parser.parse_args()
    app = MiAZ(ENV)
    app.run()

if __name__ == "__main__":
    """This is the entry point when the program is installed via Meson"""
    log.debug("MiAZ installation done via Meson")
    extra_usage = """"""
    parser = argparse.ArgumentParser(
        prog='MiAZ',
        description='Personal Document Organizer',
        epilog=extra_usage,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # MiAZ arguments
    miaz_options = parser.add_argument_group('MiAZ Options')
    miaz_options.add_argument('-v', '--version', help='Show current version', action='version', version='%s %s' % (ENV['APP']['shortname'], ENV['APP']['VERSION']))

    params = parser.parse_args()
    app = MiAZ(ENV)
    app.run()
