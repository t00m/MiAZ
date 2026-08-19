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
