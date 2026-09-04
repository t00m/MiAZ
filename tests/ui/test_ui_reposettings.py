#!/usr/bin/python3

"""UI: the Repository Settings dialog.

Per-repository settings used to be split across three places: an inline group
in the Application Settings dialog, a per-plugin dialog behind a button in the
Plugins tab, and nothing at all for the rest. These check they arrive in one.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import GObject

import pytest


@pytest.fixture
def repo_settings(clean_view):
    """The dialog, opened, with its widgets registered."""
    clean_view.service('actions').show_repository_settings()
    clean_view.pump(0.5)
    window = clean_view.widget('window-repo-settings')
    assert window is not None, 'the repository settings window did not open'
    yield window
    window.close()
    clean_view.pump(0.3)


def row_titles(widget):
    """The title of every Adw.PreferencesRow anywhere under `widget`.

    A group wraps its rows in boxes and list boxes, and an ExpanderRow holds
    more rows inside itself, so this walks the whole tree rather than the
    direct children.
    """
    found = []
    if isinstance(widget, Adw.PreferencesRow):
        found.append(widget.get_title())
    child = widget.get_first_child()
    while child is not None:
        found.extend(row_titles(child))
        child = child.get_next_sibling()
    return found


def test_the_settings_tab_is_there(repo_settings, clean_view):
    page = clean_view.widget('repository-settings-page-settings')
    assert page is not None, 'no Settings tab'


def test_the_settings_tab_names_the_repository(repo_settings, clean_view):
    page = clean_view.widget('repository-settings-page-settings')
    row_name = clean_view.widget('repository-settings-row-name')
    row_path = clean_view.widget('repository-settings-row-location')
    assert row_name is not None and row_path is not None
    repo = clean_view.service('repo')
    assert row_path.get_subtitle() == repo.docs


def test_nothing_is_built_until_the_tab_is_shown(repo_settings, clean_view):
    """The guard that keeps the scanner asleep. AutoScan builds its group by
    running SANE, so opening this dialog must not call any builder."""
    page = clean_view.widget('repository-settings-page-settings')
    assert page.is_built() is False
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)
    assert page.is_built() is True


def _page_number(notebook, page):
    for number in range(notebook.get_n_pages()):
        child = notebook.get_nth_page(number)
        if child is page or (hasattr(child, 'get_first_child')
                             and child.get_first_child() is page):
            return number
    raise AssertionError('page is not in the notebook')


def count_handlers(obj, signal_name):
    """How many handlers are connected to this signal right now.

    There is no call that answers this directly. signal_handler_find returns
    one match at a time, so each one found is blocked to take it out of the
    running and unblocked again afterwards, which leaves the object exactly
    as it was. Mirrors the helper tests/ui/test_ui_plugin_signals.py uses for
    the same question about plugins.
    """
    signal_id, detail = GObject.signal_parse_name(signal_name, obj, True)
    match = GObject.SignalMatchType.ID | GObject.SignalMatchType.UNBLOCKED
    blocked = []
    while True:
        handler_id = GObject.signal_handler_find(
            obj, match, signal_id, detail, None, None, None)
        if not handler_id:
            break
        GObject.signal_handler_block(obj, handler_id)
        blocked.append(handler_id)
    for handler_id in blocked:
        GObject.signal_handler_unblock(obj, handler_id)
    return len(blocked)


def test_the_page_disconnects_when_the_dialog_closes(clean_view):
    """A fresh page is built every time the dialog opens. Each one has to let
    go of the plugin-system signal it took hold of, or repeated open/close
    leaks a handler and leaves a dead page reacting to plugin changes, the
    same bug tests/ui/test_ui_plugin_signals.py exists to catch for plugins.
    """
    plugin_system = clean_view.service('plugin-system')
    baseline = count_handlers(plugin_system, 'plugins-updated')

    clean_view.service('actions').show_repository_settings()
    clean_view.pump(0.5)
    window = clean_view.widget('window-repo-settings')
    assert window is not None, 'the repository settings window did not open'

    page = clean_view.widget('repository-settings-page-settings')
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)
    assert page._sid_plugins_updated is not None, 'the page never connected'
    assert count_handlers(plugin_system, 'plugins-updated') == baseline + 1

    window.close()
    clean_view.pump(0.3)

    assert page._sid_plugins_updated is None, 'the page is still connected'
    assert count_handlers(plugin_system, 'plugins-updated') == baseline
