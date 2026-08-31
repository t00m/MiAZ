#!/usr/bin/python3

"""
Tests for the translation catalogue.

po/POTFILES is a hand-written list, and nothing checked it. It kept naming
MiAZ/backend/history.py and the seven files of MiAZAIChat months after both were
deleted, and xgettext stops at the first file it cannot open: `ninja miaz-pot`
printed one error and wrote nothing, so the catalogue silently stopped moving.
Three files that do call gettext had never been listed either.
"""

import ast
import os

POTFILES = os.path.join('po', 'POTFILES')
LINGUAS = os.path.join('po', 'LINGUAS')

# Where translatable Python lives. Everything else (tests, scripts, packaging)
# is not shipped to a user and has no interface to translate.
SOURCE_DIRS = [
    os.path.join('MiAZ'),
    os.path.join('data', 'resources', 'plugins'),
]

# The gettext aliases MiAZ uses. N_ marks a string for extraction without
# translating it there and then.
GETTEXT_NAMES = {'_', 'N_'}


def listed_files():
    with open(POTFILES, encoding='utf-8') as potfiles:
        return [line.strip() for line in potfiles if line.strip()]


def listed_languages():
    with open(LINGUAS, encoding='utf-8') as linguas:
        return [line.strip() for line in linguas
                if line.strip() and not line.startswith('#')]


def catalogue_files():
    return sorted(name[:-3] for name in os.listdir('po') if name.endswith('.po'))


def python_files(root):
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for name in names:
            if name.endswith('.py'):
                yield os.path.join(base, name)


def calls_gettext(path):
    with open(path, encoding='utf-8') as source:
        tree = ast.parse(source.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in GETTEXT_NAMES:
                return True
    return False


def test_every_listed_file_exists():
    """A path that no longer exists breaks extraction for every file after it,
    which is a failure nobody sees unless they read the ninja output.
    """
    missing = [path for path in listed_files() if not os.path.exists(path)]
    assert missing == [], (
        f"po/POTFILES names files that are gone: {missing}. "
        f"Remove them, or extraction writes nothing at all.")


def test_every_file_calling_gettext_is_listed():
    """A file left out is a screen the user reads in English whatever their
    language, and nothing says so.
    """
    listed = set(listed_files())
    unlisted = []
    for root in SOURCE_DIRS:
        for path in python_files(root):
            key = path.replace(os.sep, '/')
            if key not in listed and calls_gettext(path):
                unlisted.append(key)
    assert sorted(unlisted) == [], (
        f"These files call gettext but are not in po/POTFILES: "
        f"{sorted(unlisted)}. Their strings are never extracted.")


def test_no_duplicate_entries():
    """A file listed twice makes xgettext read it twice and doubles its
    references in the pot, which is noise in every po file after the merge.
    """
    listed = listed_files()
    seen = set()
    twice = sorted({path for path in listed if path in seen or seen.add(path)})
    assert twice == [], f"po/POTFILES lists these more than once: {twice}"


def test_linguas_and_catalogues_agree():
    """meson builds one mo per language in LINGUAS. A language listed with no
    po file fails the build; a po file left behind after a language is dropped
    is merged on every update and installed by nobody.
    """
    assert listed_languages() == catalogue_files(), (
        f"po/LINGUAS says {listed_languages()} and po/ holds "
        f"{catalogue_files()}.")
