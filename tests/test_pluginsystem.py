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
