#!/usr/bin/python3

"""
Pango markup must never be built from repository text unescaped.

A document sent by "Waldorf & Frommer" made the workspace show an empty Sent by
column. set_markup does not merely warn on bad markup, it refuses to set the
text at all, so the value the user filed disappears from the view and only a
Gtk-WARNING on the console says why. Every column did it: the description of a
country, a group, a purpose, a person, a title, a filename.

An ampersand is ordinary in a company name, so this is not an edge case.

The rule: a value that comes from a repository is either set with set_text,
which does not parse anything, or escaped with GLib.markup_escape_text before
it goes near a markup string.
"""

import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where labels are built from repository values.
WIDGETS = os.path.join(ROOT, 'MiAZ', 'frontend', 'desktop')

MARKUP_SETTERS = {'set_markup', 'set_tooltip_markup', 'set_label_markup'}
ESCAPE = 'markup_escape_text'

# Markup the checker cannot prove safe, allowed because a person checked it.
# Keyed by file and function, since line numbers move. Each entry needs a reason.
ALLOWED = {
    ('services/dialogs.py', '__init__'):
        'the body is markup by contract: callers pass their own tags, so '
        'escaping what they interpolate is their job (workflow.py does)',
    ('services/factory.py', 'create_button_content'):
        'title is a UI label the caller writes, not repository text',
    ('services/factory.py', 'create_button'):
        'title and tooltip are UI labels the caller writes',
    ('services/factory.py', 'create_button_toggle'):
        'title and tooltip are UI labels the caller writes',
    ('services/factory.py', 'create_label'):
        'text is a UI label the caller writes, and some callers pass markup',
    ('widgets/assistant.py', '_on_name_changed'):
        'the key comes from util.valid_key, which strips &, < and >',
    ('widgets/configview.py', '__init__'):
        'a translated literal plus the model title, no repository value',
    ('widgets/mainwindow.py', '_on_workspace_menu_update'):
        'document counts',
    ('widgets/chip.py', '__init__'):
        'markup is markup by contract: the caller passes its own tags, so '
        'escaping what it interpolates is its job (workspace.py does)',
    ('widgets/dateentry.py', 'validate'):
        'translated literals and strftime output, which has no & in any locale',
    ('widgets/filenamesview.py', 'update'):
        'every field is passed through markup_escape_text in the loop that '
        'builds the parts; the scan cannot see through the join',
}


def allow_key(path, function_name):
    relative = os.path.relpath(path, os.path.join(ROOT, 'MiAZ', 'frontend', 'desktop'))
    return (relative.replace(os.sep, '/'), function_name)


def python_files(root):
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for name in sorted(names):
            if name.endswith('.py'):
                yield os.path.join(base, name)


def is_escaped_call(node):
    """True for GLib.markup_escape_text(...) and markup_escape_text(...)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == ESCAPE
    return isinstance(func, ast.Name) and func.id == ESCAPE


def interpolations_are_escaped(node, assigned):
    """Every {...} in an f-string must be escaped.

    The value may have been escaped one line earlier and put in a name, which
    is how workspace.py builds its filter tags, so names are followed too.
    """
    if not isinstance(node, ast.JoinedStr):
        return True
    for part in node.values:
        if not isinstance(part, ast.FormattedValue):
            continue
        value = resolve(part.value, assigned)
        if is_escaped_call(value):
            continue
        if isinstance(value, ast.Constant):
            continue
        if isinstance(value, ast.JoinedStr) and interpolations_are_escaped(value, assigned):
            continue
        return False
    return True


def local_assignments(function):
    """The last value assigned to each plain name inside this function."""
    assigned = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = node.value
    return assigned


def resolve(node, assigned):
    """Follow one level of `name = <expr>` so `set_markup(tooltip)` is judged
    on the f-string that built the tooltip, which is how these read."""
    seen = 0
    while isinstance(node, ast.Name) and node.id in assigned and seen < 4:
        node = assigned[node.id]
        seen += 1
    return node


def argument_is_safe(node, assigned):
    """A literal, a translated literal, or an f-string of escaped values."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return interpolations_are_escaped(node, assigned)
    if is_escaped_call(node):
        return True
    # _('...') and friends: a translated literal carries no repository value.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in {'_', 'N_'}:
        return all(argument_is_safe(arg, assigned) for arg in node.args)
    # '<tt>{path}</tt>'.format(path=escaped): safe when the template is a
    # literal and every value in it is escaped. Translated strings do this.
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'format'):
        if not argument_is_safe(node.func.value, assigned):
            return False
        supplied = list(node.args) + [kw.value for kw in node.keywords]
        return all(is_escaped_call(resolve(value, assigned))
                   or isinstance(resolve(value, assigned), ast.Constant)
                   for value in supplied)
    # Concatenation and joins are safe only if every part is.
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return (argument_is_safe(node.left, assigned)
                and argument_is_safe(node.right, assigned))
    return False


def offenders():
    found = []
    for path in python_files(WIDGETS):
        tree = ast.parse(open(path, encoding='utf-8').read(), path)
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            assigned = local_assignments(function)
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute) or func.attr not in MARKUP_SETTERS:
                    continue
                if not node.args:
                    continue
                if argument_is_safe(resolve(node.args[0], assigned), assigned):
                    continue
                if allow_key(path, function.name) in ALLOWED:
                    continue
                found.append(f"{os.path.relpath(path, ROOT)}:{node.lineno} "
                             f"in {function.name}()")
    return sorted(found)


def allowed_entries_in_use():
    """Which allowlist entries the scan would flag if they were not allowed."""
    used = set()
    for path in python_files(WIDGETS):
        tree = ast.parse(open(path, encoding='utf-8').read(), path)
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            assigned = local_assignments(function)
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute) or func.attr not in MARKUP_SETTERS:
                    continue
                if not node.args:
                    continue
                if argument_is_safe(resolve(node.args[0], assigned), assigned):
                    continue
                used.add(allow_key(path, function.name))
    return used


def test_markup_is_never_built_from_unescaped_values():
    """set_markup with an unescaped value does not warn and carry on: it drops
    the text, so the column goes blank and the document looks empty.
    """
    assert offenders() == [], (
        "These build Pango markup from a value that is not escaped:\n  "
        + "\n  ".join(offenders())
        + "\nUse set_text when there is no markup, or wrap the value in "
          "GLib.markup_escape_text.")


def test_every_allowlist_entry_still_needs_to_be_there():
    """An exemption that no longer applies hides the next real one."""
    in_use = allowed_entries_in_use()
    stale = []
    for key, reason in ALLOWED.items():
        if key not in in_use:
            stale.append(f"{key[0]}::{key[1]}() (nothing there builds markup "
                         f"the checker questions any more)")
        elif not reason.strip():
            stale.append(f"{key[0]}::{key[1]}() (no reason given)")
    assert stale == [], f"Remove these from ALLOWED: {stale}"
