#!/usr/bin/python3

"""UI: plugins keeping the shared containers tidy. Checklist section 10.

scripts/devel/check_plugin_ui.py did this by hand and printed a report. These
run the same cycles and assert, so a regression fails a build instead of
waiting for someone to read the output.
"""

import pytest

# Plugins that contribute to shared UI, and the workspace page each adds.
CONTRIBUTORS = {
    'MiAZNotes': 'notes-all',
    'MiAZProjectMgt': None,
    'MiAZPeriodicity': None,
    'MiAZFullscreen': None,
}


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
    """What the shared containers hold right now."""
    workspace = driver.workspace
    stack = workspace.get_stack()
    names = []
    child = stack.get_first_child()
    while child is not None:
        page = stack.get_page(child)
        if page is not None:
            names.append(page.get_name())
        child = child.get_next_sibling()
    return {
        'pages': sorted(names),
        'sidebar': children(driver.widget('sidebar-plugin-section')),
        'headerbar_left': children(driver.widget('headerbar-left-box')),
        'headerbar_right': children(driver.widget('headerbar-right-box')),
        'dropdowns': len(driver.widget('plugin-dropdowns') or []),
    }


def find_plugin(system, name):
    for info in system.plugins:
        if info.get_name() == name:
            return info
    return None


@pytest.mark.parametrize('plugin_name', sorted(CONTRIBUTORS))
def test_a_plugin_gives_back_what_it_added(miaz, plugin_name):
    """10.2 to 10.5: disable and enable twice, and end where we started."""
    system = miaz.service('plugin-system')
    info = find_plugin(system, plugin_name)
    if info is None or not info.is_loaded():
        pytest.skip(f'{plugin_name} is not enabled in this repository')

    before = snapshot(miaz)

    system.unload_plugin(info)
    miaz.pump(0.5)
    unloaded = snapshot(miaz)

    system.load_plugin(info)
    miaz.pump(0.5)
    assert snapshot(miaz) == before, f'{plugin_name} did not restore its UI'

    # Twice, because a second cycle is what caught the stale widget keys.
    system.unload_plugin(info)
    miaz.pump(0.5)
    system.load_plugin(info)
    miaz.pump(0.5)
    assert snapshot(miaz) == before, f'{plugin_name} broke on the second cycle'

    # And it really did take something away in between, otherwise the check
    # above proves nothing.
    contributed = any(before[key] != unloaded[key] for key in before)
    assert contributed, f'{plugin_name} contributes nothing to shared UI'


def test_a_page_plugin_removes_its_page(miaz):
    """10.2: the page goes, rather than lingering hidden in the stack."""
    system = miaz.service('plugin-system')
    info = find_plugin(system, 'MiAZNotes')
    if info is None or not info.is_loaded():
        pytest.skip('MiAZNotes is not enabled in this repository')

    assert 'notes-all' in snapshot(miaz)['pages']
    system.unload_plugin(info)
    miaz.pump(0.5)
    try:
        assert 'notes-all' not in snapshot(miaz)['pages']
    finally:
        system.load_plugin(info)
        miaz.pump(0.5)
    assert 'notes-all' in snapshot(miaz)['pages']


def test_every_enabled_plugin_reports_itself(miaz):
    """10.1: the plugin manager knows what is loaded, with a description."""
    system = miaz.service('plugin-system')
    loaded = [info for info in system.plugins if info.is_loaded()]
    assert loaded, 'no plugin is enabled in this repository'
    for info in loaded:
        assert info.get_name()
        assert info.get_description()
