#!/usr/bin/python3

"""
Tests for the plugin category vocabulary.

Nothing checked these values before, and they drifted: three plugins declared
Subcategory 'User Interface', which `plugin_categories` never defined. Their
menu label stayed translated only because settings.py happened to contain the
same literal. That is the accident these tests are here to prevent.

The module imports gi/Peas, so the test sets the versions first, like the app
does. `plugin_categories` and `validate_category` are module level and side
effect free, so importing needs no running app and no display.
"""

import os
import re
import glob
import configparser

import gi
gi.require_version('Peas', '2')
gi.require_version('Gtk', '4.0')

from MiAZ.frontend.desktop.services import pluginsystem as ps

PLUGIN_DIR = os.path.join('data', 'resources', 'plugins')
CATALOGUE = os.path.join('po', 'es_ES.po')


def bundled_plugin_files():
    return sorted(glob.glob(os.path.join(PLUGIN_DIR, '*', '*.plugin')))


def declared_pair(plugin_file):
    parser = configparser.ConfigParser()
    parser.read(plugin_file)
    section = parser['Plugin']
    return section['Category'], section['Subcategory']


def test_there_are_bundled_plugins_to_check():
    # A glob that matches nothing would make every test below pass silently.
    assert len(bundled_plugin_files()) >= 17


def test_every_bundled_plugin_declares_a_known_pair():
    for plugin_file in bundled_plugin_files():
        category, subcategory = declared_pair(plugin_file)
        problem = ps.validate_category(category, subcategory)
        assert problem is None, f"{plugin_file}: {problem}"


def test_plugin_file_and_module_declare_the_same_pair():
    """The pair is written twice, in the .plugin file and in plugin_info."""
    for plugin_file in bundled_plugin_files():
        category, subcategory = declared_pair(plugin_file)
        for module in glob.glob(os.path.join(os.path.dirname(plugin_file), '*.py')):
            source = open(module, encoding='utf-8').read()
            found_cat = re.search(r"'Category'\s*:\s*'([^']*)'", source)
            found_sub = re.search(r"'Subcategory'\s*:\s*'([^']*)'", source)
            if found_cat is None:
                continue
            assert found_cat.group(1) == category, module
            assert found_sub.group(1) == subcategory, module


def test_names_are_one_word():
    """The subcategory is a menu label, sitting next to 'Toggle fullscreen'."""
    for category, subcategories in ps.plugin_categories.items():
        assert ' ' not in category, category
        for subcategory in subcategories:
            assert ' ' not in subcategory, subcategory


def test_validate_category_accepts_a_known_pair():
    assert ps.validate_category('Documents', 'Import') is None


def test_validate_category_rejects_an_unknown_category():
    problem = ps.validate_category('Data Management', 'Import')
    assert problem is not None
    assert 'Data Management' in problem


def test_validate_category_rejects_a_subcategory_from_another_category():
    problem = ps.validate_category('Documents', 'Backup')
    assert problem is not None
    assert 'Backup' in problem


def test_every_name_reaches_the_translation_catalogue():
    """The whole reason plugin_categories exists.

    No code reads the dict. Its N_() calls are what puts the names in po/, and
    both display sites translate the value they read at runtime: `_(category)`
    in configview and `_(subcategory)` in app.install_plugin_menu. A name that
    never got extracted shows up untranslated in the menu and in the plugin
    manager filters. Regenerate with `ninja -C _build miaz-update-po`.
    """
    catalogue = open(CATALOGUE, encoding='utf-8').read()
    names = set(ps.plugin_categories)
    for subcategories in ps.plugin_categories.values():
        names.update(subcategories)
    missing = [n for n in sorted(names)
               if f'msgid "{n}"\n' not in catalogue]
    assert not missing, f"not in {CATALOGUE}: {', '.join(missing)}"


def test_the_repository_category_offers_a_history():
    """MiAZHistory files its settings under Repository > History, and a pair
    that is not in the vocabulary is only warned about at runtime."""
    assert ps.validate_category('Repository', 'History') is None


def test_the_module_named_in_the_plugin_file_is_the_file_that_exists():
    """A .plugin naming a module that is not there loads nothing, silently.

    MiAZRelated shipped for a moment with Module=related while the code was in
    relateddocs.py, and the only symptom was a plugin that never appeared.
    """
    missing = []
    for plugin_file in sorted(glob.glob(os.path.join(PLUGIN_DIR, "*", "*.plugin"))):
        directory = os.path.dirname(plugin_file)
        parser = configparser.ConfigParser()
        parser.read(plugin_file)
        module = parser.get('Plugin', 'Module', fallback='')
        if not os.path.exists(os.path.join(directory, f'{module}.py')):
            missing.append(f"{os.path.basename(plugin_file)} names "
                           f"Module={module}, but {module}.py is not there")
    assert missing == [], '\n'.join(missing)


# ---------------------------------------------------------------------------
# Version, the one duplicated field nothing guarded
# ---------------------------------------------------------------------------

def declared_version(plugin_file):
    """The Version the .plugin file declares, or None when it declares none."""
    parser = configparser.ConfigParser()
    parser.read(plugin_file)
    return parser['Plugin'].get('Version')


def module_version(plugin_file):
    """(version, module path) from the plugin_info dict, or (None, None)."""
    for module in sorted(glob.glob(os.path.join(os.path.dirname(plugin_file), '*.py'))):
        source = open(module, encoding='utf-8').read()
        found = re.search(r"'Version'\s*:\s*'([^']*)'", source)
        if found is not None:
            return found.group(1), module
    return None, None


def test_no_bundled_plugin_declares_a_version():
    """A bundled plugin ships with MiAZ, so it has no version of its own.

    The number used to be written twice per plugin, in the .plugin file and in
    plugin_info, and nine of the twenty-one disagreed with themselves. Both
    halves reach the user, so which number you saw depended on where you
    looked. Rather than keep two copies in step through every release, neither
    is written: MiAZPluginSystem falls back to the application version for a
    plugin that declares none.

    An out-of-tree plugin is released on its own schedule and keeps its
    Version. Only the bundled ones are covered here.
    """
    declared = []
    for plugin_file in bundled_plugin_files():
        if declared_version(plugin_file) is not None:
            declared.append(plugin_file)
        found, module = module_version(plugin_file)
        if found is not None:
            declared.append(module)
    assert not declared, (
        'these carry a version of their own, so they will drift from '
        'meson.build again:\n' + '\n'.join(declared))
