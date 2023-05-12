#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Setup MiAZ project.
# File: main.py.
# Author: Tomás Vírseda
# License: GPL v3
# Description: main entry point
"""

import os
import sys
import locale
import gettext
import argparse

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger

app_version = open(ENV['FILE']['VERSION']).read().strip()
app_shortname = ENV['APP']['shortname']

class MiAZ:
    def __init__(self) -> None:
        self.setup_environment()
        self.log = get_logger('MiAZ.Main')
        self.set_internationalization()
        self.log.info("%s v%s - Start", app_shortname, app_version)

    def setup_environment(self):
        """Setup MiAZ user environment

        Create local paths if they do not exist
        """
        for entry in ENV['LPATH']:
            if not os.path.exists(ENV['LPATH'][entry]):
                os.makedirs(ENV['LPATH'][entry])

    def set_internationalization(self):
        """Sets application internationalization."""
        try:
            locale.bindtextdomain('miaz', ENV['GPATH']['LOCALE'])
            locale.textdomain('miaz')
            self.log.debug("Gettext: binding to %s", ENV['GPATH']['LOCALE'])
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
        self.log.debug('Desktop name: %s', ENV['SYS']['DESKTOP'])
        if ENV['SYS']['DESKTOP'] is not None:
            from MiAZ.frontend.desktop.app import MiAZApp
        else:
            from MiAZ.frontend.console.app import MiAZApp
        app = MiAZApp(application_id=ENV['APP']['ID'])
        try:
            app.run()
        except KeyboardInterrupt:
            self.log.error("Application killed by user")
            exit(0)
        self.log.info("%s v%s - End", app_shortname, app_version)


def main():
    """Set up application arguments and execute."""
    extra_usage = """"""
    parser = argparse.ArgumentParser(
        prog='MiAZ',
        description='Personal Document Organizer',
        epilog=extra_usage,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # MiAZ arguments
    miaz_options = parser.add_argument_group('MiAZ Options')
    miaz_options.add_argument('-v', '--version', help='Show current version', action='version', version='%s %s' % (ENV['APP']['shortname'], ENV['APP']['version']))

    params = parser.parse_args()
    app = MiAZ()
    app.run()
