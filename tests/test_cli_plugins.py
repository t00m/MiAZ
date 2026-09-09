#!/usr/bin/python3

"""
Tests for plugin-contributed commands on the command line.

A plugin declares a command in its .plugin file, the same way it already
declares a menu entry there:

    MenuEntry-extract=Extract text (OCR)…
    Command-ocr=Extract text from a document with OCR

Discovery has to be cheap, because `miaz search` pays for it on every run and
gets nothing back. Reading the 21 .plugin files takes 1.3 ms; AST-parsing the
21 modules for their plugin_info takes 89 ms. So the .plugin file carries the
command names, and the parameter schema in plugin_info is read only once the
user actually asks for that command, which needs the module imported anyway.
"""

import io
import os

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from MiAZ.backend.plugins import discover_commands
from MiAZ.frontend.console.cli import build_parser, known_commands, main


def make_plugin(root, module='ocr', command_lines=('Command-ocr=Read a document',),
                body=None):
    """Write a plugin directory that looks like the ones MiAZ ships."""
    plugin_dir = root / module
    plugin_dir.mkdir(parents=True, exist_ok=True)
    meta = ['[Plugin]',
            f'Module={module}',
            f'Name=MiAZ{module.upper()}',
            'Loader=python',
            'Description=A plugin',
            'Category=Documents',
            'Subcategory=Annotation',
            'MenuEntry-extract=Extract text']
    meta.extend(command_lines)
    (plugin_dir / f'{module}.plugin').write_text('\n'.join(meta) + '\n',
                                                 encoding='utf-8')
    if body is None:
        body = (
            "plugin_info = {\n"
            f"    'Module': '{module}',\n"
            f"    'Name': 'MiAZ{module.upper()}',\n"
            "    'Description': 'A plugin',\n"
            "    'Operations': [{\n"
            "        'name': 'ocr',\n"
            "        'help': 'Read a document',\n"
            "        'run': 'run_ocr',\n"
            "        'params': [\n"
            "            {'name': 'document', 'positional': True},\n"
            "            {'name': 'language', 'default': 'eng'},\n"
            "        ],\n"
            "    }],\n"
            "}\n"
            "\n"
            "\n"
            "def run_ocr(app, args, stdout, stderr):\n"
            "    stdout.write(f'{args.document}:{args.language}\\n')\n"
            "    return 0\n")
    (plugin_dir / f'{module}.py').write_text(body, encoding='utf-8')
    return plugin_dir


def test_a_command_declared_in_a_plugin_file_is_discovered(tmp_path):
    make_plugin(tmp_path)

    commands = discover_commands([str(tmp_path)])

    assert 'ocr' in commands
    assert commands['ocr']['help'] == 'Read a document'
    assert commands['ocr']['module'] == 'ocr'


def test_discovery_does_not_import_the_plugin(tmp_path):
    """The whole reason the names live in the .plugin file.

    A plugin whose module does not even parse is still discovered, which is
    the proof that nothing imported it. Import happens when the command runs.
    """
    make_plugin(tmp_path, body='this is not python(((\n')

    assert 'ocr' in discover_commands([str(tmp_path)])


def test_a_plugin_that_declares_no_command_contributes_none(tmp_path):
    """Most plugins are GUI-only and should stay invisible to the CLI."""
    make_plugin(tmp_path, module='fullscreen', command_lines=())

    assert discover_commands([str(tmp_path)]) == {}


def test_a_missing_plugin_directory_is_not_an_error(tmp_path):
    """A fresh install that has never opened the window has no user plugin
    directory yet. That is not a reason for `miaz search` to fail."""
    assert discover_commands([str(tmp_path / 'nope')]) == {}


def test_plugin_commands_join_the_known_commands(tmp_path):
    """miaz.py decides between the window and the command line by testing the
    first argument against this set, before anything is loaded. A plugin
    command that is not in it would open the window instead."""
    make_plugin(tmp_path)

    commands = known_commands([str(tmp_path)])

    assert 'ocr' in commands
    assert 'search' in commands, 'the built-in commands must survive'
    assert 'repos' in commands


def test_the_built_in_commands_need_no_plugin_directory():
    """build_parser() is called with no arguments all over the tests and by
    anything that only wants the built-ins."""
    assert 'search' in known_commands()
    assert build_parser() is not None


def test_a_plugin_command_gets_its_declared_flags(tmp_path):
    """The parameter schema comes from plugin_info, read at parse time."""
    make_plugin(tmp_path)

    parser = build_parser([str(tmp_path)])
    args = parser.parse_args(['ocr', 'DOC-1', '--language', 'spa'])

    assert args.command == 'ocr'
    assert args.document == 'DOC-1'
    assert args.language == 'spa'


def with_plugins(env, plugins_dir):
    """Point an isolated ENV's plugin directories at a temporary one.

    Built on the miaz_env fixture rather than on the real ENV, so these tests
    never touch the developer's own repository and still pass on a machine
    that has none, which is what CI is.
    """
    env = dict(env)
    env['GPATH'] = dict(env['GPATH'], PLUGINS=str(plugins_dir))
    env['LPATH'] = dict(env['LPATH'], PLUGINS=str(plugins_dir / '_user'))
    return env


def test_running_a_plugin_command_calls_its_handler(tmp_path, miaz_env,
                                                    make_repo, register_repo):
    """End to end: the CLI imports the one module that owns the command,
    resolves the named callable and hands it the console app."""
    plugins = tmp_path / 'plugins'
    make_plugin(plugins)
    register_repo(miaz_env, 'Home', make_repo('Home'), current=True)
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', 'DOC-1', '--language', 'spa'], stdout, stderr,
                env=with_plugins(miaz_env, plugins))

    assert code == 0, stderr.getvalue()
    assert stdout.getvalue() == 'DOC-1:spa\n'


def test_a_plugin_command_runs_against_the_open_repository(tmp_path, miaz_env,
                                                           make_repo, register_repo):
    """A plugin command is handed the console app with its repository already
    open, so it reaches documents the same way `search` does."""
    plugins = tmp_path / 'plugins'
    make_plugin(plugins, module='ocrrepo',
                command_lines=('Command-ocrrepo=Name the repository',),
                body=("plugin_info = {\n"
                      "    'Operations': [{'name': 'ocrrepo', "
                      "'run': 'run_ocr', 'params': []}],\n"
                      "}\n"
                      "\n"
                      "\n"
                      "def run_ocr(app, args, stdout, stderr):\n"
                      "    index = app.get_service('index')\n"
                      "    stdout.write(f'{index is not None}\\n')\n"
                      "    return 0\n"))
    register_repo(miaz_env, 'Home', make_repo('Home'), current=True)
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocrrepo'], stdout, stderr, env=with_plugins(miaz_env, plugins))

    assert code == 0, stderr.getvalue()
    assert stdout.getvalue() == 'True\n'


def test_a_plugin_command_whose_handler_is_missing_reports_which_plugin(
        tmp_path, miaz_env, make_repo, register_repo):
    """A plugin naming a callable it does not define is the plugin's bug. Say
    so, rather than dying with an AttributeError from inside the CLI."""
    plugins = tmp_path / 'plugins'
    # Its own module name: import_module caches in sys.modules by name, so a
    # second plugin called 'ocr' in another directory would reuse the first
    # one's schema.
    make_plugin(plugins, module='ocrbroken',
                command_lines=('Command-ocrbroken=Read a document',),
                body=("plugin_info = {\n"
                      "    'Operations': [{'name': 'ocrbroken', "
                      "'run': 'run_ocr', 'params': []}],\n"
                      "}\n"))
    register_repo(miaz_env, 'Home', make_repo('Home'), current=True)
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocrbroken'], stdout, stderr, env=with_plugins(miaz_env, plugins))

    assert code == 2
    assert 'run_ocr' in stderr.getvalue()
    assert 'ocrbroken' in stderr.getvalue()


def test_a_plugin_cannot_take_over_a_built_in_command(tmp_path):
    """`search` means one thing. A plugin declaring it does not get to decide
    what, and the answer must not depend on which plugin was scanned last."""
    plugins = tmp_path / 'plugins'
    make_plugin(plugins, module='hijack',
                command_lines=('Command-search=Not the real search',))

    parser = build_parser([str(plugins)])
    args = parser.parse_args(['search', 'invoice'])

    assert args.text == 'invoice', 'the built-in search parser was replaced'


def test_miaz_dispatches_a_plugin_command_instead_of_opening_the_window(tmp_path):
    """The integration point.

    miaz.py chooses between the window and the command line by testing the
    first argument, before anything is loaded. Built against the built-in
    command set alone, a plugin command falls through to the window.

    Run with no display, so the two outcomes are unmistakable: the command
    prints its line, or the window path complains that it has nowhere to draw.
    """
    import subprocess
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = tmp_path / 'home'
    # Where ENV puts the user plugin directory, given this HOME.
    plugins = home / '.MiAZ' / 'opt' / 'plugins'
    make_plugin(plugins, module='clidispatch',
                command_lines=('Command-clidispatch=Prove the dispatch',),
                body=("plugin_info = {\n"
                      "    'Operations': [{'name': 'clidispatch', "
                      "'run': 'run_it', 'params': []}],\n"
                      "}\n"
                      "\n"
                      "\n"
                      "def run_it(app, args, stdout, stderr):\n"
                      "    stdout.write('DISPATCHED\\n')\n"
                      "    return 0\n"))

    repo = tmp_path / 'repo'
    (repo / '.conf').mkdir(parents=True)
    (repo / '.conf' / 'repo.json').write_text('{"FORMAT": 1}', encoding='utf-8')

    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
           'HOME': str(home), 'PYTHONPATH': root, 'LC_ALL': 'C'}
    result = subprocess.run([sys.executable, '-m', 'MiAZ.miaz', 'clidispatch',
                             '--repo', str(repo)],
                            cwd=root, env=env, capture_output=True, text=True,
                            timeout=120)

    assert 'found no display' not in result.stderr, (
        'miaz treated a plugin command as a reason to open the window')
    assert 'DISPATCHED' in result.stdout, (
        f"stdout={result.stdout!r} stderr={result.stderr[-2000:]!r}")
