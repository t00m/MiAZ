#!/usr/bin/python3

"""
Tests for notes, which are core as of 0.3.

Notes started as MiAZNotes, a plugin, and its store was reachable only by
putting the plugin's own directory on sys.path and importing a top level
package called `lib`. MiAZOCR had to do exactly that to file the text it
extracted. A note is part of what MiAZ knows about a document, so the reading
and writing of one belongs in the backend, where it can be tested without a
display and used without a plugin being installed.

The views stayed where views belong.

There was no direct test coverage of any of this while it was a plugin, which
is the other half of why it moved: core modules in this project are the tested
ones.
"""

import os
import zipfile

import pytest

from MiAZ.backend.notes import (CategoryStore, NotesBackup, NotesStore,
                                notes_dir)


class QuietLog:
    """The store logs, and a test that prints its own noise is harder to read."""

    def __init__(self):
        self.errors = []

    def debug(self, *args):
        pass

    def warning(self, *args):
        self.errors.append(args)

    def error(self, *args):
        self.errors.append(args)

    def info(self, *args):
        pass


@pytest.fixture
def store(tmp_path):
    return NotesStore(str(tmp_path / 'notes'), QuietLog())


def test_the_notes_directory_did_not_move_with_the_code(tmp_path):
    """Moving code must not move data.

    Notes written while MiAZNotes was a plugin live under
    .conf/plugins/MiAZNotes/data, and every existing repository has them
    there. Keeping the path means no migration and nothing to lose; the
    location is only odd to read, which is worth less than the risk.
    """
    assert notes_dir('/repo') == '/repo/.conf/plugins/MiAZNotes/data'


def test_creating_a_note_writes_a_file_named_after_the_document(store):
    """A note is found by the document it belongs to, so the link is the
    filename rather than something inside the file."""
    path = store.create('DOC-1.pdf', {'Category': 'OCR'}, 'the body')

    assert os.path.isfile(path)
    assert os.path.basename(path).startswith('DOC-1.pdf')
    assert path.endswith('.md')


def test_a_note_reads_back_as_it_was_written(store):
    header, body = store.read(
        store.create('DOC-1.pdf', {'Category': 'OCR'}, 'the body'))

    assert header['Category'] == 'OCR'
    assert body.strip() == 'the body'


def test_a_note_carries_the_default_header_keys(store):
    """The header is what the list view sorts and filters on, so a note with
    half a header is a note that cannot be found."""
    header, _body = store.read(store.create('DOC-1.pdf', {}, 'x'))

    for key in ('Author', 'Category', 'Date', 'Priority', 'Status'):
        assert key in header, f'{key} missing from a fresh note'


def test_notes_are_counted_per_document(store):
    store.create('DOC-1.pdf', {}, 'one')
    store.create('DOC-1.pdf', {}, 'two')
    store.create('DOC-2.pdf', {}, 'three')

    assert store.count_for_document('DOC-1.pdf') == 2
    assert store.count_for_document('DOC-2.pdf') == 1
    assert store.count_for_document('DOC-3.pdf') == 0
    assert store.has_notes('DOC-1.pdf') is True
    assert store.has_notes('DOC-3.pdf') is False


def test_a_note_knows_which_document_it_belongs_to(store):
    path = store.create('DOC-1.pdf', {}, 'one')

    assert store.document_id_of(path) == 'DOC-1.pdf'


def test_renaming_a_document_takes_its_notes_with_it(store):
    """A rename is the commonest thing that happens to a document in MiAZ, and
    a note left behind under the old name is a note nobody finds again."""
    store.create('OLD.pdf', {}, 'one')
    store.create('OLD.pdf', {}, 'two')

    moved = store.rename_for_document('OLD.pdf', 'NEW.pdf')

    assert len(moved) == 2
    assert store.count_for_document('NEW.pdf') == 2
    assert store.count_for_document('OLD.pdf') == 0


def test_deleting_a_note_removes_only_that_one(store):
    first = store.create('DOC-1.pdf', {}, 'one')
    store.create('DOC-1.pdf', {}, 'two')

    store.delete(first)

    assert store.count_for_document('DOC-1.pdf') == 1


def test_a_note_updated_keeps_its_path(store):
    path = store.create('DOC-1.pdf', {'Category': 'General'}, 'before')

    store.update(path, {'Category': 'OCR'}, 'after')
    header, body = store.read(path)

    assert header['Category'] == 'OCR'
    assert body.strip() == 'after'


def test_reading_a_note_that_is_not_there_does_not_raise(store):
    """The workspace asks about documents whose notes may have been deleted
    outside MiAZ."""
    header, body = store.read('/nowhere/at/all.md')

    assert body == ''
    assert header


def test_categories_persist_next_to_the_notes(tmp_path):
    categories = CategoryStore(str(tmp_path / 'notes'), QuietLog())
    os.makedirs(str(tmp_path / 'notes'), exist_ok=True)

    assert categories.add('Invoices') is True
    assert categories.has('Invoices') is True
    assert 'Invoices' in categories.list()

    categories.remove('Invoices')
    assert categories.has('Invoices') is False


def test_a_broken_categories_file_is_not_a_crash(tmp_path):
    """It is a plain JSON file next to the notes, so a person can break it."""
    data_dir = tmp_path / 'notes'
    data_dir.mkdir()
    (data_dir / 'categories.json').write_text('not json', encoding='utf-8')

    assert CategoryStore(str(data_dir), QuietLog()).list() == []


def test_notes_survive_a_backup_and_a_restore(tmp_path):
    """Backup and restore are what a person reaches for before doing something
    they are not sure about, so a round trip has to be exact."""
    data_dir = str(tmp_path / 'notes')
    log = QuietLog()
    store = NotesStore(data_dir, log)
    store.create('DOC-1.pdf', {'Category': 'OCR'}, 'the body')
    backup = NotesBackup(data_dir, log)
    archive = str(tmp_path / 'notes.zip')

    assert backup.backup(archive) >= 1
    assert zipfile.is_zipfile(archive)

    backup.reset_data_dir()
    assert store.count_for_document('DOC-1.pdf') == 0

    backup.restore(archive)
    assert store.count_for_document('DOC-1.pdf') == 1
    _header, body = store.read(store.list_for_document('DOC-1.pdf')[0])
    assert body.strip() == 'the body'


def test_the_backup_name_says_what_it_is(tmp_path):
    name = NotesBackup(str(tmp_path), QuietLog()).default_backup_name()

    assert name.startswith('MiAZNotes-backup-')
    assert name.endswith('.zip')


def test_the_core_notes_module_needs_no_toolkit(tmp_path):
    """Notes are data. `miaz ocr` files one on a server with no display, and
    before this move it could only do so through a sys.path hack into the
    plugin's own `lib` package.
    """
    import subprocess
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
           'HOME': str(tmp_path), 'PYTHONPATH': root, 'LC_ALL': 'C'}
    result = subprocess.run(
        [sys.executable, '-c',
         'import sys\n'
         'import MiAZ.backend.notes\n'
         "toolkit = [m for m in sys.modules if m.startswith('gi.repository.')\n"
         "           and m.rsplit('.', 1)[-1] in ('Gtk', 'Adw', 'Gdk')]\n"
         "print('TOOLKIT:' + ','.join(sorted(toolkit)))\n"],
        cwd=root, env=env, capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stderr[-3000:]
    assert 'TOOLKIT:\n' in result.stdout, result.stdout.strip()


def test_a_note_is_plain_markdown_a_person_can_read(store):
    """The format is the feature: notes outlive MiAZ if they are readable
    without it."""
    path = store.create('DOC-1.pdf', {'Category': 'OCR'}, '# Heading\n\ntext')
    content = open(path, encoding='utf-8').read()

    assert content.startswith('---')
    assert 'Category: OCR' in content
    assert '# Heading' in content


def test_the_store_makes_its_directory(tmp_path):
    """Nothing creates it beforehand once notes are core: the first note in a
    repository is what brings the directory into being."""
    data_dir = str(tmp_path / 'brand' / 'new')

    NotesStore(data_dir, QuietLog())

    assert os.path.isdir(data_dir)


def test_two_notes_in_the_same_second_do_not_overwrite_each_other(store):
    """A note used to be named to the second, so a second note filed against
    one document inside that second landed on the same path and replaced the
    first, silently. Nobody clicking managed it often; `miaz ocr A.pdf A.pdf`
    manages it every time.
    """
    first = store.create('DOC-1.pdf', {}, 'first note')
    second = store.create('DOC-1.pdf', {}, 'second note')

    assert first != second, 'the second note overwrote the first'
    assert store.count_for_document('DOC-1.pdf') == 2

    bodies = {store.read(path)[1].strip() for path in
              store.list_for_document('DOC-1.pdf')}
    assert bodies == {'first note', 'second note'}


def test_a_note_with_a_collision_suffix_still_knows_its_document(store):
    """The suffix sits where document_id_of, list_for_document and
    rename_for_document all ignore it. Worth pinning, because it is the kind
    of thing a later tidy of the filename would quietly break."""
    store.create('DOC-1.pdf', {}, 'first')
    second = store.create('DOC-1.pdf', {}, 'second')

    assert store.document_id_of(second) == 'DOC-1.pdf'

    store.rename_for_document('DOC-1.pdf', 'DOC-2.pdf')
    assert store.count_for_document('DOC-2.pdf') == 2
    assert store.count_for_document('DOC-1.pdf') == 0
