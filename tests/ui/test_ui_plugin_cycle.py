#!/usr/bin/python3

"""UI: every plugin gives back what it took, and starts clean the next time.

test_ui_plugins.py cycles the four plugins that contribute obvious widgets.
This one cycles every plugin the sandbox can load, and looks at more than
widgets: the menus, the rename-dialog tabs, and whether the long-lived signals
a plugin listens to still fire safely once it is gone.

A plugin that leaks a handler does not fail on unload. It fails later, when
the workspace emits and a dead object answers, which is how the column
visibility crash reached a release.
"""

import gi
gi.require_version('Gtk', '4.0')

import pytest

from tests.menutree import menu_actions


def children(widget):
    if widget is None:
        return 0
    count = 0
    child = widget.get_first_child()
    while child is not None:
        count += 1
        child = child.get_next_sibling()
    return count


def snapshot(driver):
    """Everything shared that a plugin can touch."""
    stack = driver.workspace.get_stack()
    pages = []
    child = stack.get_first_child()
    while child is not None:
        page = stack.get_page(child)
        if page is not None:
            pages.append(page.get_name())
        child = child.get_next_sibling()

    seen, keep = set(), []
    actions = []
    for key in ('workspace-menu-selection', 'workspace-menu-single',
                'workspace-plugins-section', 'window-menu-app',
                'headerbar-add-menu'):
        actions.extend(menu_actions(driver.widget(key), seen, keep))

    tabs = driver.service('document-tabs')
    return {
        'pages': sorted(pages),
        'menu': sorted(actions),
        'sidebar': children(driver.widget('sidebar-plugin-section')),
        'headerbar_left': children(driver.widget('headerbar-left-box')),
        'headerbar_right': children(driver.widget('headerbar-right-box')),
        'dropdowns': len(driver.widget('plugin-dropdowns') or []),
        'doctabs': sorted(f"{tab['owner']}:{tab['title']}"
                          for tab in tabs.get_registrations()) if tabs else [],
    }


def settled(driver, tries=25):
    """Snapshot once the shared state stops moving.

    Some plugins install their menu when a background job finishes: the
    scanner one lists a submenu of sources after probing the device. Without
    waiting for that, a snapshot taken mid-detection differs from the next one
    for reasons that have nothing to do with the plugin under test.
    """
    previous = snapshot(driver)
    for _attempt in range(tries):
        driver.pump(0.2)
        current = snapshot(driver)
        if current == previous:
            return current
        previous = current
    return previous


def compare(now, expected, message):
    """Fail naming the key that drifted, not with two truncated dicts."""
    drift = []
    for key in sorted(expected):
        if now[key] != expected[key]:
            drift.append(f'  {key}: {expected[key]!r} -> {now[key]!r}')
    if drift:
        raise AssertionError(message + '\n' + '\n'.join(drift))


def loadable(system):
    """The plugins this sandbox can actually load, by name."""
    names = []
    for info in system.plugins:
        name = info.get_name()
        if name == 'HelloWorld':
            # The sample plugin, not shipped behaviour worth asserting on.
            continue
        names.append(name)
    return sorted(names)


def find(system, name):
    for info in system.plugins:
        if info.get_name() == name:
            return info
    return None


@pytest.fixture(scope='module')
def plugin_names(miaz):
    return loadable(miaz.service('plugin-system'))


def test_the_sandbox_can_see_every_bundled_plugin(miaz, plugin_names):
    """If this drops, the cycle test below is quietly covering less."""
    assert len(plugin_names) >= 16


@pytest.mark.parametrize('plugin_name', [
    'MiAZAIAssistant', 'MiAZAutoScan', 'MiAZColumnVisibility',
    'MiAZExport2CSV', 'MiAZExport2Dir', 'MiAZExport2Text',
    'MiAZExport2Zip', 'MiAZFullscreen', 'MiAZImportFromScan',
    'MiAZImportFromZip', 'MiAZInsights', 'MiAZOCR', 'MiAZOikos',
    'MiAZPeriodicity', 'MiAZProjectMgt', 'MiAZWSFont',
])
def test_a_plugin_survives_two_cycles(miaz, plugin_name):
    """Load, unload, load, unload, load. The shared state must not drift.

    Every plugin is included, not only the ones with visible widgets: a plugin
    that adds nothing to a container can still leave a menu entry, a rename
    tab or a handler behind.
    """
    system = miaz.service('plugin-system')
    info = find(system, plugin_name)
    assert info is not None, f'{plugin_name} is not in the plugin index'

    started_loaded = system.is_plugin_loaded(info)
    if not started_loaded:
        if not system.load_plugin(info):
            pytest.skip(f'{plugin_name} cannot load here: '
                        f'{system.get_load_error(info.get_module_name())}')
        miaz.pump(0.5)

    try:
        loaded = settled(miaz)

        system.unload_plugin(info)
        unloaded = settled(miaz)

        assert system.load_plugin(info), f'{plugin_name} did not load again'
        compare(settled(miaz), loaded,
                f'{plugin_name} came back different after one cycle')

        system.unload_plugin(info)
        compare(settled(miaz), unloaded,
                f'{plugin_name} left more behind on the second unload')

        assert system.load_plugin(info), f'{plugin_name} did not load a third time'
        compare(settled(miaz), loaded,
                f'{plugin_name} came back different after two cycles')
    finally:
        if system.is_plugin_loaded(info) != started_loaded:
            if started_loaded:
                system.load_plugin(info)
            else:
                system.unload_plugin(info)
            miaz.pump(0.4)


# The action and the accelerator are the two things unload_plugin used to
# leave behind. MiAZProjectMgt is the plugin that shows it: it declares three
# shortcuts, and <Control>p went on firing a handler whose service was gone.
PROJECT_ACTIONS = ('plugin-menuitem-MiAZProjectMgt-assign',
                   'plugin-menuitem-MiAZProjectMgt-unassign',
                   'plugin-menuitem-MiAZProjectMgt-manage')


def test_a_plugin_takes_its_actions_and_shortcuts_with_it(miaz):
    system = miaz.service('plugin-system')
    info = find(system, 'MiAZProjectMgt')
    assert info is not None

    if not system.is_plugin_loaded(info):
        assert system.load_plugin(info)
        miaz.pump(0.4)

    app = miaz.app
    for name in PROJECT_ACTIONS:
        assert app.lookup_action(name) is not None, f'{name} was never registered'
    assert app.get_accels_for_action('app.plugin-menuitem-MiAZProjectMgt-assign') \
        == ['<Control>p']

    system.unload_plugin(info)
    miaz.pump(0.4)
    try:
        for name in PROJECT_ACTIONS:
            assert app.lookup_action(name) is None, f'{name} outlived the plugin'
            assert app.get_accels_for_action(f'app.{name}') == [], \
                f'{name} kept its shortcut'
    finally:
        assert system.load_plugin(info)
        miaz.pump(0.4)

    for name in PROJECT_ACTIONS:
        assert app.lookup_action(name) is not None, f'{name} did not come back'


def test_a_plugin_takes_its_widget_keys_with_it(miaz):
    """A key left pointing at a detached widget is the trap register_widget
    was written for: the next activation finds the old one and does nothing."""
    system = miaz.service('plugin-system')
    info = find(system, 'MiAZProjectMgt')
    assert info is not None

    if not system.is_plugin_loaded(info):
        assert system.load_plugin(info)
        miaz.pump(0.4)

    keys = ('plugin-MiAZProjectMgt',
            'plugin-menuitem-MiAZProjectMgt',
            'plugin-menuitem-MiAZProjectMgt-assign')
    for key in keys:
        assert miaz.widget(key) is not None, f'{key} was never registered'

    system.unload_plugin(info)
    miaz.pump(0.4)
    try:
        for key in keys:
            assert miaz.widget(key) is None, f'{key} outlived the plugin'
    finally:
        assert system.load_plugin(info)
        miaz.pump(0.4)

    for key in keys:
        assert miaz.widget(key) is not None, f'{key} did not come back'
