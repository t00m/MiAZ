#!/usr/bin/python3

"""UI: the Repository Settings dialog.

Per-repository settings used to be split across three places: an inline group
in the Application Settings dialog, a per-plugin dialog behind a button in the
Plugins tab, and nothing at all for the rest. These check they arrive in one.
"""

from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import GObject
from gi.repository import Gtk

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


def test_the_tabs_show_their_names(repo_settings, clean_view):
    """The three tab labels used to render as an icon and three dots.

    factory.create_label ellipsizes every label it builds, so the label's
    minimum width was one ellipsis, and a notebook hands a tab its minimum.
    The width is measured rather than the ellipsize setting read: what matters
    is that the name is actually legible, however it comes to be.
    """
    notebook = clean_view.widget('repository-settings-notebook')
    assert notebook.get_n_pages() == 3
    for number in range(notebook.get_n_pages()):
        box = notebook.get_tab_label(notebook.get_nth_page(number))
        label = box.get_last_child()
        text = label.get_text()
        assert text, f'tab {number} has no label text'
        # measure() returns four values: the two baselines are not wanted here.
        minimum, natural = label.measure(Gtk.Orientation.HORIZONTAL, -1)[:2]
        assert minimum == natural, (
            f'tab {number} ({text!r}) can shrink to {minimum}px against a '
            f'natural {natural}px, so the notebook will cut it to an ellipsis')


def test_the_settings_tab_groups_by_category(repo_settings, clean_view):
    """One page per category, not one scroll of every group.

    With every plugin enabled the single page stacked ten groups, and the AI
    assistant's alone holds an expander per provider. The categories are the
    ones the registry already sorts its builders by, so this asserts the list
    against the registry rather than against a hardcoded set of names.
    """
    page = clean_view.widget('repository-settings-page-settings')
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)

    names = page.get_page_names()
    assert names[0] == 'Repository-self', (
        f'the repository page is not first: {names}')

    registry = clean_view.service('plugin-system').settings
    expected = {category for category, _owner, _builder in registry.builders()}
    plugin_pages = set(names[1:]) - {'Other'}
    assert plugin_pages == expected, (
        f'category pages {plugin_pages} do not match the registry {expected}')


def test_an_empty_category_gets_no_page(repo_settings, clean_view):
    """A page is added on first use, so a category nothing registers under
    does not appear as an empty heading."""
    page = clean_view.widget('repository-settings-page-settings')
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)

    registry = clean_view.service('plugin-system').settings
    used = {category for category, _owner, _builder in registry.builders()}
    from MiAZ.frontend.desktop.services import pluginsystem as ps
    unused = set(ps.plugin_categories) - used
    assert unused, 'need a category nothing registers under to test this'
    for category in unused:
        assert not page.has_page(category), (
            f'{category} has no settings but got a page anyway')


def test_the_repository_page_survives_a_plugin_change(repo_settings, clean_view):
    """Plugin pages are thrown away and rebuilt when plugins change. The
    repository page is not a plugin's, and rebuilding it would lose whatever
    the user has half typed into the name row."""
    page = clean_view.widget('repository-settings-page-settings')
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)

    row_name = clean_view.widget('repository-settings-row-name')
    row_name.set_text('half typed')
    page._on_plugins_updated()
    clean_view.pump(0.3)

    assert page.has_page('Repository-self'), 'the repository page went away'
    assert clean_view.widget('repository-settings-row-name').get_text() == 'half typed'


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


def test_the_scanner_is_never_probed_by_the_settings_tab(repo_settings, clean_view):
    """Neither opening the dialog nor showing the Settings tab may run SANE.

    Probing wakes the scanner and took about four seconds on the main loop,
    which is most of what the tab used to cost to open. The plugin already
    probes once at startup, on a worker thread, to build its menu, so the
    settings group reads what that found instead of asking again.

    This asserted the opposite of its second half once: that showing the tab
    DID probe, as a stand-in for the group being built late rather than early.
    That the group is built late is pinned by
    test_nothing_is_built_until_the_tab_is_shown, so this one is free to say
    the thing it is named for. The group still has to be built, or "nothing
    was probed" would also be true of doing nothing at all, so that is checked
    too.

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
        assert calls == [], 'showing the Settings tab probed the scanner'
        assert page.is_built(), 'the tab was shown but nothing was built'
        assert 'Scanner settings' in group_titles(page), (
            'the scanner group is missing, so "nothing was probed" only means '
            'nothing was built')
    finally:
        if system.is_plugin_loaded(info) != started_loaded:
            system.unload_plugin(info)
            clean_view.pump(0.4)


def group_titles(widget):
    """The title of every Adw.PreferencesGroup anywhere under `widget`.

    Mirrors row_titles, but for groups: build_legacy_rows files its Configure
    rows under an 'Other plugins' group, and that title is on the group, not
    on a row.
    """
    found = []
    if isinstance(widget, Adw.PreferencesGroup):
        found.append(widget.get_title())
    child = widget.get_first_child()
    while child is not None:
        found.extend(group_titles(child))
        child = child.get_next_sibling()
    return found


def find_group(widget, title):
    """The first Adw.PreferencesGroup anywhere under `widget` with this title.

    Used to scope a row search to one specific group, rather than the whole
    page: a plugin name and some unrelated row's title could otherwise
    collide and make a check pass for the wrong reason.
    """
    if isinstance(widget, Adw.PreferencesGroup) and widget.get_title() == title:
        return widget
    child = widget.get_first_child()
    while child is not None:
        found = find_group(child, title)
        if found is not None:
            return found
        child = child.get_next_sibling()
    return None


def find_button_label(widget):
    """The label of the first Gtk.Button found anywhere under `widget`."""
    if isinstance(widget, Gtk.Button):
        return widget.get_label()
    child = widget.get_first_child()
    while child is not None:
        label = find_button_label(child)
        if label is not None:
            return label
        child = child.get_next_sibling()
    return None


def test_the_plugins_tab_has_no_configure_button(repo_settings, clean_view):
    """The Plugins tab enables and disables plugins. Configuring them is the
    Settings tab's job, and two buttons for one thing is how they drifted
    apart in the first place."""
    plugins_view = clean_view.widget('configview-Plugin')
    assert not hasattr(plugins_view, 'btnConfig'), 'the config button is still there'


def test_a_plugin_with_only_show_settings_still_gets_a_row(repo_settings, clean_view):
    """The compatibility shim, for a plugin written against the older API
    (show_settings(), called from a button the Plugins tab used to have).

    Every bundled plugin with settings now has a real install_settings_group()
    builder, so the expected set here is worked out from the running
    application rather than hardcoded: whatever is loaded, has a callable
    show_settings(), and is not already offered through the registry is what
    the shim is for, and that is what must show up as a row. That set is
    empty for every bundled plugin today, so this only covers the negative
    branch, no shim group at all; see
    test_a_stand_in_plugin_gets_a_configure_row for the positive one.
    """
    plugin_system = clean_view.service('plugin-system')
    registry = plugin_system.settings
    offered = {owner for _category, owner, _builder in registry.builders()}

    expected = set()
    for plugin_info in plugin_system.plugins:
        if not plugin_system.is_plugin_loaded(plugin_info):
            continue
        name = plugin_info.get_name()
        if name in offered:
            continue
        plugin_obj = clean_view.widget(f'plugin-{name}')
        if plugin_obj is None or not callable(getattr(plugin_obj, 'show_settings', None)):
            continue
        expected.add(name)

    page = clean_view.widget('repository-settings-page-settings')
    notebook = clean_view.widget('repository-settings-notebook')
    notebook.set_current_page(_page_number(notebook, page))
    clean_view.pump(0.4)
    groups = group_titles(page)

    if not expected:
        assert _('Other plugins') not in groups, \
            'a shim group appeared with nothing that needs it: ' + str(groups)
        return

    other_group = find_group(page, _('Other plugins'))
    assert other_group is not None, 'no Other plugins group appeared: ' + str(groups)
    # Scoped to the shim's own group, not the whole page: a plugin name
    # matching some unrelated row's title elsewhere would otherwise pass
    # for the wrong reason.
    shown = expected & set(row_titles(other_group))
    assert shown == expected, (shown, expected)


def test_a_stand_in_plugin_gets_a_configure_row(repo_settings, clean_view, monkeypatch):
    """Positive-path coverage for build_legacy_rows.

    No bundled plugin is in the show_settings()-but-no-builder state any
    more, so this registers a stand-in to exercise the branch instead of
    relying on one that happens to qualify.

    plugin_system.plugins is a plain Python property reading the libpeas
    engine, which only ever lists .plugin files found on disk, so the
    stand-in is added by patching that property on the class rather than
    trying to inject a real Peas.PluginInfo. monkeypatch restores the
    property automatically; the widget registration is removed by hand in
    the finally block, since that dictionary is on the session-scoped app
    and would otherwise leak into every test that runs after this one.
    """
    plugin_system = clean_view.service('plugin-system')

    class StandInPluginInfo:
        def get_name(self):
            return 'StandInLegacyPlugin'

        def get_module_name(self):
            return 'standinlegacyplugin'

        def is_loaded(self):
            return True

    class StandInPlugin:
        def show_settings(self, widget=None):
            pass

    real_plugins = plugin_system.plugins
    patched_plugins = real_plugins + [StandInPluginInfo()]
    monkeypatch.setattr(type(plugin_system), 'plugins',
                        property(lambda self: patched_plugins))
    clean_view.app.add_widget('plugin-StandInLegacyPlugin', StandInPlugin())
    try:
        page = clean_view.widget('repository-settings-page-settings')
        notebook = clean_view.widget('repository-settings-notebook')
        notebook.set_current_page(_page_number(notebook, page))
        clean_view.pump(0.4)

        groups = group_titles(page)
        assert _('Other plugins') in groups, groups
        other_group = find_group(page, _('Other plugins'))
        assert other_group is not None
        titles = row_titles(other_group)
        assert 'StandInLegacyPlugin' in titles, titles
        assert find_button_label(other_group) == _('Configure'), \
            'no Configure button in the shim row'
    finally:
        clean_view.app.remove_widget('plugin-StandInLegacyPlugin')


def test_the_dialog_has_three_tabs(repo_settings, clean_view):
    notebook = clean_view.widget('repository-settings-notebook')
    assert notebook.get_n_pages() == 3, 'expected Metadata, Plugins, Settings'


def test_the_metadata_tab_lists_the_five_built_in_types(repo_settings, clean_view):
    """The five built-in types come first, in this exact order. A plugin
    that owns a vocabulary of its own (MiAZPeriodicity, MiAZProjectMgt in
    this sandbox) is free to add more after them, so this does not require
    the whole list to be just those five; it does require that whatever
    else is there is accounted for, by checking every remaining name against
    the plugin system's own record of who registered a metadata view, rather
    than only checking the list is no longer than before.
    test_a_plugin_vocabulary_joins_the_metadata_list below checks that
    Periodicity and Projects specifically are among them."""
    page = clean_view.widget('repository-settings-page-metadata')
    assert page is not None, 'no Metadata tab'
    names = page.get_view_names()
    assert names[:5] == ['Country', 'Group', 'Purpose', 'SentBy', 'SentTo']
    registry = clean_view.service('plugin-system').settings
    registered = {name for _owner, name, _title, _icon, _factory
                 in registry.views()}
    extra = names[5:]
    assert set(extra) <= registered, (extra, registered)


def test_choosing_a_metadata_type_switches_the_stack(repo_settings, clean_view):
    page = clean_view.widget('repository-settings-page-metadata')
    page.show_view('Purpose')
    clean_view.pump(0.2)
    assert page.stack.get_visible_child_name() == 'Purpose'


def test_a_plugin_vocabulary_joins_the_metadata_list(repo_settings, clean_view):
    """MiAZPeriodicity and MiAZProjectMgt own a vocabulary each. Both used to
    show it in a dialog of their own, reached from a button in the Plugins
    tab, which put a repository vocabulary two dialogs deep."""
    page = clean_view.widget('repository-settings-page-metadata')
    names = page.get_view_names()
    assert names[:5] == ['Country', 'Group', 'Purpose', 'SentBy', 'SentTo']
    assert 'Periodicity' in names, names
    assert 'Projects' in names, names


def test_a_bogus_icon_name_does_not_show_a_broken_image(repo_settings, clean_view):
    """install_metadata_view is public API: an out-of-tree plugin can pass
    any icon_name it likes, and a typo or an asset that was never shipped
    must not put a broken-image glyph in the list. add_view is called
    directly here with a name no theme has, rather than going through a
    plugin, since the point is add_view's own fallback, not a plugin's."""
    page = clean_view.widget('repository-settings-page-metadata')
    bogus = 'io.github.t00m.MiAZ-res-does-not-exist'
    page.add_view('Bogus', 'Bogus', bogus, Gtk.Label())
    clean_view.pump(0.2)
    row = page.listbox.get_row_at_index(len(page.get_view_names()) - 1)
    icon = row.get_child().get_first_child()
    assert isinstance(icon, Gtk.Image)
    assert icon.get_icon_name() != bogus, \
        'the bogus name reached the widget unchanged'
    assert icon.get_icon_name() == 'io.github.t00m.MiAZ-res-plugins'


def test_the_manage_menu_entry_opens_the_metadata_tab(clean_view):
    """Ctrl+Alt+P used to present a second copy of the same view."""
    plugin_obj = clean_view.widget('plugin-MiAZProjectMgt')
    if plugin_obj is None:
        pytest.skip('MiAZProjectMgt is not enabled in this repository')
    plugin_obj._manage_properties()
    clean_view.pump(0.5)
    window = clean_view.widget('window-repo-settings')
    assert window is not None, 'the repository settings window did not open'
    page = clean_view.widget('repository-settings-page-metadata')
    assert page.stack.get_visible_child_name() == 'Projects'
    window.close()
    clean_view.pump(0.3)


def test_closing_the_settings_window_refreshes_the_projects_tab(
        clean_view, monkeypatch):
    """MiAZProjectTab's manage button used to open a dialog and connect to
    its 'closed' signal to rebuild the tick list once the user was done.
    Repository Settings is a window, not a dialog, and has no 'closed'
    signal, only 'close-request'; a show_manager that returned None (as an
    early version of it did) or a caller that still connected to 'closed'
    would both fail exactly this way: the button opens the window, but the
    tab's own list never refreshes when it closes, silently.
    """
    plugin_obj = clean_view.widget('plugin-MiAZProjectMgt')
    if plugin_obj is None:
        pytest.skip('MiAZProjectMgt is not enabled in this repository')
    tabs = clean_view.service('document-tabs')
    registration = next((reg for reg in tabs.get_registrations()
                         if reg['name'] == 'projects'), None)
    if registration is None:
        pytest.skip('the projects tab is not registered')
    tab = registration['factory'](clean_view.app)

    # show_manager must hand back the window it opened, not None: the method
    # it replaced returned its dialog for exactly this reason, and a caller
    # that gets nothing back has nothing to connect to.
    first_window = plugin_obj.show_manager(widget=tab)
    assert first_window is not None, \
        'show_manager must return the settings window, not None'
    assert first_window is clean_view.widget('window-repo-settings')
    first_window.close()
    clean_view.pump(0.3)

    # The real path: the manage button's own click handler, which is what
    # silently stopped refreshing the tab when show_manager returned None
    # and the caller tried to connect 'closed' to a window that has no such
    # signal.
    calls = []
    monkeypatch.setattr(tab, '_build_rows', lambda: calls.append(1))
    tab._on_manage_clicked()
    clean_view.pump(0.5)
    window = clean_view.widget('window-repo-settings')
    assert window is not None, 'the settings window did not open'

    window.close()
    clean_view.pump(0.3)

    assert calls, ('closing the settings window did not rebuild the '
                   'projects tick list')
