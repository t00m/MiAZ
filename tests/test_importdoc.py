#!/usr/bin/python3

"""
Tests for the pure path expansion used by the import service
(MiAZ.frontend.desktop.services.importdoc).

expand_dropped() is what turns what the user dropped on the workspace into
the list of files to copy, and it is what the drop dialog counts to tell the
user how many files each choice would import. It is module-level and side
effect free: it only reads the filesystem.

The module imports GTK and Adw, so the test sets the gi versions first (the
app does the same in miaz.py). Importing it creates no widgets and needs no
display.
"""

import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from MiAZ.frontend.desktop.services import importdoc as m


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


def test_files_are_kept_as_they_are(tmp_path):
    root = _tree(str(tmp_path))
    loose = os.path.join(root, 'loose.pdf')
    assert m.expand_dropped([loose]) == [loose]


def test_folder_gives_its_direct_files(tmp_path):
    root = _tree(str(tmp_path))
    found = m.expand_dropped([os.path.join(root, 'folder')])
    assert [os.path.basename(path) for path in found] == ['one.pdf', 'two.pdf']


def test_folder_recursive_gives_the_whole_tree(tmp_path):
    root = _tree(str(tmp_path))
    found = m.expand_dropped([os.path.join(root, 'folder')], recursive=True)
    assert sorted(os.path.basename(path) for path in found) == [
        'four.pdf', 'one.pdf', 'three.pdf', 'two.pdf']


def test_files_and_folders_mixed(tmp_path):
    root = _tree(str(tmp_path))
    dropped = [os.path.join(root, 'loose.pdf'), os.path.join(root, 'folder')]
    assert len(m.expand_dropped(dropped)) == 3
    assert len(m.expand_dropped(dropped, recursive=True)) == 5


def test_the_dropped_file_comes_first(tmp_path):
    """Order is the order dropped, so the dialog and the import agree."""
    root = _tree(str(tmp_path))
    dropped = [os.path.join(root, 'loose.pdf'), os.path.join(root, 'folder')]
    assert os.path.basename(m.expand_dropped(dropped)[0]) == 'loose.pdf'


def test_folder_files_are_sorted(tmp_path):
    """os.listdir order is arbitrary; the import order should not be."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'folder'))
    for name in ('c.pdf', 'a.pdf', 'b.pdf'):
        with open(os.path.join(root, 'folder', name), 'w', encoding='utf-8') as handler:
            handler.write('document')
    found = m.expand_dropped([os.path.join(root, 'folder')])
    assert [os.path.basename(path) for path in found] == ['a.pdf', 'b.pdf', 'c.pdf']


def test_empty_folder_gives_nothing(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'empty'))
    assert m.expand_dropped([os.path.join(root, 'empty')]) == []
    assert m.expand_dropped([os.path.join(root, 'empty')], recursive=True) == []


def test_a_missing_path_is_kept(tmp_path):
    """Kept, not dropped: the import reports it as failed instead of hiding it."""
    missing = os.path.join(str(tmp_path), 'gone.pdf')
    assert m.expand_dropped([missing]) == [missing]


def test_empty_paths_are_ignored(tmp_path):
    """A remote URI has no local path, and Gio gives None for it."""
    root = _tree(str(tmp_path))
    loose = os.path.join(root, 'loose.pdf')
    assert m.expand_dropped([None, '', loose]) == [loose]


def test_a_symlinked_subfolder_is_not_followed(tmp_path):
    """A link back up the tree would otherwise walk forever."""
    root = _tree(str(tmp_path))
    os.symlink(os.path.join(root, 'folder'),
               os.path.join(root, 'folder', 'sub', 'loop'))
    found = m.expand_dropped([os.path.join(root, 'folder')], recursive=True)
    assert len(found) == 4


def test_duplicates_are_dropped_once(tmp_path):
    """A file dropped on its own and inside its folder is still one import."""
    root = _tree(str(tmp_path))
    dropped = [os.path.join(root, 'folder', 'one.pdf'),
               os.path.join(root, 'folder')]
    found = m.expand_dropped(dropped)
    assert [os.path.basename(path) for path in found] == ['one.pdf', 'two.pdf']


# needs_batch: a big import holds the workspace back and runs off the main loop


def test_a_small_import_is_not_batched():
    assert m.needs_batch(1) is False
    assert m.needs_batch(m.BATCH_THRESHOLD) is False


def test_a_big_import_is_batched():
    assert m.needs_batch(m.BATCH_THRESHOLD + 1) is True


def test_nothing_to_import_is_not_batched():
    assert m.needs_batch(0) is False
