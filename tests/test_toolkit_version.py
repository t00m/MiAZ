#!/usr/bin/python3

"""
The declared GTK and Adw minimums against the APIs the source actually calls.

miaz.py refuses to start when the toolkit is too old, and the two numbers it
refuses on were written by hand and never checked. They said GTK 4.6 and Adw
1.6 while the code called Gtk.FileDialog (4.10) and Adw.ShortcutsDialog (1.8).
The gap ran the other way too: CI installs Ubuntu's libadwaita 1.5, which the
gate waved through as supported, so every UI test died at setup with
SystemExit and the run read as a broken machine rather than a wrong floor.

The version each API was introduced in is written in the GIR files, so nothing
here is a hand-maintained table. GIR ships in the -devel packages; without them
there is nothing to check against and the tests skip.
"""

import ast
import os
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, 'MiAZ', 'miaz.py')

SOURCE_DIRS = [os.path.join(ROOT, 'MiAZ'),
               os.path.join(ROOT, 'data', 'resources', 'plugins')]

GIR = {
    'Gtk': '/usr/share/gir-1.0/Gtk-4.0.gir',
    'Adw': '/usr/share/gir-1.0/Adw-1.gir',
}

# The GIR elements that carry a "version" attribute worth reading.
VERSIONED = ('class', 'enumeration', 'record', 'interface', 'bitfield')

# APIs used above the floor on purpose, behind a version check with a fallback.
# Each entry names the guard constant and its reason; the tests below verify it.
VERSION_GUARDED = {
    'Adw.ShortcutsDialog': (
        'ADW_SHORTCUTS_DIALOG',
        'GNOME provides this widget from libadwaita 1.8. Debian 13, the '
        'current stable, ships 1.7.6, so show_app_help falls back to '
        '_build_shortcuts_fallback there.'),
    'Adw.ShortcutsSection': (
        'ADW_SHORTCUTS_DIALOG', 'part of Adw.ShortcutsDialog, same guard'),
    'Adw.ShortcutsItem': (
        'ADW_SHORTCUTS_DIALOG', 'part of Adw.ShortcutsDialog, same guard'),
}


def as_tuple(version):
    return tuple(int(part) for part in version.split('.'))


def declared_minimum(name):
    """Read GTK_MINIMUM or ADW_MINIMUM out of miaz.py without importing it.

    Importing the entry point runs the environment setup and can call
    sys.exit, which is the very thing under test here.
    """
    tree = ast.parse(open(ENTRY, encoding='utf-8').read(), ENTRY)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not assigned at the top level of miaz.py")


def attributes_used(module_name):
    """Every X in `module_name.X`, mapped to the files that call it.

    Read from the AST, not with grep: 'no Adw.Sidebar' in a comment is not a
    use of Adw.Sidebar, and reading the text says it is.
    """
    used = {}
    for root in SOURCE_DIRS:
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for name in names:
                if not name.endswith('.py'):
                    continue
                path = os.path.join(base, name)
                try:
                    tree = ast.parse(open(path, encoding='utf-8').read(), path)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Attribute)
                            and isinstance(node.value, ast.Name)
                            and node.value.id == module_name):
                        used.setdefault(node.attr, set()).add(path)
    return used


def newest_api_used(module_name):
    """The highest 'introduced in' version among the APIs the source calls."""
    girfile = GIR[module_name]
    if not os.path.exists(girfile):
        pytest.skip(f"{girfile} not installed (needs the -devel package)")
    used = attributes_used(module_name)
    root = ET.parse(girfile).getroot()
    newest = (0, 0)
    culprit = None
    for node in root.iter():
        if node.tag.split('}')[-1] not in VERSIONED:
            continue
        name = node.get('name')
        version = node.get('version')
        if name in used and version:
            if f'{module_name}.{name}' in VERSION_GUARDED:
                continue
            if as_tuple(version) > newest:
                newest, culprit = as_tuple(version), name
    return newest, culprit


@pytest.mark.parametrize('module_name, constant', [
    ('Gtk', 'GTK_MINIMUM'),
    ('Adw', 'ADW_MINIMUM'),
])
def test_the_declared_minimum_covers_what_the_code_calls(module_name, constant):
    needed, culprit = newest_api_used(module_name)
    declared = declared_minimum(constant)
    assert declared >= needed, (
        f"{constant} is {declared} but {module_name}.{culprit} needs {needed}. "
        f"MiAZ would start on a toolkit too old for it and fail at the call.")


def test_the_version_check_compares_tuples():
    """'MAJOR >= 4 and MINOR >= 6' is not a version comparison. It calls 5.0
    too old and, the way it was written for Adw, called 1.5 new enough.
    """
    source = open(ENTRY, encoding='utf-8').read()
    for bad in ('MAJOR_VERSION >= 4 and', 'MAJOR_VERSION >= 1 and'):
        assert bad not in source, (
            f"miaz.py compares the version parts separately ({bad!r}). "
            f"Compare (MAJOR, MINOR) against the minimum tuple instead.")


def test_a_guarded_api_really_is_guarded_where_it_is_called():
    """The exemption is for a call behind a version check. If the file calling
    it does not mention the constant the check compares against, there is no
    check and the entry is hiding a crash on an older toolkit.
    """
    unguarded = []
    for qualified, (constant, _reason) in VERSION_GUARDED.items():
        module_name, attribute = qualified.split('.')
        callers = attributes_used(module_name).get(attribute, set())
        for path in callers:
            if constant not in open(path, encoding='utf-8').read():
                unguarded.append(f"{qualified} in {os.path.relpath(path, ROOT)}")
    assert unguarded == [], (
        f"Called without the guard the allowlist claims: {unguarded}")


def test_every_guarded_entry_still_needs_to_be_there():
    """An exemption that no longer applies hides the next real one."""
    stale = []
    for qualified, (constant, reason) in VERSION_GUARDED.items():
        module_name, attribute = qualified.split('.')
        if not attributes_used(module_name).get(attribute):
            stale.append(f"{qualified} (nothing calls it any more)")
        elif not reason.strip():
            stale.append(f"{qualified} (no reason given)")
        elif not constant.strip():
            stale.append(f"{qualified} (no guard named)")
    assert stale == [], f"Remove these from VERSION_GUARDED: {stale}"
