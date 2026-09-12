#!/usr/bin/python3

"""
Architectural boundaries, enforced instead of documented.

AGENTS.md states two rules that nothing checked until now, so both had drifted:
the backend imports no GUI toolkit, and the frontend does not touch repository
documents behind the util service's back.

Each rule has an allowlist. An entry is a decision with a reason attached, not a
way to silence the test: adding one should feel like a change worth explaining.
"""

import ast
import os

BACKEND = os.path.join('MiAZ', 'backend')
FRONTEND = os.path.join('MiAZ', 'frontend')
CONSOLE = os.path.join('MiAZ', 'frontend', 'console')
PLUGINS = os.path.join('data', 'resources', 'plugins')

# gi namespaces that mean "this module draws or talks to a display".
# GObject, GLib and Gio are deliberately allowed: the backend exposes its events
# as GObject signals, which is the backend/frontend contract.
GUI_NAMESPACES = {'Gtk', 'Adw', 'Gdk', 'GdkPixbuf', 'Pango', 'WebKit', 'Graphene'}

# Filesystem calls that mutate or enumerate on their own, rather than going
# through the util service (which emits filename-added / -deleted / -renamed so
# the index and the workspace stay in step).
FS_CALLS = {
    ('os', 'rename'), ('os', 'replace'), ('os', 'remove'), ('os', 'unlink'),
    ('os', 'mkdir'), ('os', 'rmdir'),
    ('shutil', 'copy'), ('shutil', 'copy2'), ('shutil', 'copyfile'),
    ('shutil', 'move'), ('shutil', 'rmtree'), ('shutil', 'copytree'),
}

# Frontend modules allowed to call the above, with the reason each is exempt.
# None of them touches a repository document; that is the line.
FS_ALLOWED = {
    'MiAZ/frontend/desktop/services/pluginsystem.py':
        'installs and uninstalls plugin files under ~/.MiAZ/opt/plugins, and '
        'removes a plugin WWW directory. Not repository documents.',
    'MiAZ/frontend/desktop/services/icm.py':
        'exports plugin icons into ~/.MiAZ/opt/icons so the icon theme can '
        'resolve them by name.',
}


# Methods that return something truthy, so GLib.idle_add keeps re-running them.
# GLib repeats an idle source until its callback returns a falsy value, so
# idle_add(srvdlg.show_toast, msg) rebuilds the toast on every iteration of the
# main loop, for ever. Use tasks.run_on_main for anything whose return value is
# not yours to control.
RETURNS_A_VALUE = {
    'show_toast': 'returns the Adw.Toast it created',
    'release': 'SuspendHandle.release returns True the first time',
}


def idle_add_with_a_returning_callback(tree):
    """(callback, lineno) for every idle_add handed a callback that returns."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != 'idle_add':
            continue
        if not node.args:
            continue
        callback = node.args[0]
        if isinstance(callback, ast.Attribute) and callback.attr in RETURNS_A_VALUE:
            found.append((callback.attr, node.lineno))
    return found


def python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in sorted(filenames):
            if name.endswith('.py'):
                yield os.path.join(dirpath, name)


def parse(path):
    with open(path, 'r', encoding='utf-8') as handler:
        return ast.parse(handler.read(), filename=path)


def imports_desktop_frontend(tree):
    """True when this module imports anything from MiAZ.frontend.desktop."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith('MiAZ.frontend.desktop'):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('MiAZ.frontend.desktop'):
                    return True
    return False


def gui_namespaces_imported(tree):
    """The gi.repository namespaces this module imports."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'gi.repository':
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('gi.repository.'):
                    found.add(alias.name.split('.')[-1])
    return found & GUI_NAMESPACES


def direct_fs_calls(tree):
    """(call, lineno) for every os/shutil call that bypasses the util service."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        value = node.func.value
        if isinstance(value, ast.Name) and (value.id, node.func.attr) in FS_CALLS:
            found.append((f"{value.id}.{node.func.attr}", node.lineno))
    return found


# ---------------------------------------------------------------------------
# The detectors themselves, so a passing rule is not a broken detector
# ---------------------------------------------------------------------------

def test_gui_detector_finds_a_gui_import():
    tree = ast.parse('from gi.repository import Gtk')
    assert gui_namespaces_imported(tree) == {'Gtk'}


def test_gui_detector_allows_the_backend_gi_namespaces():
    tree = ast.parse(
        'from gi.repository import GObject\n'
        'from gi.repository import GLib\n'
        'from gi.repository import Gio\n')
    assert gui_namespaces_imported(tree) == set()


def test_desktop_detector_finds_an_import():
    tree = ast.parse('from MiAZ.frontend.desktop.services.factory import X')
    assert imports_desktop_frontend(tree) is True


def test_desktop_detector_allows_the_backend():
    tree = ast.parse('from MiAZ.backend.query import DocumentQuery')
    assert imports_desktop_frontend(tree) is False


def test_fs_detector_finds_a_direct_call():
    tree = ast.parse('import os\nos.unlink(path)\n')
    assert direct_fs_calls(tree) == [('os.unlink', 2)]


def test_fs_detector_ignores_the_util_service():
    tree = ast.parse('util.filename_delete({path})\n')
    assert direct_fs_calls(tree) == []


def test_idle_add_detector_finds_a_returning_callback():
    tree = ast.parse('GLib.idle_add(self.srvdlg.show_toast, msg)')
    assert idle_add_with_a_returning_callback(tree) == [('show_toast', 1)]


def test_idle_add_detector_allows_a_callback_that_removes_its_own_source():
    """_release_suspend returns False itself, which is the other correct way."""
    tree = ast.parse('GLib.idle_add(self._release_suspend)')
    assert idle_add_with_a_returning_callback(tree) == []


def test_idle_add_detector_ignores_run_on_main():
    tree = ast.parse('run_on_main(handle.release)')
    assert idle_add_with_a_returning_callback(tree) == []


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------

def test_backend_imports_no_gui_toolkit():
    """The backend must stay runnable without a display.

    GObject, GLib and Gio are fine and used on purpose. Gtk, Adw and Gdk are
    not: importing one here means the logic cannot be tested or reused headless,
    which is what put the document parse inside a Gtk.Box in the first place.
    """
    offenders = {}
    for path in python_files(BACKEND):
        found = gui_namespaces_imported(parse(path))
        if found:
            offenders[path] = sorted(found)
    assert offenders == {}, (
        f"Backend modules importing a GUI toolkit: {offenders}. "
        f"Move the widget code to MiAZ/frontend/desktop/widgets/.")


def test_console_frontend_runs_without_a_display():
    """The command line must work on a machine with no display.

    One convenient import of a desktop helper would make it need one, and the
    split that makes the command line possible would rot from there. The
    console package may use the backend and nothing else of the frontend.
    """
    offenders = {}
    checked = 0
    for path in python_files(CONSOLE):
        checked += 1
        tree = parse(path)
        problems = sorted(gui_namespaces_imported(tree))
        if imports_desktop_frontend(tree):
            problems.append('MiAZ.frontend.desktop')
        if problems:
            offenders[path] = problems
    # A rule that walks the wrong directory finds nothing and passes for ever.
    assert checked >= 2, f'expected the console package under {CONSOLE}'
    assert offenders == {}, (
        f"Console modules that need a display: {offenders}. "
        f"The command line may import MiAZ.backend only.")


def test_frontend_does_not_touch_the_filesystem_directly():
    """Document operations go through the util service.

    util.filename_rename / _delete / _import emit the signals the index and the
    workspace listen to. A frontend module calling os.unlink on a document
    leaves both holding an entry for a file that is gone.
    """
    offenders = {}
    for path in python_files(FRONTEND):
        key = path.replace(os.sep, '/')
        if key in FS_ALLOWED:
            continue
        found = direct_fs_calls(parse(path))
        if found:
            offenders[key] = found
    assert offenders == {}, (
        f"Frontend modules calling the filesystem directly: {offenders}. "
        f"Use the util service, or add an entry to FS_ALLOWED with a reason.")


def test_every_allowlist_entry_still_needs_to_be_there():
    """An exemption that no longer applies is worse than no exemption: it hides
    the next real violation in that file.
    """
    stale = []
    for key, reason in FS_ALLOWED.items():
        path = key.replace('/', os.sep)
        if not os.path.exists(path):
            stale.append(f"{key} (file is gone)")
        elif not direct_fs_calls(parse(path)):
            stale.append(f"{key} (no longer calls the filesystem)")
        elif not reason.strip():
            stale.append(f"{key} (no reason given)")
    assert stale == [], f"Remove these from FS_ALLOWED: {stale}"


def test_idle_add_is_not_handed_a_callback_that_returns_a_value():
    """GLib repeats an idle source until the callback returns something falsy.

    Handing it a function that returns a value arms the source for ever: the
    scan toast was rebuilt on every iteration of the main loop until the app
    closed. MiAZ.backend.tasks.run_on_main runs a callback once whatever it
    returns, and is what these call sites want.
    """
    offenders = {}
    checked = 0
    for root in (BACKEND, FRONTEND, PLUGINS):
        for path in python_files(root):
            checked += 1
            found = idle_add_with_a_returning_callback(parse(path))
            if found:
                offenders[path.replace(os.sep, '/')] = found
    # A rule that walks the wrong directories finds nothing and passes for ever.
    assert checked >= 50, f'expected to scan the package and the plugins, saw {checked} files'
    assert offenders == {}, (
        f"idle_add handed a callback that returns a value: {offenders}. "
        f"Use MiAZ.backend.tasks.run_on_main instead. "
        f"Why each one repeats: {RETURNS_A_VALUE}.")
