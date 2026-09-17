#!/usr/bin/python3

"""
Tests for MiAZ.backend.importer, which puts documents into a repository.

The expansion and the copying were inside the desktop import service, in a
module that imports Gtk at the top, so `miaz add` could not have reached them
without a display. They are the same functions; what moved is where they live.

Runs without a display: os and MiAZUtil, no GTK.
"""

import os

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from MiAZ.backend.importer import expand_paths, free_target, import_paths
from MiAZ.backend.util import MiAZUtil


class MockApp:
    """MiAZUtil stores the app and, for these calls, never asks it anything."""

    def get_config(self, name):
        return None


def util():
    return MiAZUtil(MockApp())


def _tree(root):
    """A folder with two files, a subfolder with two more, and a loose file."""
    os.makedirs(os.path.join(root, 'folder', 'sub'))
    for path in (
        os.path.join(root, 'loose.pdf'),
        os.path.join(root, 'folder', 'one.pdf'),
        os.path.join(root, 'folder', 'two.pdf'),
        os.path.join(root, 'folder', 'sub', 'three.pdf'),
        os.path.join(root, 'folder', 'sub', 'four.pdf'),
    ):
        with open(path, 'w', encoding='utf-8') as handler:
            handler.write('document')
    return root


# ---------------------------------------------------------------------------
# expand_paths
# ---------------------------------------------------------------------------

def test_files_are_kept_as_they_are(tmp_path):
    root = _tree(str(tmp_path))
    loose = os.path.join(root, 'loose.pdf')
    assert expand_paths([loose]) == [loose]


def test_a_directory_gives_its_direct_files(tmp_path):
    root = _tree(str(tmp_path))
    found = expand_paths([os.path.join(root, 'folder')])
    assert [os.path.basename(path) for path in found] == ['one.pdf', 'two.pdf']


def test_a_directory_recursive_gives_the_whole_tree(tmp_path):
    root = _tree(str(tmp_path))
    found = expand_paths([os.path.join(root, 'folder')], recursive=True)
    assert sorted(os.path.basename(path) for path in found) == [
        'four.pdf', 'one.pdf', 'three.pdf', 'two.pdf']


def test_files_and_directories_mixed(tmp_path):
    root = _tree(str(tmp_path))
    given = [os.path.join(root, 'loose.pdf'), os.path.join(root, 'folder')]
    assert len(expand_paths(given)) == 3
    assert len(expand_paths(given, recursive=True)) == 5


def test_the_order_given_is_the_order_imported(tmp_path):
    root = _tree(str(tmp_path))
    given = [os.path.join(root, 'loose.pdf'), os.path.join(root, 'folder')]
    assert os.path.basename(expand_paths(given)[0]) == 'loose.pdf'


def test_the_files_of_a_directory_are_sorted(tmp_path):
    """os.listdir order is arbitrary; the import order should not be."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'folder'))
    for name in ('c.pdf', 'a.pdf', 'b.pdf'):
        with open(os.path.join(root, 'folder', name), 'w', encoding='utf-8') as handler:
            handler.write('document')
    found = expand_paths([os.path.join(root, 'folder')])
    assert [os.path.basename(path) for path in found] == ['a.pdf', 'b.pdf', 'c.pdf']


def test_an_empty_directory_gives_nothing(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'empty'))
    assert expand_paths([os.path.join(root, 'empty')]) == []
    assert expand_paths([os.path.join(root, 'empty')], recursive=True) == []


def test_a_missing_path_is_kept(tmp_path):
    """Kept, not dropped: the import reports it as failed instead of hiding it."""
    missing = os.path.join(str(tmp_path), 'gone.pdf')
    assert expand_paths([missing]) == [missing]


def test_empty_paths_are_ignored(tmp_path):
    """A remote URI has no local path, and Gio gives None for it."""
    root = _tree(str(tmp_path))
    loose = os.path.join(root, 'loose.pdf')
    assert expand_paths([None, '', loose]) == [loose]


def test_a_symlinked_subdirectory_is_not_followed(tmp_path):
    """A link back up the tree would otherwise walk forever."""
    root = _tree(str(tmp_path))
    os.symlink(os.path.join(root, 'folder'),
               os.path.join(root, 'folder', 'sub', 'loop'))
    found = expand_paths([os.path.join(root, 'folder')], recursive=True)
    assert len(found) == 4


def test_a_file_named_twice_is_imported_once(tmp_path):
    """A file given on its own and inside its directory is still one import."""
    root = _tree(str(tmp_path))
    given = [os.path.join(root, 'folder', 'one.pdf'),
             os.path.join(root, 'folder')]
    found = expand_paths(given)
    assert [os.path.basename(path) for path in found] == ['one.pdf', 'two.pdf']


# ---------------------------------------------------------------------------
# free_target
# ---------------------------------------------------------------------------

def test_a_free_name_is_used_as_it_is(tmp_path):
    docs = str(tmp_path)
    assert free_target(docs, '-----INVOICE-.pdf') == os.path.join(
        docs, '-----INVOICE-.pdf')


def test_a_taken_name_gets_a_number_on_the_concept(tmp_path):
    """The concept, not the end of the name: the last field is who it was sent
    to, and a suffix there would invent a recipient."""
    docs = str(tmp_path)
    (tmp_path / '-----INVOICE-.pdf').write_text('first')
    assert os.path.basename(free_target(docs, '-----INVOICE-.pdf')) == \
        '-----INVOICE_2-.pdf'


def test_the_number_counts_up_until_a_name_is_free(tmp_path):
    docs = str(tmp_path)
    (tmp_path / '-----INVOICE-.pdf').write_text('first')
    (tmp_path / '-----INVOICE_2-.pdf').write_text('second')
    assert os.path.basename(free_target(docs, '-----INVOICE-.pdf')) == \
        '-----INVOICE_3-.pdf'


def test_a_name_with_no_extension_is_numbered_too(tmp_path):
    docs = str(tmp_path)
    (tmp_path / '-----README-').write_text('first')
    assert os.path.basename(free_target(docs, '-----README-')) == \
        '-----README_2-'


# ---------------------------------------------------------------------------
# import_paths
# ---------------------------------------------------------------------------

def test_a_document_arrives_under_a_normalized_name(tmp_path):
    docs = str(tmp_path / 'repo')
    os.makedirs(docs)
    source = tmp_path / 'bank statement.pdf'
    source.write_text('document')

    imported, failed = import_paths(util(), docs, [str(source)])

    assert failed == []
    assert imported == ['-----BANK_STATEMENT-.pdf']
    assert os.path.exists(os.path.join(docs, '-----BANK_STATEMENT-.pdf'))


def test_a_document_already_named_the_miaz_way_keeps_its_name(tmp_path):
    docs = str(tmp_path / 'repo')
    os.makedirs(docs)
    name = '20240115-ES-HOU-BANK-INV-RENT-JOHN.pdf'
    source = tmp_path / name
    source.write_text('document')

    imported, _failed = import_paths(util(), docs, [str(source)])

    assert imported == [name]


def test_the_source_file_stays_where_it_is(tmp_path):
    docs = str(tmp_path / 'repo')
    os.makedirs(docs)
    source = tmp_path / 'invoice.pdf'
    source.write_text('document')

    import_paths(util(), docs, [str(source)])

    assert source.exists()


def test_a_second_document_with_the_same_name_does_not_replace_the_first(tmp_path):
    """Two directories can each hold a scan.pdf. Overwriting would lose one of
    them, and a recursive import of a scan folder is where that happens."""
    docs = str(tmp_path / 'repo')
    os.makedirs(docs)
    for index, folder in enumerate(('one', 'two')):
        os.makedirs(tmp_path / folder)
        (tmp_path / folder / 'scan.pdf').write_text(f'document {index}')

    imported, failed = import_paths(
        util(), docs,
        [str(tmp_path / 'one' / 'scan.pdf'), str(tmp_path / 'two' / 'scan.pdf')])

    assert failed == []
    assert imported == ['-----SCAN-.pdf', '-----SCAN_2-.pdf']
    with open(os.path.join(docs, '-----SCAN-.pdf'), encoding='utf-8') as handler:
        assert handler.read() == 'document 0'
    with open(os.path.join(docs, '-----SCAN_2-.pdf'), encoding='utf-8') as handler:
        assert handler.read() == 'document 1'


def test_a_missing_source_is_reported_and_the_rest_still_arrive(tmp_path):
    docs = str(tmp_path / 'repo')
    os.makedirs(docs)
    good = tmp_path / 'invoice.pdf'
    good.write_text('document')
    missing = str(tmp_path / 'gone.pdf')

    imported, failed = import_paths(util(), docs, [missing, str(good)])

    assert imported == ['-----INVOICE-.pdf']
    assert failed == ['gone.pdf']


def test_nothing_to_import_is_not_an_error(tmp_path):
    docs = str(tmp_path / 'repo')
    os.makedirs(docs)
    assert import_paths(util(), docs, []) == ([], [])


# ---------------------------------------------------------------------------
# Reporting: a massive import is one job, so it has to say where it has got to
# ---------------------------------------------------------------------------

def test_importing_reports_each_document(tmp_path):
    """Without this a 1322 document import shows "1 running" for minutes."""
    docs = tmp_path / 'repo'
    docs.mkdir()
    sources = []
    for index in range(3):
        source = tmp_path / f'20260101-ES-HOU-ACME-INV-doc{index}-JOHNDOE.pdf'
        source.write_text('x')
        sources.append(str(source))

    said = []
    import_paths(util(), str(docs), sources,
                 report=lambda message, fraction: said.append(
                     (message, fraction)))

    assert len(said) == 3, f'reported {len(said)} times for 3 documents'
    assert said[-1][1] == 1.0, 'the last document is not the whole of it'


def test_importing_without_a_reporter_still_works(tmp_path):
    """`miaz add` passes none, and must not have to."""
    docs = tmp_path / 'repo'
    docs.mkdir()
    source = tmp_path / '20260101-ES-HOU-ACME-INV-doc-JOHNDOE.pdf'
    source.write_text('x')
    imported, failed = import_paths(util(), str(docs), [str(source)])
    assert len(imported) == 1
    assert failed == []
