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

from MiAZ.backend.log import get_logger

class MiAZ:
    def __init__(self, ENV: dict) -> None:
        self.env = ENV
        self.setup_environment()
        self.log = get_logger('MiAZ.Main')
        self.set_internationalization()
        self.log.info("%s v%s - Start", ENV['APP']['shortname'], ENV['FILE']['VERSION'])

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
        try:
            app.run()
        except KeyboardInterrupt:
            self.log.error("Application killed by user")
            exit(0)
        self.log.info("%s v%s - End", app_shortname, app_version)


def main(ENV):
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
    app = MiAZ(ENV)
    app.run()
