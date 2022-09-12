#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

from MiAZ.backend.env import ENV
from MiAZ.backend.util import get_version


class MiAZ:
    def __init__(self, params) -> None:
        self.params = params
    def run(self):
        print("%s v%s" % (ENV['APP']['shortname'], get_version()))
        self.setup_environment()
        if ENV['SYS']['DESKTOP'] is not None:
            from MiAZ.frontend.desktop.gui import GUI
        else:
            from MiAZ.frontend.console.gui import GUI
        app = GUI(application_id="com.example.MiAZ")
        app.run()

    def setup_environment(self):
            """
            Setup MiAZ user environment
            """
            # Create local paths if they do not exist
            # ~ self.log.debug("Checking directories for MiAZ")
            for entry in ENV['LPATH']:
                if not os.path.exists(ENV['LPATH'][entry]):
                    os.makedirs(ENV['LPATH'][entry])
                    # ~ self.log.debug("Directory %s created", ENV['LPATH'][entry])
            # ~ self.log.debug("MiAZ directory structure ok")

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
