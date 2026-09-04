#!/usr/bin/python3

"""Tests for the menu entries a plugin definition declares.

A plugin's menu entries used to be built in its startup(): each plugin named
its own action, wrote its own label and passed its own shortcuts, and five of
them passed nothing at all and got the plugin description as a menu label.
The definition declares them now, so these check the declaration is complete
and that its two halves say the same thing.

The pair is written twice on purpose, the same way Category and Subcategory
are: the .plugin file is what the plugin manager reads before the module is
imported, and plugin_info is what the running plugin reads. Nothing keeps
them in step but this.
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

# Written with the id in the key name: repeated keys are not an INI file.
DECLARED = re.compile(r'^MenuEntry-([\w-]+)$')


def bundled_plugin_files():
    return sorted(glob.glob(os.path.join(PLUGIN_DIR, '*', '*.plugin')))


def declared_in_file(plugin_file):
    """[(id, label, shortcuts)] as the .plugin file writes them."""
    parser = configparser.ConfigParser()
    # Labels are read back as they were written, and a menu label may hold
    # capitals that the default lower-casing would eat.
    parser.optionxform = str
    parser.read(plugin_file)
    entries = []
    for key, value in parser['Plugin'].items():
        match = DECLARED.match(key)
        if match is None:
            continue
        label, _, keys = value.partition('|')
        shortcuts = [key for key in keys.split(',') if key]
        entries.append((match.group(1), label, shortcuts))
    return entries


def declared_in_module(plugin_file):
    """[(id, label, shortcuts)] as the module writes them.

    Read out of the source rather than imported: importing a plugin module
    pulls in its own package and, for some of them, a running application.
    """
    directory = os.path.dirname(plugin_file)
    for module in sorted(glob.glob(os.path.join(directory, '*.py'))):
        source = open(module, encoding='utf-8').read()
        block = re.search(r"'MenuEntries'\s*:\s*\[(.*?)\n\s*\]", source, re.S)
        if block is None:
            continue
        entries = []
        for row in re.finditer(
                r"\(\s*'([\w-]+)'\s*,\s*_\('((?:[^'\\]|\\.)*)'\)\s*(?:,\s*\[([^\]]*)\])?\s*\)",
                block.group(1)):
            shortcuts = re.findall(r"'([^']+)'", row.group(3) or '')
            entries.append((row.group(1), row.group(2).replace("\\'", "'"),
                            shortcuts))
        return entries
    return []


def plugins_with_entries():
    return [f for f in bundled_plugin_files() if declared_in_file(f)]


def test_most_bundled_plugins_declare_entries():
    # A helper that quietly returned nothing would make every test below pass.
    assert len(plugins_with_entries()) >= 17


def test_the_file_and_the_module_declare_the_same_entries():
    """Same ids, same labels, same shortcuts, in the same order."""
    for plugin_file in plugins_with_entries():
        assert declared_in_module(plugin_file) == declared_in_file(plugin_file), \
            plugin_file


def test_entry_ids_are_unique_within_a_plugin():
    """The id is the action name, and two actions cannot share one."""
    for plugin_file in plugins_with_entries():
        ids = [entry_id for entry_id, _label, _keys in declared_in_file(plugin_file)]
        assert len(ids) == len(set(ids)), plugin_file


def wired_in_module(plugin_file):
    """The ids the module passes to install_menu_entries, from its source."""
    directory = os.path.dirname(plugin_file)
    wired = set()
    for module in glob.glob(os.path.join(directory, '*.py')):
        source = open(module, encoding='utf-8').read()
        for call in re.finditer(r'install_menu_entries\(\s*\{(.*?)\}', source, re.S):
            wired.update(re.findall(r"'([\w-]+)'\s*:", call.group(1)))
    return wired


def test_every_declared_entry_is_wired_to_something():
    """A declared id with no callback is an entry that does nothing.

    The plugin system logs it and leaves the entry out, so the only symptom
    at runtime is a menu one item short.
    """
    for plugin_file in plugins_with_entries():
        declared = {entry_id for entry_id, _label, _keys in declared_in_file(plugin_file)}
        assert declared <= wired_in_module(plugin_file), plugin_file


def test_nothing_is_wired_that_was_not_declared():
    """The other half: a callback for an id the definition never names."""
    for plugin_file in plugins_with_entries():
        declared = {entry_id for entry_id, _label, _keys in declared_in_file(plugin_file)}
        assert wired_in_module(plugin_file) <= declared, plugin_file


def test_every_label_reaches_the_translation_catalogue():
    """A label the extraction missed shows up in English in the menu.

    Regenerate with `ninja -C _build miaz-update-po`.
    """
    catalogue = open(CATALOGUE, encoding='utf-8').read()
    missing = []
    for plugin_file in plugins_with_entries():
        for _entry_id, label, _keys in declared_in_file(plugin_file):
            if f'msgid "{label}"\n' not in catalogue:
                missing.append(f'{os.path.basename(plugin_file)}: {label}')
    assert missing == [], f"not in {CATALOGUE}: {', '.join(missing)}"


def test_normalise_fills_in_the_missing_shortcuts():
    entries = ps.normalise_menu_entries([('all', 'See all notes'),
                                         ('doc', 'Create a note', ['<Ctrl>N'])])
    assert entries == [('all', 'See all notes', []),
                       ('doc', 'Create a note', ['<Ctrl>N'])]


def test_normalise_drops_an_entry_that_is_not_one():
    assert ps.normalise_menu_entries([('lonely',), (), None or ()]) == []


def test_normalise_accepts_nothing_declared():
    assert ps.normalise_menu_entries(None) == []
    assert ps.normalise_menu_entries([]) == []
