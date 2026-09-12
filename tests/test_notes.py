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
import shutil
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


# Migration out of the plugins directory
#
# ---------------------------------------------------------------------------
# search: what the command line and the all-notes view both ask for
# ---------------------------------------------------------------------------

def raw_note(store, filename, body='', date='2026-01-01 10:00:00',
             category='General', status='Draft', priority='Medium',
             author='t00m'):
    """A note file written by hand, so its date and header are the test's.

    create() stamps the current time into both the filename and the header,
    which makes an ordering or a date test impossible to write through it.
    """
    path = os.path.join(store.data_dir, filename)
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write(f"---\nAuthor: {author}\nCategory: {category}\n"
                      f"Date: {date}\nPriority: {priority}\n"
                      f"Status: {status}\n---\n\n{body}")
    return path


def test_search_with_no_filter_returns_every_note(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'one')
    raw_note(store, 'DOC-2.pdf_20260101100001.md', 'two')
    assert len(store.search()) == 2


def test_a_found_note_carries_its_document_and_its_header(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', '# Meter reading\n\nrest',
             category='OCR')
    note, = store.search()
    assert note.document_id == 'DOC-1.pdf'
    assert note.category == 'OCR'
    assert note.date == '2026-01-01 10:00:00'
    assert note.summary == 'Meter reading'
    assert note.body.startswith('# Meter reading')


def test_search_finds_text_in_the_body(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'the meter was read')
    raw_note(store, 'DOC-2.pdf_20260101100001.md', 'nothing to do with it')
    found = store.search('meter')
    assert [note.document_id for note in found] == ['DOC-1.pdf']


def test_search_finds_text_in_a_header_value(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'body', author='someone')
    assert len(store.search('someone')) == 1


def test_search_finds_text_in_the_document_it_is_filed_against(store):
    """A note about a Vattenfall letter need not have the word in it."""
    raw_note(store, '20260910-DE-HOU_E-VATTENFALL-REQ-X-TVG.pdf_20260101100000.md',
             'body')
    assert len(store.search('vattenfall')) == 1


def test_search_ignores_case(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'The Meter Was Read')
    assert len(store.search('mEtEr')) == 1


def test_search_narrows_by_document(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'same words')
    raw_note(store, 'DOC-2.pdf_20260101100001.md', 'same words')
    found = store.search(document='DOC-2')
    assert [note.document_id for note in found] == ['DOC-2.pdf']


def test_search_by_document_takes_part_of_the_name(store):
    raw_note(store, '20260910-DE-HOU_E-VATTENFALL-REQ-X-TVG.pdf_20260101100000.md',
             'body')
    assert len(store.search(document='vattenfall')) == 1


def test_search_filters_by_the_header_fields(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'one',
             category='OCR', status='Draft', priority='High')
    raw_note(store, 'DOC-2.pdf_20260101100001.md', 'two',
             category='General', status='Finished', priority='Medium')
    assert len(store.search(category='ocr')) == 1
    assert len(store.search(status='finish')) == 1
    assert len(store.search(priority='high')) == 1


def test_search_combines_its_filters(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'meter', category='OCR')
    raw_note(store, 'DOC-2.pdf_20260101100001.md', 'meter', category='General')
    found = store.search('meter', category='OCR')
    assert [note.document_id for note in found] == ['DOC-1.pdf']


def test_search_returns_the_newest_note_first(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'older',
             date='2026-01-01 10:00:00')
    raw_note(store, 'DOC-2.pdf_20260301100000.md', 'newer',
             date='2026-03-01 09:00:00')
    assert [note.body.strip() for note in store.search()] == ['newer', 'older']


def test_search_finding_nothing_is_an_empty_list(store):
    raw_note(store, 'DOC-1.pdf_20260101100000.md', 'body')
    assert store.search('nothing like it') == []


# Notes lived at <repo>/.conf/plugins/MiAZNotes while they were a plugin. They
# are core now and the path was the last thing still saying otherwise.

def legacy_tree(repo, notes=('DOC-1.pdf_20260101000000.md',), categories=True,
                where=('plugins', 'MiAZNotes')):
    """A repository whose notes are still in one of their old homes.

    Notes have lived in two places before `.conf/notes`: `.conf/plugins/
    MiAZNotes` while they were a plugin, and `.conf/MiAZNotes` for the short
    stretch between becoming core and getting a name that is not a plugin's.
    """
    legacy = os.path.join(repo, '.conf', *where)
    os.makedirs(os.path.join(legacy, 'data'), exist_ok=True)
    os.makedirs(os.path.join(legacy, 'conf'), exist_ok=True)
    for name in notes:
        with open(os.path.join(legacy, 'data', name), 'w', encoding='utf-8') as fp:
            fp.write(f'---\nCategory: General\n---\n\n{name}\n')
    if categories:
        with open(os.path.join(legacy, 'data', 'categories.json'), 'w',
                  encoding='utf-8') as fp:
            fp.write('["Invoices"]')
    with open(os.path.join(legacy, 'conf', 'Plugin-MiAZNotes.json'), 'w',
              encoding='utf-8') as fp:
        fp.write('{}')
    return legacy


def test_notes_live_in_a_directory_named_after_what_they_are(tmp_path):
    """`.conf/notes`, not a plugin's name."""
    from MiAZ.backend.notes import legacy_notes_dirs

    assert notes_dir('/repo') == '/repo/.conf/notes/data'
    assert legacy_notes_dirs('/repo') == ['/repo/.conf/plugins/MiAZNotes/data',
                                          '/repo/.conf/MiAZNotes/data']


def test_migration_moves_the_notes_out_of_the_plugins_directory(tmp_path):
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo)

    moved = migrate_notes(repo, QuietLog())

    assert moved >= 1
    assert os.path.isfile(os.path.join(notes_dir(repo), 'DOC-1.pdf_20260101000000.md'))
    assert not os.path.exists(os.path.join(repo, '.conf', 'plugins', 'MiAZNotes'))


def test_migration_keeps_everything_the_directory_held(tmp_path):
    """Not just the notes: the category list a person typed, and the settings
    file the plugin left behind. Moving is reversible, deciding what is junk
    is not."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo)

    migrate_notes(repo, QuietLog())

    assert os.path.isfile(os.path.join(notes_dir(repo), 'categories.json'))
    assert os.path.isfile(os.path.join(repo, '.conf', 'notes', 'conf',
                                       'Plugin-MiAZNotes.json'))


def test_migrated_notes_are_readable_through_the_store(tmp_path):
    """The point of the whole thing."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo)
    migrate_notes(repo, QuietLog())

    store = NotesStore(notes_dir(repo), QuietLog())
    assert store.count_for_document('DOC-1.pdf') == 1


def test_migration_does_nothing_when_there_is_nothing_to_move(tmp_path):
    """It runs on every repository open, so the common case is no case."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    os.makedirs(os.path.join(repo, '.conf'), exist_ok=True)

    assert migrate_notes(repo, QuietLog()) == 0


def test_migration_is_safe_to_run_again(tmp_path):
    """Every repository open runs it. The second one must be a no-op and must
    not disturb what the first one moved."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo)
    migrate_notes(repo, QuietLog())
    before = sorted(os.listdir(notes_dir(repo)))

    assert migrate_notes(repo, QuietLog()) == 0
    assert sorted(os.listdir(notes_dir(repo))) == before


def test_migration_never_overwrites_a_note_already_at_the_target(tmp_path):
    """Both directories can hold a note of the same name: a 0.2 MiAZ and a 0.3
    one opened the same repository in turn. Losing either is not acceptable, so
    the incoming one is kept under a new name.
    """
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo)
    os.makedirs(notes_dir(repo), exist_ok=True)
    target = os.path.join(notes_dir(repo), 'DOC-1.pdf_20260101000000.md')
    with open(target, 'w', encoding='utf-8') as fp:
        fp.write('---\nCategory: General\n---\n\nthe newer note\n')

    migrate_notes(repo, QuietLog())

    with open(target, encoding='utf-8') as fp:
        assert 'the newer note' in fp.read(), 'the target note was overwritten'
    # And the one that came from the old directory is still somewhere.
    survivors = [name for name in os.listdir(notes_dir(repo))
                 if name.startswith('DOC-1.pdf_')]
    assert len(survivors) == 2, f'a note was lost: {survivors}'


def test_a_repository_with_no_conf_directory_is_not_an_error(tmp_path):
    """migrate_notes is called on every open, including for a path that turns
    out not to be a repository at all."""
    from MiAZ.backend.notes import migrate_notes

    assert migrate_notes(str(tmp_path / 'nothing-here'), QuietLog()) == 0


def test_a_backup_taken_before_the_move_restores_after_it(tmp_path):
    """NotesBackup stores relative names, so a zip made when notes lived in
    the plugins directory restores into the new one. Worth pinning: a person
    reaches for a backup exactly when something has gone wrong."""
    repo = str(tmp_path / 'repo')
    legacy = legacy_tree(repo)
    log = QuietLog()
    archive = str(tmp_path / 'old-notes.zip')
    assert NotesBackup(os.path.join(legacy, 'data'), log).backup(archive) >= 1

    from MiAZ.backend.notes import migrate_notes
    migrate_notes(repo, log)

    # Wipe what was migrated, then restore the pre-move archive on top.
    store = NotesStore(notes_dir(repo), log)
    NotesBackup(notes_dir(repo), log).reset_data_dir()
    assert store.count_for_document('DOC-1.pdf') == 0

    NotesBackup(notes_dir(repo), log).restore(archive)
    assert store.count_for_document('DOC-1.pdf') == 1


def test_opening_a_repository_migrates_it(tmp_path, miaz_env, make_repo,
                                          register_repo):
    """The hook is repository.load(), not application start.

    Both frontends load a repository; only one of them is an application.
    Migrating at app start would leave a repository used from `miaz ocr` on a
    server writing new notes to the new directory while the old ones sat in the
    old one, and nothing would say so.
    """
    from MiAZ.frontend.console.app import MiAZConsoleApp

    repo = make_repo('Home')
    legacy_tree(repo)
    register_repo(miaz_env, 'Home', repo, current=True)

    code, message = MiAZConsoleApp(miaz_env).open_repository('Home')

    assert code == 0, message
    assert os.path.isfile(os.path.join(notes_dir(repo),
                                       'DOC-1.pdf_20260101000000.md'))
    assert not os.path.exists(os.path.join(repo, '.conf', 'plugins', 'MiAZNotes'))


def test_the_repository_config_backup_still_carries_the_notes(tmp_path, miaz_env,
                                                              make_repo,
                                                              register_repo):
    """Backup & Restore zips the whole .conf directory, so notes travel with
    it wherever inside .conf they live. Asserted rather than assumed: the move
    out of .conf/plugins would be a quiet way to drop them from every backup a
    person takes.
    """
    from MiAZ.backend.dr import MiAZDR
    from MiAZ.frontend.console.app import MiAZConsoleApp

    repo = make_repo('Home')
    register_repo(miaz_env, 'Home', repo, current=True)
    app = MiAZConsoleApp(miaz_env)
    assert app.open_repository('Home')[0] == 0

    store = NotesStore(notes_dir(repo), QuietLog())
    store.create('DOC-1.pdf', {'Category': 'OCR'}, 'the body')

    dest = tmp_path / 'backups'
    dest.mkdir()
    archive = MiAZDR(app).backup_config(os.path.join(repo, '.conf'), str(dest))

    assert archive and zipfile.is_zipfile(archive), archive
    names = zipfile.ZipFile(archive).namelist()
    assert any(name.startswith('notes/') and name.endswith('.md')
               for name in names), \
        f'no note in the configuration backup: {names}'


def test_restoring_a_config_backup_brings_the_notes_back(tmp_path, miaz_env,
                                                         make_repo,
                                                         register_repo):
    """The other half. A backup nobody can restore is not a backup."""
    from MiAZ.backend.dr import MiAZDR
    from MiAZ.frontend.console.app import MiAZConsoleApp

    repo = make_repo('Home')
    register_repo(miaz_env, 'Home', repo, current=True)
    app = MiAZConsoleApp(miaz_env)
    assert app.open_repository('Home')[0] == 0
    dr = MiAZDR(app)

    store = NotesStore(notes_dir(repo), QuietLog())
    store.create('DOC-1.pdf', {'Category': 'OCR'}, 'the body')
    dest = tmp_path / 'backups'
    dest.mkdir()
    archive = dr.backup_config(os.path.join(repo, '.conf'), str(dest))

    shutil.rmtree(notes_dir(repo))
    assert store.count_for_document('DOC-1.pdf') == 0

    dr.restore_config(os.path.join(repo, '.conf'), archive)

    assert store.count_for_document('DOC-1.pdf') == 1
    _header, body = store.read(store.list_for_document('DOC-1.pdf')[0])
    assert body.strip() == 'the body'


def test_migration_also_moves_the_short_lived_middle_location(tmp_path):
    """`.conf/MiAZNotes` existed between notes becoming core and the directory
    getting a name that is not a plugin's. Nobody should be stranded there for
    having opened MiAZ on the wrong afternoon."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo, where=('MiAZNotes',))

    moved = migrate_notes(repo, QuietLog())

    assert moved >= 1
    assert os.path.isfile(os.path.join(notes_dir(repo),
                                       'DOC-1.pdf_20260101000000.md'))
    assert not os.path.exists(os.path.join(repo, '.conf', 'MiAZNotes'))


def test_migration_gathers_notes_from_both_old_homes(tmp_path):
    """A repository can hold both: opened by a MiAZ that knew the plugin
    location and then by one that knew the middle one. Everything ends up in
    the same place and nothing is overwritten on the way."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo, notes=('DOC-1.pdf_20260101000000.md',),
                where=('plugins', 'MiAZNotes'))
    legacy_tree(repo, notes=('DOC-2.pdf_20260202000000.md',),
                where=('MiAZNotes',))

    migrate_notes(repo, QuietLog())

    store = NotesStore(notes_dir(repo), QuietLog())
    assert store.count_for_document('DOC-1.pdf') == 1
    assert store.count_for_document('DOC-2.pdf') == 1
    assert not os.path.exists(os.path.join(repo, '.conf', 'plugins', 'MiAZNotes'))
    assert not os.path.exists(os.path.join(repo, '.conf', 'MiAZNotes'))


def test_the_same_note_in_both_old_homes_survives_twice(tmp_path):
    """Same name in both, different content. Neither is the one to lose."""
    from MiAZ.backend.notes import migrate_notes

    repo = str(tmp_path / 'repo')
    legacy_tree(repo, where=('plugins', 'MiAZNotes'))
    legacy_tree(repo, where=('MiAZNotes',))

    migrate_notes(repo, QuietLog())

    survivors = [name for name in os.listdir(notes_dir(repo))
                 if name.startswith('DOC-1.pdf_')]
    assert len(survivors) == 2, f'a note was lost: {survivors}'
