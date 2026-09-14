#!/usr/bin/python3

"""
Tests for the frontend-neutral half of the plugin system.

LibPeas 2 dropped its GTK dependency, so plugin discovery, loading and
activation no longer need a display. What kept MiAZ's plugin system tied to the
desktop was where the code lived, not what it did:
frontend/desktop/services/pluginsystem.py imported Gtk at module scope and used
it in exactly one method.

These tests pin the neutral half down in MiAZ/backend/plugins.py so the console
frontend can use it, and so it stays neutral: the first test fails the moment
somebody imports Gtk into it again.
"""

import argparse
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What tells GTK where to draw. Removing all three is what a cron job or an SSH
# session without X forwarding looks like.
DISPLAY_VARS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR')


def run_without_display(code):
    """Run `code` in a fresh interpreter that has no display to draw on."""
    env = {
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        'HOME': os.environ.get('HOME', '/tmp'),
        'PYTHONPATH': ROOT,
        'LC_ALL': 'C',
    }
    for name in DISPLAY_VARS:
        env.pop(name, None)
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


def test_the_plugin_core_imports_without_pulling_in_gtk():
    """The whole point. Importing the core must not cost a toolkit.

    Asserted in a subprocess because pytest itself has already imported Gtk by
    the time this runs, so checking sys.modules in-process proves nothing.
    """
    result = run_without_display(
        'import sys\n'
        'import MiAZ.backend.plugins\n'
        "toolkit = sorted(m for m in sys.modules if m.startswith('gi.repository.')\n"
        "                 and m.rsplit('.', 1)[-1] in ('Gtk', 'Adw', 'Gdk'))\n"
        "print('TOOLKIT:' + ','.join(toolkit))\n")
    assert result.returncode == 0, result.stderr[-3000:]
    assert 'TOOLKIT:\n' in result.stdout, (
        f"the plugin core dragged a toolkit in: {result.stdout.strip()}")


def test_the_plugin_core_loads_and_activates_a_plugin_without_a_display(tmp_path):
    """Discovery, load and activation, with nowhere to draw.

    This is the probe that justified the whole change, kept as a test so a
    later import cannot quietly break it.
    """
    plugin_dir = tmp_path / 'plugins' / 'probeplug'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'probeplug.plugin').write_text(
        '[Plugin]\n'
        'Module=probeplug\n'
        'Name=ProbePlug\n'
        'Loader=python\n'
        'Description=Headless probe\n', encoding='utf-8')
    (plugin_dir / 'probeplug.py').write_text(
        'from MiAZ.backend.plugins import MiAZExtension\n'
        '\n'
        "plugin_info = {'Name': 'ProbePlug', 'Description': 'Headless probe'}\n"
        '\n'
        '\n'
        'class ProbePlugin(MiAZExtension):\n'
        "    __gtype_name__ = 'ProbePlugin'\n"
        '\n'
        '    def do_activate(self):\n'
        '        self.activated = True\n', encoding='utf-8')

    result = run_without_display(
        'from MiAZ.backend.plugins import MiAZPluginCore\n'
        f'core = MiAZPluginCore(search_paths=[{str(tmp_path / "plugins")!r}])\n'
        "info = core.get_plugin_info('probeplug')\n"
        'core.load_plugin(info)\n'
        "extension = core.get_extension('probeplug')\n"
        "print('ACTIVATED:' + str(getattr(extension, 'activated', False)))\n")
    assert result.returncode == 0, result.stderr[-3000:]
    assert 'ACTIVATED:True' in result.stdout, result.stdout + result.stderr[-2000:]


def test_an_operation_is_read_out_of_the_plugin_declaration():
    """A plugin declares what it can do as plain data, the way it already
    declares menu entries."""
    from MiAZ.backend.plugins import parse_operations

    operations = parse_operations({
        'Operations': [{
            'name': 'ocr',
            'help': 'Extract text from a document',
            'run': 'run_ocr',
            'params': [{'name': 'document', 'positional': True}],
        }],
    }, owner='ocr')

    assert len(operations) == 1
    assert operations[0].name == 'ocr'
    assert operations[0].owner == 'ocr'
    assert operations[0].run == 'run_ocr'


def test_an_operation_without_a_handler_is_not_an_operation():
    """A declaration with no `run` names nothing to call. Dropping it beats
    failing later with an AttributeError from inside argparse."""
    from MiAZ.backend.plugins import parse_operations

    assert parse_operations({'Operations': [{'name': 'ocr'}]}, owner='ocr') == []


def test_an_operation_declares_its_own_command_line_flags():
    """One declaration, rendered as argparse. The GUI renders the same
    declaration as a menu entry and a settings row."""
    from MiAZ.backend.plugins import parse_operations

    operation = parse_operations({
        'Operations': [{
            'name': 'ocr',
            'run': 'run_ocr',
            'params': [
                {'name': 'document', 'positional': True},
                {'name': 'language', 'default': 'eng'},
                {'name': 'force', 'flag': True},
            ],
        }],
    }, owner='ocr')[0]

    parser = argparse.ArgumentParser(prog='miaz ocr')
    operation.add_arguments(parser)
    args = parser.parse_args(['DOC-1', '--language', 'spa', '--force'])

    assert args.document == 'DOC-1'
    assert args.language == 'spa'
    assert args.force is True


def test_an_operation_flag_defaults_to_off_and_its_value_to_the_declared_default():
    """The defaults come from the declaration, not from argparse's guesses."""
    from MiAZ.backend.plugins import parse_operations

    operation = parse_operations({
        'Operations': [{
            'name': 'ocr',
            'run': 'run_ocr',
            'params': [
                {'name': 'document', 'positional': True},
                {'name': 'language', 'default': 'eng'},
                {'name': 'force', 'flag': True},
            ],
        }],
    }, owner='ocr')[0]

    parser = argparse.ArgumentParser(prog='miaz ocr')
    operation.add_arguments(parser)
    args = parser.parse_args(['DOC-1'])

    assert args.language == 'eng'
    assert args.force is False


def test_a_choice_parameter_refuses_a_value_outside_the_vocabulary():
    """AutoScan's _SOURCES and _RESOLUTIONS are already a controlled
    vocabulary, hand-rendered three times. Declared once, argparse enforces
    it for free."""
    from MiAZ.backend.plugins import parse_operations

    operation = parse_operations({
        'Operations': [{
            'name': 'scan',
            'run': 'run_scan',
            'params': [{'name': 'source',
                        'choices': ['Flatbed', 'ADF'],
                        'default': 'Flatbed'}],
        }],
    }, owner='autoscan')[0]

    parser = argparse.ArgumentParser(prog='miaz scan')
    operation.add_arguments(parser)

    # argparse reports the bad value and exits 2, which is the code the CLI
    # already uses for arguments that do not make sense.
    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(['--source', 'Telepathy'])
    assert exit_info.value.code == 2


def test_an_integer_parameter_arrives_as_an_integer():
    """A resolution is compared and passed to a command, not concatenated."""
    from MiAZ.backend.plugins import parse_operations

    operation = parse_operations({
        'Operations': [{
            'name': 'scan',
            'run': 'run_scan',
            'params': [{'name': 'resolution', 'type': 'int', 'default': 300}],
        }],
    }, owner='autoscan')[0]

    parser = argparse.ArgumentParser(prog='miaz scan')
    operation.add_arguments(parser)

    assert parser.parse_args(['--resolution', '600']).resolution == 600
    assert parser.parse_args([]).resolution == 300


def test_the_desktop_plugin_system_shares_the_core_extension_class():
    """All 21 plugins import MiAZExtension from the desktop module.

    _activate_plugin_instance finds a plugin's class with
    issubclass(cls, MiAZExtension). If the desktop module ever defines its own
    class instead of re-exporting the core's, that check fails for every
    plugin, and it fails silently: the loader just reports "no MiAZExtension
    subclass found".
    """
    from MiAZ.backend.plugins import MiAZExtension as core_extension
    from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension

    assert MiAZExtension is core_extension


def test_the_desktop_plugin_system_is_built_on_the_core():
    """One loader, not two. The desktop adds placement, nothing else."""
    from MiAZ.backend.plugins import MiAZPluginCore
    from MiAZ.frontend.desktop.services.pluginsystem import MiAZPluginSystem

    assert issubclass(MiAZPluginSystem, MiAZPluginCore)


def test_the_desktop_plugin_system_still_exports_what_the_app_imports():
    """The names the desktop app and the plugins reach for, unchanged.

    Moving code is only safe if the old import paths keep working, so this
    lists them rather than trusting that nothing was missed.
    """
    from MiAZ.frontend.desktop.services import pluginsystem

    for name in ('MiAZExtension', 'MiAZAPI', 'MiAZPlugin', 'MiAZPluginSystem',
                 'plugin_version', 'normalise_menu_entries', 'plugin_categories',
                 'validate_category', 'PLUGIN_DEFAULT_ICON'):
        assert hasattr(pluginsystem, name), f"pluginsystem lost {name}"


def test_a_plugin_path_is_defined_in_one_place():
    """The desktop helper and the command line have to agree on where a
    plugin's notes and settings live, or `miaz ocr` writes a note the window
    never shows."""
    from MiAZ.backend.plugins import plugin_config_dir, plugin_data_dir

    assert plugin_data_dir('/repo', 'MiAZOCR') == \
        '/repo/.conf/plugins/MiAZOCR/data'
    assert plugin_config_dir('/repo', 'MiAZOCR') == \
        '/repo/.conf/plugins/MiAZOCR/conf'


def test_the_desktop_plugin_helper_uses_those_same_paths():
    """Read off MiAZPlugin rather than duplicated here, so the two cannot
    drift apart without this failing."""
    from MiAZ.backend.plugins import plugin_data_dir
    from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin

    class OneRepository:
        docs = '/repo'

        def get_service(self, name):
            return self if name == 'repo' else None

    helper = MiAZPlugin.__new__(MiAZPlugin)
    helper.app = OneRepository()
    helper.name = 'MiAZOCR'

    assert helper.get_data_dir() == plugin_data_dir('/repo', 'MiAZOCR')
    assert helper.get_config_dir().endswith('/MiAZOCR/conf')


def test_a_parameter_can_take_more_than_one_value():
    """The menu entry runs on the selection, which is usually several
    documents. The command has to be able to say the same thing."""
    from MiAZ.backend.plugins import parse_operations

    operation = parse_operations({
        'Operations': [{
            'name': 'ocr',
            'run': 'run_ocr',
            'params': [{'name': 'documents', 'positional': True,
                        'multiple': True}],
        }],
    }, owner='ocr')[0]

    parser = argparse.ArgumentParser(prog='miaz ocr')
    operation.add_arguments(parser)

    assert parser.parse_args(['A.pdf', 'B.pdf']).documents == ['A.pdf', 'B.pdf']
    assert parser.parse_args(['A.pdf']).documents == ['A.pdf']


def test_a_multiple_parameter_still_wants_at_least_one_value():
    """`miaz ocr` with no document is a mistake, not a request to OCR the
    whole repository."""
    from MiAZ.backend.plugins import parse_operations

    operation = parse_operations({
        'Operations': [{
            'name': 'ocr',
            'run': 'run_ocr',
            'params': [{'name': 'documents', 'positional': True,
                        'multiple': True}],
        }],
    }, owner='ocr')[0]

    parser = argparse.ArgumentParser(prog='miaz ocr')
    operation.add_arguments(parser)

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_only_the_displayed_values_go_through_gettext(tmp_path, monkeypatch):
    """An author's name and a URL are not messages.

    get_plugin_attributes used to translate every value it read, which is some
    two hundred lookups over the bundled plugins to keep two of them, and would
    rewrite a URL that happened to be a msgid.
    """
    import gettext as gettext_module
    from MiAZ.backend import plugins as core

    plugin_file = tmp_path / 'demo.plugin'
    plugin_file.write_text(
        '[Plugin]\n'
        'Module=demo\n'
        'Name=Demo\n'
        'Description=A demo plugin\n'
        'Authors=Somebody <somebody@example.com>\n'
        'Website=http://example.com\n'
        'Command-demo=Do the demo thing\n',
        encoding='utf-8')

    seen = []

    def spy(text):
        seen.append(text)
        return f'<{text}>'

    monkeypatch.setattr(gettext_module, 'gettext', spy)

    attributes = core.get_plugin_attributes(str(plugin_file))

    assert attributes['Module'] == 'demo'
    assert attributes['Name'] == 'Demo'
    assert attributes['Authors'] == 'Somebody <somebody@example.com>'
    assert attributes['Website'] == 'http://example.com'
    assert attributes['Description'] == '<A demo plugin>'
    assert attributes['Command-demo'] == '<Do the demo thing>'
    assert sorted(seen) == ['A demo plugin', 'Do the demo thing']


def test_a_direct_import_records_no_failure(tmp_path):
    """The fallback used to write a failure entry and pop it on the next line.

    It reads as though a direct import is a failure, and one of the two lines
    is always wrong.
    """
    from MiAZ.backend.plugins import MiAZPluginCore

    plugin_dir = tmp_path / 'demo'
    plugin_dir.mkdir()
    (plugin_dir / 'demo.py').write_text(
        'from MiAZ.backend.plugins import MiAZExtension\n'
        '\n'
        '\n'
        'class Demo(MiAZExtension):\n'
        "    __gtype_name__ = 'DemoDirectImport'\n",
        encoding='utf-8')

    core = MiAZPluginCore(search_paths=[str(tmp_path)])
    module = core.import_module('demo')

    assert module is not None
    assert core.get_load_failures() == {}
    assert core.get_load_error('demo') is None
