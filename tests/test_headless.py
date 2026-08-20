#!/usr/bin/python3

"""
Tests for starting MiAZ where there is no display.

Running `miaz` over SSH without X forwarding built the plugin index, started the
web server, and only then died building the first widget with "Gtk couldn't be
initialized". The desktop crash handler then tried to report that in an
Adw.AlertDialog, which needs the display that is missing, and the process took
a SIGSEGV. The user got a traceback, a core dump, and no hint that `miaz search`
works fine there.
"""

import os
import signal
import subprocess
import sys

import gi

gi.require_version('Gdk', '4.0')
from gi.repository import Gdk

from MiAZ.frontend.desktop.services.crash import MiAZCrashHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What tells GTK where to draw. Removing all three is what an SSH session
# without X forwarding looks like.
DISPLAY_VARS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR')


def run_headless(args, home):
    env = {
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        'HOME': str(home),
        'PYTHONPATH': ROOT,
        'LC_ALL': 'C',
    }
    for name in DISPLAY_VARS:
        env.pop(name, None)
    return subprocess.run([sys.executable, '-m', 'MiAZ.miaz'] + args,
                          cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=120)


def test_no_display_does_not_crash(tmp_path):
    """A segfault is not a message. Whatever MiAZ says here, it has to say it
    and exit, not dump core.
    """
    result = run_headless([], tmp_path / 'home')
    assert result.returncode >= 0, (
        f"MiAZ died of signal {-result.returncode} "
        f"({signal.Signals(-result.returncode).name}) with no display")


def test_no_display_says_so_and_points_at_the_command_line(tmp_path):
    """The command line works without a display, so the message should say
    where to go instead of only what failed.
    """
    result = run_headless([], tmp_path / 'home')
    assert result.returncode == 2, f"exit code was {result.returncode}"
    assert 'display' in result.stderr.lower(), result.stderr[-2000:]
    assert 'miaz search' in result.stderr, result.stderr[-2000:]


def test_no_display_leaves_the_window_work_undone(tmp_path):
    """The check has to come before the expensive startup, not after it. The
    web server is the visible half of that: it opens a socket.
    """
    result = run_headless([], tmp_path / 'home')
    assert 'WebServer running' not in result.stderr, (
        "MiAZ started the web server before finding out it had no window")


def test_the_command_line_still_works_without_a_display(tmp_path):
    """The point of refusing the window is that the rest still runs."""
    result = run_headless(['repos'], tmp_path / 'home')
    assert result.returncode in (0, 1, 3), (
        f"exit code {result.returncode}, stderr: {result.stderr[-2000:]}")


class FakeApp:
    def get_env(self):
        return {}

    def get_widget(self, name):
        return None


def test_crash_dialog_is_skipped_when_there_is_no_display(monkeypatch):
    """The crash handler is installed before the window exists, on purpose, so
    it has to survive the case where GTK itself is what failed. Building an
    Adw.AlertDialog without a display segfaults inside GTK, which no `except
    Exception` around it can catch.
    """
    monkeypatch.setattr(Gdk.Display, 'get_default', staticmethod(lambda: None))
    handler = MiAZCrashHandler(FakeApp())
    built = []
    monkeypatch.setattr(handler, '_build_and_present',
                        lambda *args: built.append(args))
    handler._present_dialog('boom', 'the report')
    assert built == [], "the crash dialog was built with no display to show it on"


def test_crash_dialog_is_built_when_there_is_a_display(monkeypatch):
    """The guard must not swallow the dialog on a normal desktop."""
    monkeypatch.setattr(Gdk.Display, 'get_default', staticmethod(lambda: object()))
    handler = MiAZCrashHandler(FakeApp())
    built = []
    monkeypatch.setattr(handler, '_build_and_present',
                        lambda *args: built.append(args))
    handler._present_dialog('boom', 'the report')
    assert built == [('boom', 'the report')]
