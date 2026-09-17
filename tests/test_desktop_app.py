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

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from MiAZ.frontend.desktop.app import MiAZApp


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
