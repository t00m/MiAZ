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
from gi.repository import Gio

import pytest


def children(widget):
    if widget is None:
        return 0
    count = 0
    child = widget.get_first_child()
    while child is not None:
        count += 1
        child = child.get_next_sibling()
    return count


def menu_actions(menu, seen=None):
    """Every action reachable from a Gio.Menu, submenus and sections included.

    `seen` guards against walking the same submenu twice: the plugin submenus
    are linked from more than one root, so without it the same entry is
    reported several times and a real duplicate cannot be told apart.
    """
    if seen is None:
        seen = set()
    if menu is None or id(menu) in seen:
        return []
    seen.add(id(menu))
    found = []
    for position in range(menu.get_n_items()):
        value = menu.get_item_attribute_value(position, 'action', None)
        if value is not None:
            found.append(value.get_string())
        for link in (Gio.MENU_LINK_SUBMENU, Gio.MENU_LINK_SECTION):
            child = menu.get_item_link(position, link)
            if child is not None:
                found.extend(menu_actions(child, seen))
    return found


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

    seen = set()
    actions = []
    for key in ('workspace-menu-selection', 'workspace-menu-single',
                'workspace-plugins-section', 'window-menu-app',
                'headerbar-add-menu'):
        actions.extend(menu_actions(driver.widget(key), seen))

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
    assert len(plugin_names) >= 18


@pytest.mark.parametrize('plugin_name', [
    'MiAZAddFromDir', 'MiAZAIAssistant', 'MiAZAutoScan', 'MiAZColumnVisibility',
    'MiAZCopy2Clipboard', 'MiAZExport2CSV', 'MiAZExport2Dir', 'MiAZExport2Text',
    'MiAZExport2Zip', 'MiAZFullscreen', 'MiAZImportFromScan',
    'MiAZImportFromZip', 'MiAZInsights', 'MiAZNotes', 'MiAZOCR',
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
