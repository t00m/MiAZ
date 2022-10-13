#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

from MiAZ.backend.env import ENV
from MiAZ.backend.util import get_version
from MiAZ.backend.log import get_logger


class MiAZ:
    def __init__(self, params) -> None:
        self.setup_environment()
        self.log = get_logger('MiAZ.Main')
        self.log.info("%s v%s - Start", ENV['APP']['shortname'], get_version())
        self.params = params

    def setup_environment(self):
        """Setup MiAZ user environment

        Create local paths if they do not exist
        """
        for entry in ENV['LPATH']:
            if not os.path.exists(ENV['LPATH'][entry]):
                os.makedirs(ENV['LPATH'][entry])

    def run(self):
        """Execute MiAZ in desktop or console mode"""
        if ENV['SYS']['DESKTOP'] is not None:
            from MiAZ.frontend.desktop.app import MiAZApp
        else:
            from MiAZ.frontend.console.app import MiAZApp
        app = MiAZApp(application_id="com.example.MiAZ")
        app.run()
        self.log.info("%s v%s - End", ENV['APP']['shortname'], get_version())


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
    app = MiAZ(params)
    app.run()
