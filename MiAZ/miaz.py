#!@PYTHON@

# Copyright 2019-2025 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import json
import argparse
import signal
import locale
import gettext
import subprocess

sys.path.insert(1, '@pkgdatadir@')

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.util import which

log = MiAZLog('MiAZ')

# Check Desktop environment
ENV['DESKTOP'] = {}
try:
    import gi
except:
    sys.exit("No support for Python GObject")

try:
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk
    from gi.repository import GLib
    ENV['DESKTOP']['GTK_VERSION'] = (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION)
    ENV['DESKTOP']['GTK_SUPPORT'] = Gtk.MAJOR_VERSION >= 4 and Gtk.MINOR_VERSION >= 6
except (ValueError, ModuleNotFoundError):
    ENV['DESKTOP']['GTK_SUPPORT'] = False

try:
    gi.require_version('Adw', '1')
    from gi.repository import Adw
    ENV['DESKTOP']['ADW_VERSION'] = (Adw.MAJOR_VERSION, Adw.MINOR_VERSION, Adw.MICRO_VERSION)
    ENV['DESKTOP']['ADW_SUPPORT'] = Adw.MAJOR_VERSION >= 1 and Adw.MINOR_VERSION >= 6
except (ValueError, ModuleNotFoundError):
    ENV['DESKTOP']['ADW_SUPPORT'] = False


ENV['DESKTOP']['ENABLED'] = ENV['DESKTOP']['GTK_SUPPORT'] and ENV['DESKTOP']['ADW_SUPPORT']
log.debug(f"GTK available ({Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION})")
log.debug(f"ADW available ({Adw.MAJOR_VERSION}.{Adw.MINOR_VERSION}.{Adw.MICRO_VERSION})")
log.debug(f"Desktop enabled? {ENV['DESKTOP']['ENABLED']}")
if not ENV['DESKTOP']['ENABLED']:
    log.error("Desktop dependencies not met to run this app")
    log.error("Make sure that Gtk version is >= 4.6 and Adw is >= 1.6")
    sys.exit(-1)


signal.signal(signal.SIGINT, signal.SIG_DFL)
gettext.install('miaz', ENV['APP']['LOCALEDIR'])

try:
    locale.bindtextdomain('miaz', ENV['APP']['LOCALEDIR'])
    locale.textdomain('miaz')
except Exception:
    log.error('Cannot set locale.')

try:
    gettext.bindtextdomain('miaz', ENV['APP']['LOCALEDIR'])
    gettext.textdomain('miaz')
except Exception:
    log.error('Cannot load translations.')


ENV['APP']['RUNTIME']['EXEC'] = os.path.abspath(__file__)


class MiAZ:
    """MiAZ Entry point class."""

    def __init__(self, ENV: dict) -> None:
        """Set up environment and run the application."""
        self.env = ENV
        log.debug("MiAZ Environment variables:")
        for section in self.env:
            log.debug(f"\t[{section}]")
            for envvar in self.env[section]:
                log.debug(f"\t\t{envvar} = {self.env[section][envvar]}")
        self.setup_environment()
        self.log = MiAZLog('MiAZ')
        self.set_internationalization()
        self.log.info(f"{ENV['APP']['shortname']} v{ENV['APP']['VERSION']} - Start")

    def setup_environment(self):
        """Set up MiAZ user environment."""
        ENV = self.env
        for entry in ENV['LPATH']:
            if not os.path.exists(ENV['LPATH'][entry]):
                os.makedirs(ENV['LPATH'][entry])

    def set_internationalization(self):
        """Set application internationalization."""
        ENV = self.env
        try:
            locale.bindtextdomain('miaz', ENV['GPATH']['LOCALE'])
            locale.textdomain('miaz')
            gettext.bindtextdomain('miaz', ENV['GPATH']['LOCALE'])
            gettext.textdomain('miaz')
        except AttributeError as e:
            # Python built without gettext support does not have
            # bindtextdomain() and textdomain().
            self.log.error(f"{e}")
            self.log.error("Could not bind the gettext translation domain")

    def run(self, params):
        """Execute MiAZ in desktop or console mode."""
        self.log.info(f"Params: {params}")
        ENV = self.env
        if ENV['DESKTOP']['ENABLED']:
            from MiAZ.frontend.desktop.app import MiAZApp
        else:
            from MiAZ.frontend.console.app import MiAZApp
        app = MiAZApp(application_id=ENV['APP']['ID'])
        app.set_env(ENV)

        # Set up the signal handler for CONTROL-C
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.exit)

        try:
            app.run()
        except KeyboardInterrupt:
            self.log.error("Application killed by user")
            sys.exit(0)
        self.log.info(f"{ENV['APP']['shortname']} v{ENV['APP']['VERSION']} - End")

def parse_arguments():
    parser = argparse.ArgumentParser(description=ENV['APP']['description'])
    parser.add_argument('--version', action='version', version=ENV['APP']['VERSION'], help='Show version number and exit.')
    return parser.parse_args()


if __name__ == "__main__":
    """
    This is the entry point when the program is installed via Meson
    """
    log.debug("MiAZ installation done via Meson!")
    args = parse_arguments()
    app = MiAZ(ENV)
    app.run(sys.argv)
