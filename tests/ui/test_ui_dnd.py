#!/usr/bin/python3

"""UI: dropping files on the workspace imports them into the repository."""

import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk
from gi.repository import Gtk


def _write(path, text='document'):
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write(text)
    return path


def _imported(driver, marker):
    """The repository files whose name carries our marker."""
    docs = driver.service('repo').docs
    return [name for name in os.listdir(docs) if marker in name.lower()]


def _cleanup(driver, marker):
    docs = driver.service('repo').docs
    for name in _imported(driver, marker):
        os.unlink(os.path.join(docs, name))
    driver.pump(0.4)


def test_the_documents_page_accepts_dropped_files(miaz):
    """The drop target is installed, on the documents page, for files."""
    drop = miaz.widget('workspace-drop-target')
    assert isinstance(drop, Gtk.DropTarget)
    assert drop.get_gtypes() == [Gdk.FileList.__gtype__]
    assert drop.get_actions() & Gdk.DragAction.COPY

    page = miaz.workspace.get_stack().get_child_by_name('workspace-default')
    controllers = [controller for controller in page.observe_controllers()]
    assert drop in controllers


def test_dropping_files_imports_them(miaz, tmp_path):
    """Files land in the repository, under a normalized name."""
    source = _write(os.path.join(str(tmp_path), 'droppedone.pdf'))
    try:
        miaz.service('importdoc').import_dropped([source])
        miaz.pump(0.5)
        found = _imported(miaz, 'droppedone')
        assert len(found) == 1
        # Normalized: seven fields, the concept holding the original name.
        # Stored filenames are uppercase, the extension is not.
        assert found[0].split('.')[0].split('-')[5] == 'DROPPEDONE'
    finally:
        _cleanup(miaz, 'droppedone')


def test_dropping_files_asks_nothing(miaz, tmp_path):
    """No folder means no question: the files are imported straight away."""
    source = _write(os.path.join(str(tmp_path), 'droppedtwo.pdf'))
    try:
        assert miaz.service('importdoc').import_dropped([source]) is None
    finally:
        _cleanup(miaz, 'droppedtwo')


def test_a_remote_path_alone_imports_nothing(miaz):
    """Gio gives None for a file with no local path."""
    assert miaz.service('importdoc').import_dropped([None]) is None


def test_dropping_a_folder_asks_first(miaz, tmp_path):
    """The dialog counts the folder's files, and recounts when ticked."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'folder', 'sub'))
    _write(os.path.join(root, 'folder', 'droppedthree.pdf'))
    _write(os.path.join(root, 'folder', 'droppedfour.pdf'))
    _write(os.path.join(root, 'folder', 'sub', 'droppedfive.pdf'))

    dialog = miaz.service('importdoc').import_dropped(
        [os.path.join(root, 'folder')])
    miaz.pump(0.3)
    try:
        assert dialog is not None
        # Nothing is imported while the question is on screen.
        assert _imported(miaz, 'dropped') == []

        check = miaz.widget('import-drop-recursive')
        label = miaz.widget('import-drop-count')
        assert check.get_active() is False
        assert '2' in label.get_text()

        check.set_active(True)
        miaz.pump(0.2)
        assert '3' in label.get_text()

        check.set_active(False)
        miaz.pump(0.2)
        assert '2' in label.get_text()
    finally:
        dialog.close()
        miaz.pump(0.3)


def test_answering_no_imports_nothing(miaz, tmp_path):
    """Cancelling the question cancels the whole drop."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'folder'))
    _write(os.path.join(root, 'folder', 'droppedsix.pdf'))

    importdoc = miaz.service('importdoc')
    dialog = importdoc.import_dropped([os.path.join(root, 'folder')])
    miaz.pump(0.3)
    dialog.close()
    miaz.pump(0.4)
    assert _imported(miaz, 'droppedsix') == []


def test_the_answer_decides_how_deep_the_import_goes(miaz, tmp_path):
    """Ticking the box imports the subfolders too; leaving it does not."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, 'folder', 'sub'))
    _write(os.path.join(root, 'folder', 'droppedseven.pdf'))
    _write(os.path.join(root, 'folder', 'sub', 'droppedeight.pdf'))
    dropped = [os.path.join(root, 'folder')]
    importdoc = miaz.service('importdoc')

    try:
        # Not recursive: the file in the subfolder stays out.
        dialog = importdoc.import_dropped(dropped)
        miaz.pump(0.3)
        miaz.widget('import-drop-recursive').set_active(False)
        dialog.emit('response', 'apply')
        miaz.pump(0.5)
        assert len(_imported(miaz, 'droppedseven')) == 1
        assert _imported(miaz, 'droppedeight') == []

        # Recursive: it comes in.
        dialog = importdoc.import_dropped(dropped)
        miaz.pump(0.3)
        miaz.widget('import-drop-recursive').set_active(True)
        dialog.emit('response', 'apply')
        miaz.pump(0.5)
        assert len(_imported(miaz, 'droppedeight')) == 1
    finally:
        _cleanup(miaz, 'dropped')
