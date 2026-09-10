#!/usr/bin/python3

"""
Tests for MiAZOCR on the command line.

The plugin declares `Command-ocr` in its .plugin file, so `miaz ocr <document>`
reads the document and writes the text as a note, which is what the menu entry
does with the selection. Both go through MiAZ/backend/ocr.py, so there is one
implementation and not two.

These drive main() against the real plugin directory, because the point is
that the shipped MiAZOCR works, not that a fixture shaped like it does.
"""

import io
import os

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

import pytest

from MiAZ.frontend.console.cli import main
from tests.test_ocr import needs_ocrmypdf, needs_pdftotext, write_pdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS = os.path.join(ROOT, 'data', 'resources', 'plugins')

DOCUMENT = '20260101-ES-FIN-BANKX-INV-ocrtest-JOHNDOE.pdf'


@pytest.fixture
def repository(tmp_path, miaz_env, make_repo, register_repo):
    """A repository holding one PDF, and an ENV pointed at the real plugins."""
    repo = make_repo('Home')
    write_pdf(tmp_path / 'source.pdf', 'Hello OCR from MiAZ')
    with open(os.path.join(repo, DOCUMENT), 'wb') as handler:
        handler.write((tmp_path / 'source.pdf').read_bytes())
    register_repo(miaz_env, 'Home', repo, current=True)

    env = dict(miaz_env)
    env['GPATH'] = dict(env['GPATH'], PLUGINS=PLUGINS)
    env['LPATH'] = dict(env['LPATH'], PLUGINS=str(tmp_path / 'userplugins'))
    return env, repo


def notes_in(repo):
    """Every note this repository holds.

    Asks notes_dir rather than spelling the path out, so a move of the notes
    directory does not need this test changed with it.
    """
    from MiAZ.backend.notes import notes_dir
    data_dir = notes_dir(repo)
    if not os.path.isdir(data_dir):
        return []
    return sorted(name for name in os.listdir(data_dir) if name.endswith('.md'))


def test_the_plugin_declares_a_command():
    """Discovery reads the .plugin file, so the declaration has to be there
    and not only in plugin_info."""
    from MiAZ.backend.plugins import discover_commands

    commands = discover_commands([PLUGINS])

    assert 'ocr' in commands
    assert commands['ocr']['module'] == 'ocr'


def test_the_plugin_module_imports_without_a_toolkit():
    """MiAZOCR has to be importable on a server with no Gtk typelib, or the
    command it declares cannot run there.

    A subprocess, because pytest has imported GTK long before this runs.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, '-c',
         "import gi\n"
         "_real = gi.require_version\n"
         "def refuse(namespace, version):\n"
         "    if namespace in ('Gtk', 'Gdk', 'Adw'):\n"
         "        raise ValueError(namespace)\n"
         "    return _real(namespace, version)\n"
         "gi.require_version = refuse\n"
         "import importlib.util\n"
         f"spec = importlib.util.spec_from_file_location('ocr', {os.path.join(PLUGINS, 'MiAZOCR', 'ocr.py')!r})\n"
         "module = importlib.util.module_from_spec(spec)\n"
         "spec.loader.exec_module(module)\n"
         "print('OPERATIONS:' + str(len(module.plugin_info['Operations'])))\n"],
        cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT),
        capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stderr[-3000:]
    assert 'OPERATIONS:1' in result.stdout, result.stdout + result.stderr[-2000:]


@needs_pdftotext
def test_ocr_writes_a_note_for_the_named_document(repository):
    """The whole point: a document in, a note out, no window anywhere."""
    env, repo = repository
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', DOCUMENT], stdout, stderr, env=env)

    assert code == 0, stderr.getvalue()
    notes = notes_in(repo)
    assert len(notes) == 1, f'notes: {notes}, stderr: {stderr.getvalue()}'
    assert notes[0].startswith(DOCUMENT)


@needs_pdftotext
def test_the_note_holds_the_extracted_text_and_the_language(repository):
    """A note that does not say how it was made cannot be judged later."""
    env, repo = repository
    main(['ocr', DOCUMENT, '--language', 'eng'], io.StringIO(), io.StringIO(),
         env=env)

    from MiAZ.backend.notes import notes_dir
    note = os.path.join(notes_dir(repo), notes_in(repo)[0])
    with open(note, encoding='utf-8') as handler:
        content = handler.read()

    assert 'Hello OCR from MiAZ' in content
    assert 'eng' in content


@needs_pdftotext
def test_ocr_reads_more_than_one_document(repository):
    """The menu entry runs on the selection, which is usually several."""
    env, repo = repository
    second = DOCUMENT.replace('ocrtest', 'ocrtwo')
    with open(os.path.join(repo, second), 'wb') as handler:
        handler.write(open(os.path.join(repo, DOCUMENT), 'rb').read())
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', DOCUMENT, second], stdout, stderr, env=env)

    assert code == 0, stderr.getvalue()
    assert len(notes_in(repo)) == 2, stderr.getvalue()


def test_a_document_that_is_not_in_the_repository_is_reported(repository):
    """Naming the wrong file is the commonest mistake at a prompt. Say which
    one, and do not write a note for it."""
    env, repo = repository
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', 'NOT-A-DOCUMENT.pdf'], stdout, stderr, env=env)

    assert code == 1
    assert 'NOT-A-DOCUMENT.pdf' in stderr.getvalue()
    assert notes_in(repo) == []


@needs_pdftotext
def test_one_bad_document_does_not_stop_the_others(repository):
    """A batch has to survive a bad file, and still report it."""
    env, repo = repository
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', 'NOT-A-DOCUMENT.pdf', DOCUMENT], stdout, stderr, env=env)

    assert len(notes_in(repo)) == 1, stderr.getvalue()
    assert code == 1, 'a run with a failure in it should not report success'
    assert 'NOT-A-DOCUMENT.pdf' in stderr.getvalue()


@needs_ocrmypdf
def test_forcing_ocr_is_offered_on_the_command_line(repository):
    """--force is the flag that matters for a PDF whose text layer is wrong."""
    env, repo = repository
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', DOCUMENT, '--force'], stdout, stderr, env=env)

    assert code == 0, stderr.getvalue()
    assert len(notes_in(repo)) == 1


def test_the_document_is_never_modified(repository):
    """The repository's copy is the document."""
    env, repo = repository
    source = os.path.join(repo, DOCUMENT)
    before = open(source, 'rb').read()

    main(['ocr', DOCUMENT], io.StringIO(), io.StringIO(), env=env)

    assert open(source, 'rb').read() == before


@needs_pdftotext
def test_ocr_files_a_note_without_the_notes_plugin_installed(tmp_path, miaz_env,
                                                             make_repo,
                                                             register_repo):
    """Notes are core as of 0.3, so MiAZOCR needs no plugin to file one.

    The plugin directory here holds MiAZOCR and nothing else: no MiAZNotes to
    find, no `lib` package to put on sys.path. Before the move this returned 3
    saying there was nowhere to put the text.
    """
    plugins = tmp_path / 'onlyocr'
    (plugins / 'MiAZOCR').mkdir(parents=True)
    for name in ('ocr.py', 'ocr.plugin'):
        with open(os.path.join(PLUGINS, 'MiAZOCR', name), 'rb') as source:
            (plugins / 'MiAZOCR' / name).write_bytes(source.read())

    repo = make_repo('Home')
    write_pdf(tmp_path / 'source.pdf', 'Hello OCR from MiAZ')
    with open(os.path.join(repo, DOCUMENT), 'wb') as handler:
        handler.write((tmp_path / 'source.pdf').read_bytes())
    register_repo(miaz_env, 'Home', repo, current=True)

    env = dict(miaz_env)
    env['GPATH'] = dict(env['GPATH'], PLUGINS=str(plugins))
    env['LPATH'] = dict(env['LPATH'], PLUGINS=str(tmp_path / 'user'))
    stdout, stderr = io.StringIO(), io.StringIO()

    code = main(['ocr', DOCUMENT], stdout, stderr, env=env)

    assert code == 0, stderr.getvalue()
    assert len(notes_in(repo)) == 1, stderr.getvalue()


def test_the_plugin_no_longer_depends_on_another_plugin():
    """Notes moved to core, so the declaration has to go with it: a stale
    Dependencies line is a plugin that refuses to load for a missing thing
    that is no longer a thing."""
    from MiAZ.backend.plugins import get_plugin_attributes

    attributes = get_plugin_attributes(
        os.path.join(PLUGINS, 'MiAZOCR', 'ocr.plugin'))

    assert 'MiAZNotes' not in attributes.get('Dependencies', '')
