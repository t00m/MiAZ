#!/usr/bin/python3

"""UI: the four bare keys fire on the document list and nowhere else.

Return, F2, Delete and Ctrl+A are what every file manager uses and what every
text entry also wants. MiAZ has a search entry that can hold focus, so a
global Delete would remove documents while somebody was editing a filter.
They are installed on the list instead, and this file is the proof.
"""

from gi.repository import Gtk

from MiAZ.frontend.desktop.services import shortcuts as sct


def controller(driver):
    found = driver.widget('workspace-shortcut-controller')
    assert found is not None, 'the document list has no shortcut controller'
    return found


def test_the_list_controller_is_local_scope(miaz):
    """GLOBAL would put these keys back on the window, which is the bug."""
    assert controller(miaz).get_scope() == Gtk.ShortcutScope.LOCAL


def test_the_controller_is_on_the_column_view(miaz):
    assert controller(miaz).get_widget() is miaz.widget('workspace-view').cv


def test_the_controller_carries_every_list_scoped_binding(miaz):
    registry = miaz.service('shortcuts')
    wanted = {b.accelerator for b in registry.bindings(scope=sct.LIST)}
    assert wanted == {'Return', 'F2', 'Delete', '<Control>a'}
    installed = set()
    for shortcut in controller(miaz):
        installed.add(shortcut.get_trigger().to_string())
    for accelerator in wanted:
        ok, key, mods = Gtk.accelerator_parse(accelerator)
        assert Gtk.accelerator_name(key, mods) in installed or \
            accelerator in installed, f'{accelerator} is not installed'


def test_no_list_scoped_key_is_also_an_application_accelerator(miaz):
    """The regression test for the reason scoping exists. If Delete were also
    set on the application, it would fire while the search entry had focus."""
    registry = miaz.service('shortcuts')
    for binding in registry.bindings(scope=sct.LIST):
        assert miaz.app.get_accels_for_action(f'app.{binding.action}') == [], (
            f'{binding.action} is list scoped but also bound globally')


def test_the_hand_written_key_handler_is_gone(miaz):
    """Four keys used to be implemented by hand on a window controller. Two
    implementations of one key is the drift this work removes."""
    assert miaz.widget('window-event-controller') is None


def test_escape_is_a_global_accelerator_for_clearing_filters(miaz):
    assert miaz.app.get_accels_for_action('app.filters-clear') == ['Escape']


def test_focus_can_land_in_the_document_list(miaz, clean_view):
    """LOCAL scope fires only while the list, or a widget inside it, has
    focus. If focus can never land there, F2 and Delete do nothing at all,
    which is worse than the behaviour they replace.

    Focus is walked upwards because a Gtk.ColumnView holds an inner list that
    is what actually takes focus.
    """
    cv = miaz.widget('workspace-view').cv
    cv.grab_focus()
    miaz.pump()
    focus = miaz.widget('window').get_focus()
    assert focus is not None, 'nothing in the window has focus'
    while focus is not None:
        if focus is cv:
            return
        focus = focus.get_parent()
    raise AssertionError('focus did not land inside the document list')
