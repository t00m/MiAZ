#!@PYTHON@

# Copyright 2019-2025 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import argparse
import logging
import signal
import locale
import gettext
import fcntl
import atexit

sys.path.insert(1, '@pkgdatadir@')

from MiAZ.backend.log import (MiAZLog, debug_requested, enable_file_logging,
                              set_console_level)

# A bare first argument means a subcommand, so this is the command line and not
# the window. Silence the startup logging before it happens: the environment
# dump and the banner are written while importing MiAZ.env, below. MIAZ_DEBUG=1
# brings them back.
if len(sys.argv) > 1 and not sys.argv[1].startswith('-') and not debug_requested():
    set_console_level(logging.WARNING)

from MiAZ.env import ENV  # noqa: E402  (must follow the silencing above)
from MiAZ.backend.crash import install_backend_excepthook, install_fatal_handler

log = MiAZLog('MiAZ')

# The versions the code actually calls: Gtk.FileDialog is 4.10,
# Adw.InlineViewSwitcher 1.7. tests/test_toolkit_version.py checks both.
GTK_MINIMUM = (4, 10)
ADW_MINIMUM = (1, 7)

# Check Desktop environment
ENV['DESKTOP'] = {}
try:
    import gi
except ImportError:
    sys.exit("No support for Python GObject")

try:
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gdk', '4.0')
    from gi.repository import Gtk
    from gi.repository import Gdk
    from gi.repository import GLib
    try:
        gi.require_version('GLibUnix', '2.0')
        from gi.repository import GLibUnix
    except (ValueError, ImportError):
        GLibUnix = None
    ENV['DESKTOP']['GTK_VERSION'] = (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION)
    ENV['DESKTOP']['GTK_SUPPORT'] = (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION) >= GTK_MINIMUM
except (ValueError, ImportError):
    ENV['DESKTOP']['GTK_SUPPORT'] = False

try:
    gi.require_version('Adw', '1')
    from gi.repository import Adw
    ENV['DESKTOP']['ADW_VERSION'] = (Adw.MAJOR_VERSION, Adw.MINOR_VERSION, Adw.MICRO_VERSION)
    ENV['DESKTOP']['ADW_SUPPORT'] = (Adw.MAJOR_VERSION, Adw.MINOR_VERSION) >= ADW_MINIMUM
except (ValueError, ImportError):
    ENV['DESKTOP']['ADW_SUPPORT'] = False


ENV['DESKTOP']['ENABLED'] = ENV['DESKTOP']['GTK_SUPPORT'] and ENV['DESKTOP']['ADW_SUPPORT']


def toolkit_version(key):
    """A toolkit version as text, or a plain word when it is not installed.

    Read out of ENV, not off the module. The two imports above are conditional,
    so on a machine without the typelibs the names Gtk and Adw were never bound,
    and the lines below used to dereference them anyway: the branch that exists
    to tell a user their desktop packages are missing raised NameError on the
    very name it was reporting about, before reaching its own sys.exit.
    """
    version = ENV['DESKTOP'].get(key)
    return '.'.join(str(part) for part in version) if version else None


def toolkit_report(name, key, minimum):
    """One line saying what is there and what is wanted.

    Built rather than formatted in place because it has to read correctly when
    nothing is installed at all: "GTK not installed, 4.10 or later needed",
    not "GTK not installed found".
    """
    version = toolkit_version(key)
    found = f'{version} found' if version else 'not installed'
    return f'{name} {found}, {minimum[0]}.{minimum[1]} or later needed'


log.debug(f"GTK available ({toolkit_version('GTK_VERSION') or 'not installed'})")
log.debug(f"ADW available ({toolkit_version('ADW_VERSION') or 'not installed'})")
log.debug(f"Desktop enabled? {ENV['DESKTOP']['ENABLED']}")
if not ENV['DESKTOP']['ENABLED']:
    log.error("Desktop dependencies not met to run this app")
    log.error(toolkit_report('GTK', 'GTK_VERSION', GTK_MINIMUM))
    log.error(toolkit_report('Adw', 'ADW_VERSION', ADW_MINIMUM))
    sys.exit(-1)


signal.signal(signal.SIGINT, signal.SIG_DFL)
gettext.install('miaz', ENV['APP']['LOCALEDIR'])

try:
    locale.bindtextdomain('miaz', ENV['APP']['LOCALEDIR'])
    locale.textdomain('miaz')
except Exception:
    log.error('Cannot set locale.')

# Bind the iso-codes country-name catalog so util.humanize_value() can localize
# country descriptions. It is a system domain, installed at /usr/share/locale on
# a normal system and in the GNOME Flatpak runtime alike.
try:
    gettext.bindtextdomain('iso_3166-1', '/usr/share/locale')
except Exception:
    log.error('Cannot bind iso-codes locale for country names.')

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
        from MiAZ.backend.util import MiAZUtil
        log.debug(f"MiAZ install mode: {MiAZUtil.get_install_mode()}")
        self.setup_environment()
        # Enable persistent file logging now that the directories exist, then
        # install the console/log crash handler so any later failure is logged.
        log_file = enable_file_logging(ENV['FILE']['LOG'])
        self._acquire_lock()
        self.log = MiAZLog('MiAZ')
        install_backend_excepthook(self.log, ENV)
        # A segfault never reaches the excepthook above, so the Python side of
        # the stack is written by faulthandler instead.
        install_fatal_handler(log_file)
        self.clean_temp_directory()

        self.log.info(f"{ENV['APP']['shortname']} v{ENV['APP']['VERSION']} - Start")
        self.log.info(f"Logging to {log_file}")

    def _acquire_lock(self):
        lock_dir = self.env['LPATH']['VAR']
        os.makedirs(lock_dir, exist_ok=True)
        lock_path = os.path.join(lock_dir, 'miaz.lock')
        self._lock_fd = open(lock_path, 'w', encoding='utf-8')
        try:
            fcntl.lockf(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            msg = "MiAZ is already running. Exiting."
            log.warning(msg)
            sys.exit(1)
        self._lock_fd.write(str(os.getpid()) + '\n')
        self._lock_fd.flush()
        atexit.register(self._release_lock)

    def _release_lock(self):
        try:
            fcntl.lockf(self._lock_fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            self._lock_fd.close()
        except Exception:
            pass

    def setup_environment(self):
        """Set up MiAZ user environment."""
        ENV = self.env
        for entry in ENV['LPATH']:
            if not os.path.exists(ENV['LPATH'][entry]):
                os.makedirs(ENV['LPATH'][entry])
        self._ensure_tool_path()

    def clean_temp_directory(self):
        """Empty var/tmp so every run starts with no leftovers.

        Scans waiting to be imported, exports being built and unzipped bundles
        are written there and only matter while the session that created them
        is running. It runs after the lock is taken, so a second instance never
        deletes files the running one is still using, and it recreates the
        subdirectories the environment expects afterwards.
        """
        from MiAZ.backend.util import clean_temp_dir
        tmp_dir = self.env['LPATH']['TMP']
        removed = clean_temp_dir(tmp_dir)
        if removed:
            self.log.info(f"Temporary directory cleaned: {removed} entries deleted from {tmp_dir}")
        for entry in self.env['LPATH']:
            path = self.env['LPATH'][entry]
            if path.startswith(tmp_dir + os.sep):
                os.makedirs(path, exist_ok=True)

    def _ensure_tool_path(self):
        """Guarantee the standard system tool directories are on PATH.

        Launched from a GNOME .desktop icon, MiAZ can start with an empty or
        stripped PATH, so shutil.which and subprocess do not find the system
        tools plugins depend on (ocrmypdf, scanimage, pdftotext, ...), even
        though they live in /usr/bin. Running from a shell works because the
        shell PATH is rich. Append any missing standard directory so tool
        detection and execution behave the same regardless of how MiAZ started.
        """
        standard = ['/usr/local/bin', '/usr/bin', '/bin',
                    '/usr/local/sbin', '/usr/sbin', '/sbin',
                    os.path.expanduser('~/.local/bin')]
        parts = [p for p in os.environ.get('PATH', '').split(os.pathsep) if p]
        for directory in standard:
            if directory not in parts and os.path.isdir(directory):
                parts.append(directory)
        os.environ['PATH'] = os.pathsep.join(parts)

    def run(self, params):
        """Execute MiAZ in desktop or console mode."""
        self.log.info(f"Params: {params}")
        ENV = self.env

        # A known subcommand means the command line, not the window. Anything
        # else, including no arguments and --version, starts the desktop app
        # exactly as before, so the .desktop launcher is unaffected.
        from MiAZ.frontend.console.cli import COMMANDS, main
        if len(params) > 1 and params[1] in COMMANDS:
            sys.exit(main(params[1:], sys.stdout, sys.stderr, env=ENV))

        if not ENV['DESKTOP']['ENABLED']:
            # No usable GTK and no subcommand either. There is no window to
            # open, so point at what does work here rather than failing on an
            # import.
            sys.stderr.write("GTK is not available. Try 'miaz search' or "
                             "'miaz repos'.\n")
            sys.exit(2)

        # GTK imports fine with nowhere to draw and only fails at the first
        # widget. init_check() returns True regardless, so ask the display.
        Gtk.init_check()
        if Gdk.Display.get_default() is None:
            sys.stderr.write("MiAZ found no display to open its window on. "
                             "Try 'miaz search' or 'miaz repos'.\n")
            sys.exit(2)

        from MiAZ.frontend.desktop.app import MiAZApp
        app = MiAZApp(application_id=ENV['APP']['ID'])
        app.set_env(ENV)

        # Set up the signal handler for CONTROL-C
        # GLibUnix.signal_add is preferred but not available in all runtimes
        # (e.g. some Flatpak PyGObject builds expose GLibUnix without signal_add).
        # Fall back to GLib.unix_signal_add; if that too is absent, the
        # signal.signal(SIGINT, SIG_DFL) set above ensures Ctrl-C still works.
        try:
            GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.exit)
        except AttributeError:
            try:
                GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.exit)
            except AttributeError:
                log.warning("Could not register GLib SIGINT handler; relying on default signal handling")

        try:
            app.run()
        except KeyboardInterrupt:
            self.log.error("Application killed by user")
            sys.exit(0)
        self.log.info(f"{ENV['APP']['shortname']} v{ENV['APP']['VERSION']} - End")

def parse_arguments():
    # Subcommands belong to the console parser (frontend/console/cli.py). This
    # one only knows the options the window takes and would reject 'search' as
    # an unrecognised argument before run() ever sees it.
    from MiAZ.frontend.console.cli import COMMANDS
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        # Silence here rather than in main(): the environment dump and the
        # startup banner are logged while this module is imported, long before
        # a command runs. MIAZ_DEBUG=1 brings them back.
        if not debug_requested():
            from MiAZ.backend.log import set_console_level
            set_console_level(logging.WARNING)
        return None

    parser = argparse.ArgumentParser(description=ENV['APP']['description'])
    parser.add_argument('--version', action='version', version=ENV['APP']['VERSION'], help='Show version number and exit.')
    return parser.parse_args()


if __name__ == "__main__":
    """
    This is the entry point when the program is installed via Meson
    """
    args = parse_arguments()
    app = MiAZ(ENV)
    app.run(sys.argv)
