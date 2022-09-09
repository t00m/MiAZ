#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse

from MiAZ.backend.env import ENV
from MiAZ.backend.util import get_version
from MiAZ.backend.config import load_config


class MiAZ:
    def __init__(self, params) -> None:
        self.params = params
    def run(self):
        print("%s v%s" % (ENV['APP']['shortname'], get_version()))
        config = load_config()
        if config is None:
            print("Configuration file not found!")
        if ENV['SYS']['DESKTOP'] is not None:
            from MiAZ.frontend.desktop.gui import GUI
        else:
            from MiAZ.frontend.console.gui import GUI
        app = GUI(application_id="com.example.MiAZ")
        app.run()


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
