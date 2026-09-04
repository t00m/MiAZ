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


def test_an_interface_plugin_puts_its_settings_here(repo_settings, clean_view):
    """MiAZFullscreen is enabled in the test repository, and its row used to
    be in the Application Settings dialog while its value was written to this
    repository's config."""
    page = clean_view.widget('repository-settings-page-settings')
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)
    titles = row_titles(page)
    assert 'Display fullscreen toggle button' in titles, titles


def test_a_settings_group_goes_away_with_its_plugin(repo_settings, clean_view):
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('fullscreen')
    if info is None or not system.is_plugin_loaded(info):
        pytest.skip('MiAZFullscreen is not enabled in this repository')
    registry = system.settings
    assert any(owner == 'MiAZFullscreen'
               for _c, owner, _b in registry.builders())
    system.unload_plugin(info)
    clean_view.pump(0.3)
    assert not any(owner == 'MiAZFullscreen'
                   for _c, owner, _b in registry.builders())
    system.load_plugin(info)
    clean_view.pump(0.3)
    assert any(owner == 'MiAZFullscreen'
               for _c, owner, _b in registry.builders()), \
        'the group did not come back when the plugin was enabled again'


def test_a_plugin_that_had_a_dialog_now_contributes_rows(repo_settings, clean_view):
    """MiAZOCR's language row used to be reachable only through a button in
    the Plugins tab, which opened a dialog on top of a dialog.

    MiAZOCR is not in DEFAULT_PLUGINS (it needs ocrmypdf, which is not always
    installed), so it is loaded on demand here and unloaded again afterwards,
    leaving the sandbox as this test found it.
    """
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('ocr')
    if info is None:
        pytest.skip('MiAZOCR is not in the plugin index')
    started_loaded = system.is_plugin_loaded(info)
    if not started_loaded:
        if not system.load_plugin(info):
            pytest.skip('MiAZOCR cannot load here: '
                        + str(system.get_load_error(info.get_module_name())))
        clean_view.pump(0.5)
    try:
        page = clean_view.widget('repository-settings-page-settings')
        notebook = clean_view.widget('repository-settings-notebook')
        notebook.set_current_page(_page_number(notebook, page))
        clean_view.pump(0.4)
        titles = row_titles(page)
        assert 'Document language' in titles, titles
    finally:
        if system.is_plugin_loaded(info) != started_loaded:
            system.unload_plugin(info)
            clean_view.pump(0.4)


def test_scanner_settings_keep_the_manual_entry_when_no_app_is_found(
        clean_view, monkeypatch):
    """Regression guard for a dropped branch: an earlier draft of
    MiAZImportFromScan.build_settings replaced the "type a command by hand"
    fallback with a static message, silently removing the only way to set up
    scanning on a machine with no scanner .desktop file.

    This test box has several scanner applications installed (SimpleScan and
    others), so _search_scan_apps() cannot be relied on to come back empty on
    its own; going through the real Settings tab would only ever exercise the
    "apps were found" branch here. Monkeypatching _search_scan_apps on the
    loaded extension forces the other branch, and build_settings() is called
    directly (its return value does not depend on being attached to the
    Settings tab notebook) so the assertions are against the plugin's real
    method, not a copy of it.
    """
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('scan')
    if info is None:
        pytest.skip('MiAZImportFromScan is not in the plugin index')
    started_loaded = system.is_plugin_loaded(info)
    if not started_loaded:
        if not system.load_plugin(info):
            pytest.skip('MiAZImportFromScan cannot load here: '
                        + str(system.get_load_error(info.get_module_name())))
        clean_view.pump(0.5)
    try:
        extension = system.get_extension('scan')
        assert extension is not None, 'the scan extension is not active'
        monkeypatch.setattr(extension, '_search_scan_apps', lambda: [])
        group = extension.build_settings()
        titles = row_titles(group)
        assert 'Scanner command' in titles, titles
        assert 'No scanner application detected' in titles, titles
    finally:
        if system.is_plugin_loaded(info) != started_loaded:
            system.unload_plugin(info)
            clean_view.pump(0.4)


def test_the_scanner_is_not_probed_to_open_the_dialog(repo_settings, clean_view):
    """AutoScan builds its group by running SANE, which wakes the device and
    takes seconds. Opening the dialog must not do that; showing the Settings
    tab is what does.

    MiAZAutoScan is not in DEFAULT_PLUGINS, so it is loaded on demand here and
    unloaded again afterwards, leaving the sandbox as this test found it.
    """
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('autoscan')
    if info is None:
        pytest.skip('MiAZAutoScan is not in the plugin index')
    started_loaded = system.is_plugin_loaded(info)
    if not started_loaded:
        if not system.load_plugin(info):
            pytest.skip('MiAZAutoScan cannot load here: '
                        + str(system.get_load_error(info.get_module_name())))
        clean_view.pump(0.5)
    try:
        plugin_obj = clean_view.widget('plugin-MiAZAutoScan')
        calls = []
        plugin_obj._list_devices = lambda: calls.append(1) or []
        page = clean_view.widget('repository-settings-page-settings')
        assert calls == [], 'the device was probed just by opening the dialog'
        notebook = clean_view.widget('repository-settings-notebook')
        notebook.set_current_page(_page_number(notebook, page))
        clean_view.pump(0.4)
        assert calls != [], 'showing the tab did not build the group'
    finally:
        if system.is_plugin_loaded(info) != started_loaded:
            system.unload_plugin(info)
            clean_view.pump(0.4)
