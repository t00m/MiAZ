#!/usr/bin/python3

"""
Tests for MiAZ on a machine where GTK is not installed at all.

tests/test_headless.py covers the neighbouring case, GTK installed with no
display. This one is the server: no Gtk, Gdk or Adw typelib anywhere. The
command line has no use for them, and since 0.3 neither does the plugin
system, so `miaz search` has to work there.

It did not. MiAZ/miaz.py checked the toolkit at module scope and called
sys.exit(-1), which runs for every invocation and long before run() decides
whether this is a window or a command, so every command exited 255. The branch
in run() that says "GTK is not available. Try 'miaz search'" could never be
reached, because reaching it required the exit above not to have happened.

The toolkit is hidden rather than uninstalled: a sitecustomize on PYTHONPATH
makes gi.require_version refuse those three namespaces, which is what the
import guards in miaz.py actually test for.
"""

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITECUSTOMIZE = '''\
"""Hide the GTK stack, the way a server without those typelibs would."""
import gi

_real = gi.require_version


def _refuse_the_desktop(namespace, version):
    if namespace in ('Gtk', 'Gdk', 'Adw'):
        raise ValueError(f'Namespace {namespace} not available')
    return _real(namespace, version)


gi.require_version = _refuse_the_desktop
'''


@pytest.fixture
def no_toolkit(tmp_path):
    """A PYTHONPATH whose sitecustomize hides Gtk, Gdk and Adw."""
    shim = tmp_path / 'shim'
    shim.mkdir()
    (shim / 'sitecustomize.py').write_text(SITECUSTOMIZE, encoding='utf-8')
    return str(shim)


def run_miaz(args, home, shim, timeout=120):
    env = {
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        'HOME': str(home),
        'PYTHONPATH': os.pathsep.join([shim, ROOT]),
        'LC_ALL': 'C',
    }
    return subprocess.run([sys.executable, '-m', 'MiAZ.miaz'] + args,
                          cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=timeout)


def test_the_shim_really_hides_the_toolkit(no_toolkit, tmp_path):
    """The test is worthless if the toolkit is still importable.

    Checked first, so a broken shim reads as a broken shim rather than as a
    passing test of nothing.
    """
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([no_toolkit, ROOT]))
    probe = subprocess.run(
        [sys.executable, '-c',
         "import gi\n"
         "try:\n"
         "    gi.require_version('Gtk', '4.0')\n"
         "    print('VISIBLE')\n"
         "except ValueError:\n"
         "    print('HIDDEN')\n"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert probe.stdout.strip() == 'HIDDEN', probe.stdout + probe.stderr


def test_a_command_runs_without_any_toolkit(no_toolkit, tmp_path):
    """The bug: this exited 255 from a module-level sys.exit(-1)."""
    result = run_miaz(['repos'], tmp_path / 'home', no_toolkit)

    # 1 is "no repositories configured", the right answer for a fresh home.
    assert result.returncode in (0, 1), (
        f'exit {result.returncode}, stderr: {result.stderr[-3000:]}')


def test_a_search_runs_without_any_toolkit(no_toolkit, tmp_path):
    """The command that makes a server install worth having."""
    result = run_miaz(['search', 'invoice'], tmp_path / 'home', no_toolkit)

    assert result.returncode != 255, result.stderr[-3000:]
    assert 'Desktop dependencies not met' not in result.stderr


def test_a_plugin_command_runs_without_any_toolkit(no_toolkit, tmp_path):
    """A plugin that declares a command has to import with no typelib either.

    Discovery reads the .plugin files without importing anything, so `miaz
    --help` lists the command whatever the module does. Running it imports the
    module, and that is where a Gtk import at module scope would land. MiAZOCR
    keeps its Adw and Gtk imports inside the methods that build the dialog and
    says so in its docstring, which was a convention with nothing behind it.

    --help is enough: argparse prints the flags out of plugin_info, and getting
    that far means the module imported.
    """
    result = run_miaz(['ocr', '--help'], tmp_path / 'home', no_toolkit)

    assert result.returncode == 0, (
        f'exit {result.returncode}, stderr: {result.stderr[-3000:]}')
    assert '--language' in result.stdout, result.stdout + result.stderr


def test_the_window_says_what_is_missing_and_where_to_go(no_toolkit, tmp_path):
    """Asking for the window on a server should name the commands that work.

    run() has said this all along and could never be reached to say it.
    """
    result = run_miaz([], tmp_path / 'home', no_toolkit)

    assert result.returncode == 2, (
        f'exit {result.returncode}, stderr: {result.stderr[-3000:]}')
    assert 'miaz search' in result.stderr, result.stderr[-3000:]


def test_the_window_still_reports_the_versions_it_wanted(no_toolkit, tmp_path):
    """Telling somebody their GTK is too old is the point of the check.

    Losing that message would be a regression of its own, so the numbers have
    to survive wherever the check ends up.
    """
    result = run_miaz([], tmp_path / 'home', no_toolkit)

    assert '4.10' in result.stderr, result.stderr[-3000:]
    assert '1.7' in result.stderr, result.stderr[-3000:]
