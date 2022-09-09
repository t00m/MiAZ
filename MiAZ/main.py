#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse

from MiAZ.backend.env import ENV
from MiAZ.backend.util import get_version
from MiAZ.backend.util import desktop_session
from MiAZ.backend.config import load_config
from MiAZ.backend.controller import get_documents
from MiAZ.backend.controller import valid_filename


class MiAZ:
    def __init__(self, params) -> None:
        self.params = params
    def run(self):
        print("%s v%s" % (ENV['APP']['shortname'], get_version()))
        if desktop_session() is None:
            print("No Desktop Environment available")
        config = load_config()
        if config is None:
            print("Configuration file not found!")
        docs = get_documents(self.params.SOURCE)
        for doc in docs:
            valid, reasons = valid_filename(doc)
            if not valid:
                print ("%s needs revision. Reasons" % doc)
                for reason in reasons:
                    print ("\t => %s" % reason)


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
