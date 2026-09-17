#!/usr/bin/python3

"""MiAZ.frontend.desktop.app, the parts that can be judged without a window.

They were class attributes holding mutable dictionaries, so every MiAZApp
shared one registry and a second instance emptied the first one's.

The test is structural rather than behavioural, for two reasons. Building a
MiAZApp installs a crash excepthook, which is not something to do to the rest
of the suite. And a second one cannot be built at all: MiAZActions.__init__
calls GObject.signal_new, which registers on the class, so the second instance
raises 'could not create signal' before reaching anything here.
"""

import os
import subprocess
import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import GObject

from MiAZ.frontend.desktop.app import MiAZApp, remembered_size
from MiAZ.frontend.desktop.services.actions import MiAZActions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Two applications in one process, which is what the registries above are for.
# Run outside the suite because building one installs a crash excepthook, and
# pytest needs its own.
TWO_APPS = '''\
import os, sys, tempfile
sys.path.insert(0, %r)
os.environ['HOME'] = tempfile.mkdtemp(prefix='miaz-twoapps-')
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from MiAZ.frontend.desktop.app import MiAZApp
first = MiAZApp(application_id='io.github.t00m.MiAZ.TwoA')
first.add_widget('only-in-first', object())
second = MiAZApp(application_id='io.github.t00m.MiAZ.TwoB')
print('kept', first.get_widget('only-in-first') is not None)
print('separate', first._miazobjs is not second._miazobjs)
''' % ROOT


def test_the_registries_are_not_shared_between_instances():
    """A mutable class attribute is one dictionary for every instance.

    __init__ assigns into it rather than rebinding, so self._miazobjs['widgets']
    reaches the class dictionary and the instances are not separate at all.
    """
    for name in ('_miazobjs', '_config'):
        assert name not in vars(MiAZApp), (
            f'{name} is a class attribute, so every MiAZApp shares one')


def test_the_dead_finder_is_gone():
    """find_widget_by_type had no caller but its own recursion, and logged a
    debug line per widget visited. find_widget does the same job with an extra
    filter and is the one that is used."""
    assert not hasattr(MiAZApp, 'find_widget_by_type')
    assert hasattr(MiAZApp, 'find_widget')


def test_a_maximized_window_keeps_the_size_it_had_before():
    """Saving the size of a maximized window makes unmaximizing do nothing.

    A maximized window reports the screen as its size, and that size is what
    GTK restores to when the user unmaximizes: set_default_size is what the
    next start passes it. Saved while maximized, the restored window is the
    size of the screen, so the unmaximize button appears broken.
    """
    assert remembered_size(1920, 1080, maximized=True, previous=(1024, 768)) \
        == (1024, 768)


def test_an_ordinary_window_is_remembered_as_it_is():
    assert remembered_size(1024, 768, maximized=False, previous=(800, 600)) \
        == (1024, 768)


def test_a_first_run_has_nothing_to_fall_back_on():
    """Maximized before anything was ever saved: the defaults stand."""
    assert remembered_size(1920, 1080, maximized=True, previous=(1280, 800)) \
        == (1280, 800)


def test_the_signals_are_declared_on_the_class():
    """MiAZActions registered them with GObject.signal_new inside __init__.

    signal_new registers on the class, so the second instance raised
    'could not create signal'. Nothing built two, which is the only reason it
    never showed: it also made the shared registries above untestable.
    """
    # PyGObject empties __gsignals__ once it has registered what was in it, so
    # the class is what holds the answer, not the attribute.
    assert GObject.signal_lookup('settings-loaded', MiAZActions) != 0
    assert GObject.signal_lookup('rename-dialog-built', MiAZActions) != 0


def test_two_applications_keep_their_own_widgets():
    """The payoff: what the instance registries are for."""
    result = subprocess.run([sys.executable, '-c', TWO_APPS],
                            cwd=ROOT, capture_output=True, text=True,
                            timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert 'kept True' in result.stdout, result.stdout + result.stderr[-2000:]
    assert 'separate True' in result.stdout, result.stdout


def test_the_application_installs_one_job_queue():
    """The queue is both a service, for anything holding the app, and the
    module singleton run_in_background reads. They must be the same object, or
    the indicator watches a queue nothing registers with."""
    script = '''
import os, sys, tempfile
sys.path.insert(0, %r)
os.environ['HOME'] = tempfile.mkdtemp(prefix='miaz-jobq-')
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from MiAZ.backend import tasks
from MiAZ.frontend.desktop.app import MiAZApp
app = MiAZApp(application_id='io.github.t00m.MiAZ.JobQueue')
print('same', app.get_service('jobs') is tasks.job_queue())
print('present', app.get_service('jobs') is not None)
''' % ROOT
    result = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert 'same True' in result.stdout, result.stdout + result.stderr[-2000:]
    assert 'present True' in result.stdout, result.stdout
