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
#
# The window and its key controller are here because a plugin that only
# connects to the workspace's own signals is not the only kind. MiAZFullscreen
# connects to neither: it follows the window's fullscreen state and takes F11
# from the window controller, and until both were watched the census could not
# see it run at all.
WATCHED = {
    'workspace': ('workspace-loaded', 'workspace-view-updated',
                  'workspace-view-filtered', 'workspace-view-selection-changed'),
    'util': ('filename-added', 'filename-renamed', 'filename-deleted'),
    'actions': ('settings-loaded', 'rename-dialog-built'),
    'repo': ('repository-switched',),
    'workflow': ('repository-switch-started', 'repository-switch-finished'),
    'plugin-system': ('plugins-updated',),
    'window': ('notify::fullscreened',),
    'window-event-controller': ('key-pressed',),
}

# The widgets a plugin can attach an event controller to and that outlive it.
# A leaked controller is the same bug as a leaked handler and is invisible in
# the same way: the plugin is gone, and a right click still reaches it.
# MiAZColumnVisibility connects no watched signal at all. It puts a
# GestureClick on the column view, which is the only trace it leaves.
CONTROLLED = ('window', 'column-view')

CONFIGS = ('Country', 'Group', 'Purpose', 'SentBy', 'SentTo', 'Plugin')


def watched_object(driver, name):
    """The object a watched name means: some are widgets, some are services.

    The column view has no key of its own. It is reached through the workspace
    view, which is the same path the plugin attaching to it takes.
    """
    if name == 'column-view':
        view = driver.widget('workspace-view')
        return getattr(view, 'cv', None) if view is not None else None
    widget = driver.widget(name)
    return widget if widget is not None else driver.service(name)


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
    if detail:
        # Without this, 'notify::fullscreened' counts every notify handler on
        # the window, 24 of them, and one plugin connecting is lost in the
        # noise the moment anything else connects or disconnects a notify.
        match |= GObject.SignalMatchType.DETAIL
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


def count_controllers(widget):
    """How many event controllers are attached to this widget right now."""
    try:
        return len(widget.observe_controllers())
    except AttributeError:
        return 0


def handler_census(driver):
    """The handler count of every watched signal, as one comparable dict."""
    census = {}
    for name, signals in WATCHED.items():
        obj = watched_object(driver, name)
        if obj is None:
            continue
        for signal in signals:
            census[f'{name}.{signal}'] = count_handlers(obj, signal)
    for name in CONTROLLED:
        widget = watched_object(driver, name)
        if widget is None:
            continue
        census[f'{name}.controllers'] = count_controllers(widget)
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
