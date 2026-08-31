#!/usr/bin/python3

"""
Every command line tool the code shells out to must be a package dependency.

MiAZOCR needs ocrmypdf and says so in its own REQUIRED_TOOLS, but neither
debian/control nor miaz.spec declared it. Installing the .deb on Ubuntu 26.04
therefore produced an application whose OCR plugin could not work, and the only
sign was a dialog telling the user to install something the package should have
brought in.

The tool lists already exist in the code. This checks the packaging against
them, so adding a tool to a plugin without packaging it fails here rather than
on a user's machine.

The same applies to the stdlib modules the code runs as "python3 -m <module>":
the distributions split some of them out, so a plain python3 dependency does not
bring them in.
"""

import ast
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROL = os.path.join(ROOT, 'debian', 'control')
SPEC = os.path.join(ROOT, 'miaz.spec')

# Every module that shells out keeps a REQUIRED_TOOLS list so it can tell the
# user what is missing. These are those lists.
TOOL_DECLARATIONS = (
    os.path.join(ROOT, 'MiAZ', 'backend', 'extract.py'),
    os.path.join(ROOT, 'data', 'resources', 'plugins', 'MiAZOCR', 'ocr.py'),
    os.path.join(ROOT, 'data', 'resources', 'plugins', 'MiAZAutoScan', 'autoscan.py'),
)

# The binary a user types is not always the package that provides it.
PROVIDED_BY = {
    'pdftotext': {'deb': 'poppler-utils', 'rpm': 'poppler-utils'},
    'pdftoppm': {'deb': 'poppler-utils', 'rpm': 'poppler-utils'},
    'tesseract': {'deb': 'tesseract-ocr', 'rpm': 'tesseract'},
    'ocrmypdf': {'deb': 'ocrmypdf', 'rpm': 'ocrmypdf'},
    'scanimage': {'deb': 'sane-utils', 'rpm': 'sane-backends'},
}

# Tools deliberately left to the user, each with its reason: the feature is
# optional enough that packaging its dependency costs more than it gives.
NOT_PACKAGED = {
    'scanimage': (
        'MiAZAutoScan drives a scanner. sane-utils pulls a scanner stack onto '
        'machines that have no scanner, and the plugin reports the missing '
        'tool with an install command when it is enabled.'),
}


# Modules the code runs as "python3 -m <module>". These are not binaries, so
# they never appear in a REQUIRED_TOOLS list, and the distributions do not ship
# them with python3 itself. MiAZ.backend.venv builds the external-libraries
# virtualenv this way: Debian ships the module in python3-venv, and Fedora's
# ensurepip installs from the system pip instead of a bundled wheel, so it needs
# python3-pip on the host. Without them venv creation fails with an error the
# user cannot fix from inside the app.
MODULE_RUNNERS = {
    ('MiAZ/backend/venv.py', 'venv'): {'deb': 'python3-venv', 'rpm': 'python3-pip'},
}


def runs_module(relpath, module):
    """True when the source builds a "python -m <module>" command line."""
    path = os.path.join(ROOT, relpath)
    tree = ast.parse(open(path, encoding='utf-8').read(), path)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        # Keep the positions: the interpreter and the target are calls, not
        # constants, so only the flags in between are readable.
        parts = [elt.value if isinstance(elt, ast.Constant) else None
                 for elt in node.elts]
        for first, second in zip(parts, parts[1:]):
            if first == '-m' and second == module:
                return True
    return False


def declared_tools():
    """Every binary named in a REQUIRED_TOOLS list, read from the source."""
    tools = {}
    for path in TOOL_DECLARATIONS:
        tree = ast.parse(open(path, encoding='utf-8').read(), path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if not target.id.lstrip('_').startswith('REQUIRED_TOOLS'):
                    continue
                for value in ast.literal_eval(node.value):
                    tools[value] = os.path.relpath(path, ROOT)
    return tools


def deb_dependencies():
    text = open(CONTROL, encoding='utf-8').read()
    block = re.search(r'^Depends:(.*?)(?=^\w+:)', text, re.MULTILINE | re.DOTALL)
    assert block, 'no Depends field in debian/control'
    return {re.split(r'[ (]', part.strip())[0]
            for part in block.group(1).split(',') if part.strip()}


def rpm_dependencies():
    text = open(SPEC, encoding='utf-8').read()
    return {re.split(r'[ <>=]', line.split(':', 1)[1].strip())[0]
            for line in text.splitlines() if line.startswith('Requires:')}


def test_the_declarations_are_found():
    """A rename that silently emptied the list would make every other test in
    this file pass by checking nothing."""
    tools = declared_tools()
    assert len(tools) >= 5, tools
    assert 'ocrmypdf' in tools
    assert 'tesseract' in tools


@pytest.mark.parametrize('kind, reader', [('deb', deb_dependencies),
                                          ('rpm', rpm_dependencies)])
def test_every_tool_is_packaged_or_deliberately_not(kind, reader):
    declared = reader()
    missing = []
    for tool, source in sorted(declared_tools().items()):
        if tool in NOT_PACKAGED:
            continue
        package = PROVIDED_BY.get(tool, {}).get(kind)
        assert package, f'{tool} has no {kind} package mapped in PROVIDED_BY'
        if package not in declared:
            missing.append(f'{tool} (needed by {source}, provided by {package})')
    assert missing == [], (
        f'These tools are shelled out to but not declared in the {kind} '
        f'package: {missing}. Add the package, or add the tool to '
        f'NOT_PACKAGED with the reason it is left to the user.')


def test_every_not_packaged_entry_is_still_real():
    """An exemption for a tool nothing uses any more hides the next one."""
    declared = declared_tools()
    stale = [tool for tool in NOT_PACKAGED if tool not in declared]
    assert stale == [], f'Remove these from NOT_PACKAGED: {stale}'


def test_every_not_packaged_entry_gives_a_reason():
    empty = [tool for tool, reason in NOT_PACKAGED.items() if not reason.strip()]
    assert empty == [], f'These need a reason: {empty}'


@pytest.mark.parametrize('kind, reader', [('deb', deb_dependencies),
                                          ('rpm', rpm_dependencies)])
def test_every_module_run_is_packaged(kind, reader):
    declared = reader()
    missing = []
    for (relpath, module), packages in sorted(MODULE_RUNNERS.items()):
        package = packages[kind]
        if package not in declared:
            missing.append(f'python3 -m {module} (run by {relpath}, '
                           f'provided by {package})')
    assert missing == [], (
        f'These modules are run but their {kind} package is not declared: '
        f'{missing}. A Recommends is not enough: apt skips it with '
        f'--no-install-recommends and the failure needs root to fix.')


def test_every_module_runner_is_still_real():
    """A dependency kept for a call that no longer exists is dead weight."""
    stale = [f'{relpath}: python -m {module}'
             for relpath, module in MODULE_RUNNERS
             if not runs_module(relpath, module)]
    assert stale == [], f'Remove these from MODULE_RUNNERS: {stale}'
