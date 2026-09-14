#!/usr/bin/python3

"""The .plugin file is generated from the module, so the two cannot drift.

A plugin declares itself twice: in plugin_info, which the running plugin reads,
and in the .plugin file, which libpeas and the command line read before any
module is imported. tests/test_plugin_categories.py and
tests/test_plugin_menu_entries.py check that the two agree on the pairs and the
entries. This checks the whole file, by generating it and comparing.

Regenerate with:

    PYTHONPATH=. python scripts/devel/create_plugin_definitions.py data/resources/plugins
"""

import ast
import glob
import os

import gi
gi.require_version('Peas', '2')

from MiAZ.backend.plugins import plugin_definition_text
from MiAZ.backend.util import SafeDictExtractor

PLUGIN_DIR = os.path.join('data', 'resources', 'plugins')


def bundled_plugin_files():
    return sorted(glob.glob(os.path.join(PLUGIN_DIR, '*', '*.plugin')))


def module_plugin_info(directory):
    """The plugin_info of the one module in `directory` that has one."""
    for module in sorted(glob.glob(os.path.join(directory, '*.py'))):
        extractor = SafeDictExtractor('plugin_info')
        with open(module, encoding='utf-8') as handler:
            extractor.visit(ast.parse(handler.read(), filename=module))
        if extractor.result:
            return extractor.result
    return None


def test_there_are_bundled_plugins_to_check():
    assert len(bundled_plugin_files()) >= 20


def test_every_definition_matches_what_its_module_declares():
    for plugin_file in bundled_plugin_files():
        info = module_plugin_info(os.path.dirname(plugin_file))
        assert info is not None, plugin_file
        with open(plugin_file, encoding='utf-8') as handler:
            assert handler.read() == plugin_definition_text(info), plugin_file


def test_every_plugin_declares_the_loader_the_engine_enables():
    """MiAZPluginCore enables the 'python' loader and nothing else."""
    for plugin_file in bundled_plugin_files():
        info = module_plugin_info(os.path.dirname(plugin_file))
        assert info['Loader'] == 'python', plugin_file


def test_a_menu_entry_becomes_one_key_named_after_its_id():
    text = plugin_definition_text({
        'Module': 'demo',
        'MenuEntries': [('go', 'Go somewhere')],
    })
    assert text == '[Plugin]\nModule=demo\nMenuEntry-go=Go somewhere\n'


def test_shortcuts_follow_the_label_after_a_pipe():
    text = plugin_definition_text({
        'MenuEntries': [('go', 'Go', ['<Control>g', '<Control><Shift>g'])],
    })
    assert text == '[Plugin]\nMenuEntry-go=Go|<Control>g,<Control><Shift>g\n'


def test_an_operation_becomes_a_command_key():
    text = plugin_definition_text({
        'Operations': [{'name': 'ocr', 'help': 'Extract text', 'run': 'run_ocr'}],
    })
    assert text == '[Plugin]\nCommand-ocr=Extract text\n'


def test_an_operation_without_help_still_gets_its_key():
    text = plugin_definition_text({'Operations': [{'name': 'go', 'run': 'run'}]})
    assert text == '[Plugin]\nCommand-go=\n'


def test_keys_keep_the_order_the_module_writes_them_in():
    text = plugin_definition_text({'Module': 'demo', 'Name': 'Demo',
                                   'Category': 'Help'})
    assert text == '[Plugin]\nModule=demo\nName=Demo\nCategory=Help\n'
