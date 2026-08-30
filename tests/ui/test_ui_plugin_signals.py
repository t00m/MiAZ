#!/usr/bin/python3

"""UI: no plugin keeps listening after it is unloaded.

A widget left behind is visible. A handler left behind is not: the plugin is
gone and nothing happens until the workspace emits and a dead object answers.
Emitting and watching for a traceback is not enough either, since a leaked
handler often runs to the end without raising and only corrupts state.

So this counts the handlers on the objects that outlive a plugin, using
g_signal_handler_find over unblocked handlers, and asserts the count comes
back to where it started. That is the same question asked of memory: did the
plugin let go of everything it took hold of.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject

import pytest


PLUGINS = [
    'MiAZAIAssistant', 'MiAZAutoScan', 'MiAZColumnVisibility',
    'MiAZExport2CSV', 'MiAZExport2Dir', 'MiAZExport2Text',
    'MiAZExport2Zip', 'MiAZFullscreen', 'MiAZImportFromScan',
    'MiAZImportFromZip', 'MiAZInsights', 'MiAZNotes', 'MiAZOCR',
    'MiAZPeriodicity', 'MiAZProjectMgt', 'MiAZWSFont',
]

# Signal by signal, the objects a plugin can reach that outlive it.
WATCHED = {
    'workspace': ('workspace-loaded', 'workspace-view-updated',
                  'workspace-view-filtered', 'workspace-view-selection-changed'),
    'util': ('filename-added', 'filename-renamed', 'filename-deleted'),
    'actions': ('settings-loaded', 'rename-dialog-built'),
    'repo': ('repository-switched',),
    'workflow': ('repository-switch-started', 'repository-switch-finished'),
    'plugin-system': ('plugins-updated',),
}
CONFIGS = ('Country', 'Group', 'Purpose', 'SentBy', 'SentTo', 'Plugin')


def count_handlers(obj, signal_name):
    """How many handlers are connected to this signal right now.

    There is no call that answers this. signal_handler_find returns one match,
    so each one found is blocked to take it out of the running and unblocked
    again afterwards, which leaves the object exactly as it was.
    """
    try:
        signal_id, detail = GObject.signal_parse_name(signal_name, obj, True)
    except (TypeError, ValueError):
        return 0
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


def handler_census(driver):
    """The handler count of every watched signal, as one comparable dict."""
    census = {}
    for name, signals in WATCHED.items():
        obj = driver.widget(name) if name == 'workspace' else driver.service(name)
        if obj is None:
            continue
        for signal in signals:
            census[f'{name}.{signal}'] = count_handlers(obj, signal)
    for name in CONFIGS:
        config = driver.app.get_config(name)
        if config is None:
            continue
        for signal in ('used-updated', 'available-updated'):
            census[f'config[{name}].{signal}'] = count_handlers(config, signal)
    return census


def drift(after, before):
    return {key: (before[key], after[key])
            for key in before if after.get(key) != before[key]}


def find(system, name):
    return next((info for info in system.plugins if info.get_name() == name), None)


@pytest.mark.parametrize('plugin_name', PLUGINS)
def test_a_plugin_disconnects_everything_it_connected(miaz, plugin_name):
    """Load, count, unload, count. The two counts must agree."""
    system = miaz.service('plugin-system')
    info = find(system, plugin_name)
    assert info is not None

    started_loaded = system.is_plugin_loaded(info)
    if started_loaded:
        system.unload_plugin(info)
        miaz.pump(0.4)

    before = handler_census(miaz)

    if not system.load_plugin(info):
        pytest.skip(f'{plugin_name} cannot load here')
    miaz.pump(0.5)
    loaded = handler_census(miaz)

    system.unload_plugin(info)
    miaz.pump(0.5)
    after = handler_census(miaz)

    try:
        moved = drift(after, before)
        assert not moved, (
            f'{plugin_name} left handlers connected after unload '
            f'(before, after): {moved}')
    finally:
        if started_loaded:
            system.load_plugin(info)
            miaz.pump(0.4)


# The plugins that do connect to something long lived while they run. Most
# only add a menu entry and act when it is chosen, so their census is flat and
# the test above would pass for them even if it were broken. These make it
# fail if the counting itself stops working.
CONNECTORS = ['MiAZNotes', 'MiAZPeriodicity', 'MiAZProjectMgt',
              'MiAZColumnVisibility', 'MiAZFullscreen', 'MiAZInsights']


@pytest.mark.parametrize('plugin_name', CONNECTORS)
def test_the_census_sees_a_plugin_connecting(miaz, plugin_name):
    """Proof the measurement works: these raise the count while they run."""
    system = miaz.service('plugin-system')
    info = find(system, plugin_name)
    assert info is not None

    started_loaded = system.is_plugin_loaded(info)
    if started_loaded:
        system.unload_plugin(info)
        miaz.pump(0.4)

    before = handler_census(miaz)
    if not system.load_plugin(info):
        pytest.skip(f'{plugin_name} cannot load here')
    miaz.pump(0.5)
    try:
        assert drift(handler_census(miaz), before), \
            f'{plugin_name} connected nothing the census can see'
    finally:
        if not started_loaded:
            system.unload_plugin(info)
        miaz.pump(0.4)
