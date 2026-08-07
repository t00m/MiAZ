#!/usr/bin/python3

"""
Manual check: a plugin's UI contributions survive a disable/enable cycle.

The plugin system owns what a plugin adds to shared UI: workspace pages
(add_workspace_page), sidebar widgets (add_sidebar_widget,
add_sidebar_dropdown) and header bar widgets (add_headerbar_widget). It takes
them back in unload_plugin. None of that can be unit tested, because it needs a
real Adw.ViewStack, a display and a loaded repository, so this drives the cycle
in the running app and reports what each container held at every step.

Usage:

    PYTHONPATH=. python scripts/devel/check_plugin_ui.py [PluginName ...]

With no arguments it checks every plugin that contributes UI. Each named plugin
must be enabled in the active repository. The window opens, the checks run, and
it quits by itself.

PASS for one plugin means: whatever it contributed is gone after the unload, and
back in the same quantity after the reload, twice in a row. Watch the output for
GTK or Adw warnings about duplicate child names.
"""

import sys

# Plugins that contribute to shared UI, and the workspace page each adds.
DEFAULT_PLUGINS = {
    'MiAZNotes': 'notes-all',
    'MiAZProjectMgt': None,
    'MiAZPeriodicity': None,
    'MiAZFullscreen': None,
}


def children(widget):
    """Number of direct children of a Gtk container widget."""
    if widget is None:
        return None
    count = 0
    child = widget.get_first_child()
    while child is not None:
        count += 1
        child = child.get_next_sibling()
    return count


def stack_names(workspace):
    """Every child name in the workspace stack, hidden ones included."""
    stack = workspace.get_stack()
    names = []
    child = stack.get_first_child()
    while child is not None:
        page = stack.get_page(child)
        if page is not None:
            names.append(page.get_name())
        child = child.get_next_sibling()
    return names


def snapshot(app, workspace):
    """What the shared containers hold right now."""
    return {
        'pages': stack_names(workspace),
        'sidebar': children(app.get_widget('sidebar-plugin-section')),
        'headerbar_left': children(app.get_widget('headerbar-left-box')),
        'headerbar_right': children(app.get_widget('headerbar-right-box')),
        'dropdowns': len(app.get_widget('plugin-dropdowns') or []),
    }


def find_plugin(system, name):
    for info in system.plugins:
        if info.get_name() == name:
            return info
    return None


def check_one(app, system, workspace, name, page_name):
    info = find_plugin(system, name)
    if info is None:
        print(f'RESULT {name} skipped: not installed')
        return None

    before = snapshot(app, workspace)
    system.unload_plugin(info)
    unloaded = snapshot(app, workspace)
    system.load_plugin(info)
    reloaded = snapshot(app, workspace)

    # A second cycle, to catch anything that only breaks the second time.
    system.unload_plugin(info)
    system.load_plugin(info)
    twice = snapshot(app, workspace)

    print(f'RESULT {name} before      {before}')
    print(f'RESULT {name} after-unload {unloaded}')
    print(f'RESULT {name} after-reload {reloaded}')
    print(f'RESULT {name} after-twice  {twice}')

    ok = reloaded == before and twice == before
    if ok and any(before[key] != unloaded[key]
                  for key in ('pages', 'sidebar', 'headerbar_left',
                              'headerbar_right', 'dropdowns')):
        released = True
    else:
        # A plugin contributing nothing to these containers is fine; it just
        # has nothing for this check to prove.
        released = before == unloaded
        if released:
            print(f'RESULT {name} note: contributes nothing to shared containers')

    if page_name is not None:
        ok = ok and page_name in before['pages'] and page_name not in unloaded['pages']

    print(f'RESULT {name} verdict {"PASS" if ok and released is not None else "FAIL"}')
    return ok


def run_checks(app, names):
    system = app.get_service('plugin-system')
    workspace = app.get_widget('workspace')
    results = []
    for name in names:
        results.append(check_one(app, system, workspace, name,
                                 DEFAULT_PLUGINS.get(name)))
    checked = [r for r in results if r is not None]
    print(f'RESULT overall {"PASS" if checked and all(checked) else "FAIL"} '
          f'({len(checked)} plugin(s) checked)')
    app.quit()
    return False


def main():
    names = sys.argv[1:] or list(DEFAULT_PLUGINS)
    # The app parses its own arguments.
    sys.argv = ['miaz']

    from MiAZ.env import ENV
    from MiAZ.miaz import MiAZ
    MiAZ(ENV)  # sets up the environment and logging the way the app does

    from gi.repository import GLib
    from MiAZ.frontend.desktop.app import MiAZApp

    app = MiAZApp(application_id=ENV['APP']['ID'])
    app.set_env(ENV)
    # Wait for the workspace to settle before touching the containers.
    app.connect('application-started',
                lambda *_a: GLib.timeout_add(2500, run_checks, app, names))
    app.run()


if __name__ == '__main__':
    main()
