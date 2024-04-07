#!@PYTHON@

# Copyright 2024 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import signal
import locale
import gettext
import argparse


from rich.traceback import install
# ~ install(show_locals=True)

sys.path.insert(1, '@pkgdatadir@')

from loro.backend.core.env import ENV
from loro.backend.core.log import get_logger
from loro.backend.core.util import get_default_workers
from loro.main import main

log = get_logger('loro')

ENV['APP'] = {}
ENV['APP']['ID'] = '@APP_ID@'
ENV['APP']['VERSION'] = '@VERSION@'
ENV['APP']['PGKDATADIR'] = '@pkgdatadir@'
ENV['APP']['LOCALEDIR'] = '@localedir@'

signal.signal(signal.SIGINT, signal.SIG_DFL)
gettext.install('loro', ENV['APP']['LOCALEDIR'])

try:
  locale.bindtextdomain('loro', ENV['APP']['LOCALEDIR'])
  locale.textdomain('loro')
  # ~ log.debug("Locales set")
except:
  log.error('Cannot set locale.')

try:
  gettext.bindtextdomain('loro', ENV['APP']['LOCALEDIR'])
  gettext.textdomain('loro')
  # ~ log.debug("Gettext set")
except:
  log.error('Cannot load translations.')


if __name__ == "__main__":
    WORKERS = get_default_workers()

    # Loro arguments
    # ~ """Set up application arguments and execute."""
    extra_usage = """"""
    parser = argparse.ArgumentParser(
        prog='loro',
        description='%s v%s\nApplication for helping to study another language' % (ENV['APP']['ID'], ENV['APP']['VERSION']),
        epilog=extra_usage,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    loro_options = parser.add_argument_group('Loro Options')
    loro_options.add_argument('-s', '--source', help='Source language (2 letters)', action='store', dest='SOURCE')
    loro_options.add_argument('-t', '--target', help='Target language (2 letters)', action='store', dest='TARGET')
    loro_options.add_argument('-w', '--workers', help='Number of workers. Default is CPUs available/2. Default number of workers in this machine: %d' % WORKERS, type=int, action='store', dest='WORKERS', default=int(WORKERS))
    loro_options.add_argument('-L', '--log', help='Control output verbosity. Default set to INFO', dest='LOGLEVEL', action='store', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    loro_options.add_argument('-v', '--version', help='Show current version', action='version', version='%s %s' % (ENV['APP']['ID'], ENV['APP']['VERSION']))
    loro_options.add_argument('-r', '--reset', help="Warning! Delete configuration for source/target languages", action='store_true', dest='RESET', default=False)
    loro_options.add_argument('-g', '-gui', help="Execute app in GUI mode", action='store_true', dest='GUI', default=True)
    params = parser.parse_args()
    main(params)




