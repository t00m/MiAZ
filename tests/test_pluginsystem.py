#!/usr/bin/python3

"""
Unit tests for the pure load-failure text formatters in the plugin system.

The module imports gi/Peas, so the test sets the versions first (the app does
the same). The formatters are module-level and side-effect free, so importing
the module needs no running app and no display.
"""

import gi
gi.require_version('Peas', '2')

from MiAZ.frontend.desktop.services import pluginsystem as ps


def test_toast_singular():
    assert ps.format_load_failure_toast(1) == \
        '1 plugin failed to load. See Settings > Plugins.'


def test_toast_plural():
    assert ps.format_load_failure_toast(3) == \
        '3 plugins failed to load. See Settings > Plugins.'


def test_banner_single_lists_name_and_reason():
    failures = {'notes': {'name': 'MiAZNotes', 'reason': "No module named 'lib'"}}
    assert ps.format_load_failure_banner(failures) == \
        "MiAZNotes failed to load: No module named 'lib'"


def test_banner_joins_multiple():
    failures = {
        'a': {'name': 'PluginA', 'reason': 'r1'},
        'b': {'name': 'PluginB', 'reason': 'r2'},
    }
    out = ps.format_load_failure_banner(failures)
    assert 'PluginA failed to load: r1' in out
    assert 'PluginB failed to load: r2' in out
    assert '; ' in out


def test_banner_empty_is_blank():
    assert ps.format_load_failure_banner({}) == ''
