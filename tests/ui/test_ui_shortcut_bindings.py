#!/usr/bin/python3

"""UI: the keys that moved are bound to their new combinations.

Accelerators are compared parsed, never as strings. GTK normalises what it
stores, so '<Control>comma' may come back spelled differently, and comparing
text would make this test fail for the wrong reason.
"""

from gi.repository import Gtk


def parse(accelerator):
    ok, key, mods = Gtk.accelerator_parse(accelerator)
    assert ok, f'{accelerator} does not parse'
    return key, mods


def bound(driver, action):
    return [parse(a) for a in driver.app.get_accels_for_action(f'app.{action}')]


def test_the_moved_keys_carry_their_new_combinations(miaz):
    expected = {
        'app-settings': '<Control>comma',
        'app-shortcuts': '<Control>question',
        'app-help': 'F1',
        'app-quit': '<Control>q',
        'import-doc': '<Control>i',
        'import-dir': '<Control><Shift>i',
        'copy-document-names': '<Control><Shift>c',
        'notes-doc': '<Control>n',
        'notes-all': '<Control><Shift>n',
    }
    for action, accelerator in expected.items():
        assert bound(miaz, action) == [parse(accelerator)], (
            f'{action} is not on {accelerator}')


def test_about_has_no_accelerator(miaz):
    """Ctrl+B used to open About. It is Bold in every editor, and MiAZ has a
    notes editor. About conventionally has no key at all."""
    assert miaz.app.get_accels_for_action('app.app-about') == []


def test_nothing_answers_to_the_old_combinations(miaz):
    """None of the six are rebound to a different MiAZ action, so a stale
    reflex does nothing rather than something surprising."""
    for old in ('<Control>s', '<Control>b', '<Control>Insert',
                '<Shift>Insert', '<Control>BackSpace', '<Control>Delete'):
        assert miaz.app.get_actions_for_accel(old) == [], (
            f'{old} still activates something')
