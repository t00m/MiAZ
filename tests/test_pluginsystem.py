#!/usr/bin/python3

"""
Unit tests for the pure load-failure text formatters in the plugin system.

The module imports gi/Peas, so the test sets the versions first (the app does
the same). The formatters are module-level and side-effect free, so importing
the module needs no running app and no display.
"""

import gi
gi.require_version('Peas', '2')
gi.require_version('Gtk', '4.0')

from MiAZ.frontend.desktop.services import pluginsystem as ps
from MiAZ.backend.log import MiAZLog


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


# ---------------------------------------------------------------------------
# Plugin source directory and icon
# ---------------------------------------------------------------------------

import os  # noqa: E402

import pytest  # noqa: E402


class FakeApp:
    """Just enough app for MiAZPlugin: services and the environment."""

    def __init__(self, env, services=None):
        self._env = env
        self._services = services or {}

    def get_env(self):
        return self._env

    def get_service(self, name):
        return self._services.get(name)


def make_env(system_dir, user_dir):
    return {'GPATH': {'PLUGINS': str(system_dir)}, 'LPATH': {'PLUGINS': str(user_dir)}}


def make_plugin(app, name='MiAZProjectMgt', module='projmgt'):
    plugin = ps.MiAZPlugin(app)
    # register() creates repository directories, which a unit test has no use
    # for; these two attributes are all it sets that matters here.
    plugin.info = {'Name': name, 'Module': module}
    plugin.name = name
    return plugin


@pytest.fixture
def dirs(tmp_path):
    system = tmp_path / 'system'
    user = tmp_path / 'user'
    system.mkdir()
    user.mkdir()
    return system, user


def test_source_dir_found_by_plugin_name(dirs):
    # The bundled layout: folder MiAZProjectMgt holding module projmgt.py.
    system, user = dirs
    (system / 'MiAZProjectMgt').mkdir()
    plugin = make_plugin(FakeApp(make_env(system, user)))
    assert plugin.get_source_dir() == str(system / 'MiAZProjectMgt')


def test_source_dir_found_by_module_name(dirs):
    system, user = dirs
    (system / 'projmgt').mkdir()
    plugin = make_plugin(FakeApp(make_env(system, user)))
    assert plugin.get_source_dir() == str(system / 'projmgt')


def test_source_dir_looks_in_the_user_directory_too(dirs):
    system, user = dirs
    (user / 'MiAZProjectMgt').mkdir()
    plugin = make_plugin(FakeApp(make_env(system, user)))
    assert plugin.get_source_dir() == str(user / 'MiAZProjectMgt')


def test_source_dir_is_none_when_nothing_matches(dirs):
    system, user = dirs
    plugin = make_plugin(FakeApp(make_env(system, user)))
    assert plugin.get_source_dir() is None


def test_icon_path_prefers_svg_over_png(dirs):
    system, user = dirs
    source = system / 'MiAZProjectMgt'
    source.mkdir()
    (source / 'icon.png').write_bytes(b'png')
    plugin = make_plugin(FakeApp(make_env(system, user)))
    assert plugin.get_icon_path() == str(source / 'icon.png')
    (source / 'icon.svg').write_text('<svg/>')
    assert plugin.get_icon_path() == str(source / 'icon.svg')


def test_icon_name_falls_back_to_the_default(dirs):
    system, user = dirs
    (system / 'MiAZProjectMgt').mkdir()
    plugin = make_plugin(FakeApp(make_env(system, user)))
    # No icon file shipped: every plugin still has an icon to show.
    assert plugin.get_icon_name() == ps.PLUGIN_DEFAULT_ICON


def test_icon_name_exports_the_plugin_icon(dirs, tmp_path):
    from MiAZ.frontend.desktop.services.icm import MiAZIconManager

    system, user = dirs
    source = system / 'MiAZProjectMgt'
    source.mkdir()
    (source / 'icon.svg').write_text('<svg/>')
    exported = tmp_path / 'icons'

    env = make_env(system, user)
    env['LPATH']['ICONS'] = str(exported)
    app = FakeApp(env)
    app._services['icons'] = MiAZIconManager(app)

    plugin = make_plugin(app)
    assert plugin.get_icon_name() == 'miaz-plugin-projmgt'
    assert os.path.isfile(exported / 'miaz-plugin-projmgt.svg')


# ---------------------------------------------------------------------------
# Workspace pages contributed by plugins
# ---------------------------------------------------------------------------

def test_a_new_registry_knows_about_nothing():
    registry = ps.PluginPageRegistry()
    assert registry.names('MiAZNotes') == []


def test_a_page_is_recorded_against_its_plugin():
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    assert registry.names('MiAZNotes') == ['notes-all']


def test_pages_of_other_plugins_are_not_returned():
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    assert registry.names('MiAZProjectMgt') == []


def test_a_plugin_can_contribute_several_pages():
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    registry.add('MiAZNotes', 'notes-archive')
    assert registry.names('MiAZNotes') == ['notes-all', 'notes-archive']


def test_adding_the_same_page_twice_records_it_once():
    """A plugin re-activated without a clean unload must not queue two removals
    for one page."""
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    registry.add('MiAZNotes', 'notes-all')
    assert registry.names('MiAZNotes') == ['notes-all']


def test_pop_all_returns_the_pages_and_forgets_them():
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    assert registry.pop_all('MiAZNotes') == ['notes-all']
    assert registry.names('MiAZNotes') == []


def test_pop_all_leaves_other_plugins_alone():
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    registry.add('MiAZProjectMgt', 'projects')
    registry.pop_all('MiAZNotes')
    assert registry.names('MiAZProjectMgt') == ['projects']


def test_pop_all_for_an_unknown_plugin_is_empty():
    registry = ps.PluginPageRegistry()
    assert registry.pop_all('NeverSeen') == []


def test_a_plugin_toggled_off_and_on_records_its_page_once():
    """The disable/enable cycle: unload pops the page, activation adds it back."""
    registry = ps.PluginPageRegistry()
    registry.add('MiAZNotes', 'notes-all')
    registry.pop_all('MiAZNotes')
    registry.add('MiAZNotes', 'notes-all')
    assert registry.names('MiAZNotes') == ['notes-all']


# ---------------------------------------------------------------------------
# Widgets contributed to shared containers (sidebar, headerbar)
# ---------------------------------------------------------------------------

def test_a_new_widget_registry_holds_nothing():
    registry = ps.PluginWidgetRegistry()
    assert registry.count('MiAZNotes') == 0


def test_an_undo_step_is_recorded_against_its_plugin():
    registry = ps.PluginWidgetRegistry()
    registry.add('MiAZNotes', lambda: None)
    assert registry.count('MiAZNotes') == 1
    assert registry.count('MiAZFullscreen') == 0


def test_undo_all_runs_the_steps():
    registry = ps.PluginWidgetRegistry()
    ran = []
    registry.add('MiAZNotes', lambda: ran.append('a'))
    registry.undo_all('MiAZNotes')
    assert ran == ['a']


def test_undo_all_runs_the_steps_in_reverse():
    """Teardown mirrors setup: the last thing added comes out first."""
    registry = ps.PluginWidgetRegistry()
    ran = []
    registry.add('MiAZNotes', lambda: ran.append('first'))
    registry.add('MiAZNotes', lambda: ran.append('second'))
    registry.undo_all('MiAZNotes')
    assert ran == ['second', 'first']


def test_undo_all_forgets_what_it_ran():
    registry = ps.PluginWidgetRegistry()
    ran = []
    registry.add('MiAZNotes', lambda: ran.append('a'))
    registry.undo_all('MiAZNotes')
    registry.undo_all('MiAZNotes')
    assert ran == ['a']
    assert registry.count('MiAZNotes') == 0


def test_undo_all_leaves_other_plugins_alone():
    registry = ps.PluginWidgetRegistry()
    ran = []
    registry.add('MiAZNotes', lambda: ran.append('notes'))
    registry.add('MiAZFullscreen', lambda: ran.append('fullscreen'))
    registry.undo_all('MiAZNotes')
    assert ran == ['notes']
    assert registry.count('MiAZFullscreen') == 1


def test_one_failing_step_does_not_strand_the_others():
    """A widget already detached must not leave the rest attached."""
    registry = ps.PluginWidgetRegistry()
    ran = []

    def boom():
        raise RuntimeError('already gone')

    registry.add('MiAZNotes', lambda: ran.append('first'))
    registry.add('MiAZNotes', boom)
    registry.add('MiAZNotes', lambda: ran.append('third'))
    registry.undo_all('MiAZNotes')
    assert ran == ['third', 'first']


def test_undo_all_for_an_unknown_plugin_does_nothing():
    registry = ps.PluginWidgetRegistry()
    registry.undo_all('NeverSeen')
    assert registry.count('NeverSeen') == 0


def test_a_toggled_plugin_does_not_accumulate_undo_steps():
    """Disable and enable repeatedly: one contribution, one undo step."""
    registry = ps.PluginWidgetRegistry()
    for _ in range(3):
        registry.add('MiAZFullscreen', lambda: None)
        registry.undo_all('MiAZFullscreen')
    assert registry.count('MiAZFullscreen') == 0

# ---------------------------------------------------------------------------
# Settings groups contributed by plugins
# ---------------------------------------------------------------------------

def test_a_new_settings_registry_knows_about_nothing():
    registry = ps.PluginSettingsRegistry()
    assert registry.builders() == []


def test_a_builder_is_recorded_with_its_category():
    registry = ps.PluginSettingsRegistry()
    def build():
        pass
    registry.add('MiAZOCR', 'Documents', build)
    assert registry.builders() == [('Documents', 'MiAZOCR', build)]


def test_builders_are_ordered_by_category_then_plugin():
    """The Settings tab reads them in this order, so it is the registry that
    decides where each group lands rather than the order plugins loaded in."""
    registry = ps.PluginSettingsRegistry()
    registry.add('MiAZWSFont', 'Interface', lambda: None)
    registry.add('MiAZOCR', 'Documents', lambda: None)
    registry.add('MiAZAutoScan', 'Documents', lambda: None)
    assert [(category, owner) for category, owner, _b in registry.builders()] == [
        ('Documents', 'MiAZAutoScan'),
        ('Documents', 'MiAZOCR'),
        ('Interface', 'MiAZWSFont'),
    ]


def test_a_plugin_can_contribute_several_groups():
    registry = ps.PluginSettingsRegistry()
    def first():
        pass
    def second():
        pass
    registry.add('MiAZNotes', 'Documents', first)
    registry.add('MiAZNotes', 'Documents', second)
    assert len(registry.builders()) == 2


def test_the_same_builder_twice_is_recorded_once():
    """A plugin re-activated without a clean unload must not show its group
    twice."""
    registry = ps.PluginSettingsRegistry()
    def build():
        pass
    registry.add('MiAZNotes', 'Documents', build)
    registry.add('MiAZNotes', 'Documents', build)
    assert registry.builders() == [('Documents', 'MiAZNotes', build)]


def test_forget_takes_one_plugin_away():
    registry = ps.PluginSettingsRegistry()
    def keep():
        pass
    registry.add('MiAZNotes', 'Documents', lambda: None)
    registry.add('MiAZWSFont', 'Interface', keep)
    registry.forget('MiAZNotes')
    assert registry.builders() == [('Interface', 'MiAZWSFont', keep)]


def test_forget_an_unknown_plugin_is_harmless():
    registry = ps.PluginSettingsRegistry()
    registry.forget('NeverSeen')
    assert registry.builders() == []

# ---------------------------------------------------------------------------
# MiAZPlugin contribution helpers
# ---------------------------------------------------------------------------

class FakeAppWithSettingsRegistry:
    """Enough app for MiAZPlugin's contribution helpers, with no display."""

    def __init__(self, registry):
        self._registry = registry
        self._services = {'plugin-system': type('S', (), {'settings': registry})()}

    def get_service(self, name):
        return self._services.get(name)


def a_plugin(registry, category='Documents', name='MiAZOCR'):
    plugin = ps.MiAZPlugin.__new__(ps.MiAZPlugin)
    plugin.app = FakeAppWithSettingsRegistry(registry)
    plugin.name = name
    plugin.info = {'Name': name, 'Category': category, 'Subcategory': 'Import'}
    plugin.log = MiAZLog('test')
    plugin._active = True
    return plugin


def test_install_settings_group_records_it_under_the_plugin_category():
    registry = ps.PluginSettingsRegistry()
    plugin = a_plugin(registry)
    def build():
        return None
    assert plugin.install_settings_group(build) is True
    assert registry.builders() == [('Documents', 'MiAZOCR', build)]


def test_an_unloaded_plugin_installs_nothing():
    """is_active goes false before do_deactivate runs, so a background job
    finishing late cannot add settings for a plugin that is gone."""
    registry = ps.PluginSettingsRegistry()
    plugin = a_plugin(registry)
    plugin.set_active(False)
    def build():
        return None
    assert plugin.install_settings_group(build) is False
    assert registry.builders() == []
