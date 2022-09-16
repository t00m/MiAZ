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
        self.log.debug("MiAZ - Start")
        self.params = params

    def run(self):
        self.log.info("%s v%s", ENV['APP']['shortname'], get_version())
        if ENV['SYS']['DESKTOP'] is not None:
            from MiAZ.frontend.desktop.gui import GUI
        else:
            from MiAZ.frontend.console.gui import GUI
        app = GUI(application_id="com.example.MiAZ")
        app.run()
        self.log.debug("MiAZ - End")

    def setup_environment(self):
        """
        Setup MiAZ user environment
        """
        # Create local paths if they do not exist
        for entry in ENV['LPATH']:
            if not os.path.exists(ENV['LPATH'][entry]):
                os.makedirs(ENV['LPATH'][entry])

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
    miaz_options.add_argument('-s', help='Documents source directory', action='store', dest='SOURCE')
    miaz_options.add_argument('-v', help='Show current version', action='version', version='%s %s' % (ENV['APP']['shortname'], ENV['APP']['version']))

    params = parser.parse_args()
    app = MiAZ(params)
    app.run()
