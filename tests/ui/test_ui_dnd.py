#!/usr/bin/python3

"""UI: files dropped on the workspace, and documents dragged out of it."""

import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk
from gi.repository import GObject
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


# ---------------------------------------------------------------------------
# Dragging documents out, into another application
# ---------------------------------------------------------------------------

def _drag_source(driver, key):
    source = driver.widget(key)
    assert source is not None, f'no drag source registered as {key}'
    return source


def _prepared(source, driver):
    """What the drag would carry, asked of the real prepare handler."""
    return source.emit('prepare', 0.0, 0.0)


def _select(driver, ids):
    """Select these documents in the shared selection model."""
    view = driver.widget('workspace-view')
    selection = view.get_selection()
    selection.unselect_all()
    model = selection.get_model()
    for position in range(model.get_n_items()):
        if model.get_item(position).id in ids:
            selection.select_item(position, False)
    driver.pump(0.3)


DRAG_SOURCES = ('workspace-view-drag-source', 'workspace-grid-drag-source')


def test_both_views_offer_a_drag_source(miaz):
    """The document list and the grid. The timeline is a reading view and is
    left out on purpose."""
    for key in DRAG_SOURCES:
        assert _drag_source(miaz, key) is not None


def test_a_drag_copies_and_never_moves(miaz):
    """A drop target offered MOVE may delete what it took, and here the file
    in the repository is the document itself."""
    for key in DRAG_SOURCES:
        actions = _drag_source(miaz, key).get_actions()
        assert actions == Gdk.DragAction.COPY, f'{key} offers {actions}'
        assert not (actions & Gdk.DragAction.MOVE), f'{key} would allow a move'


def test_dragging_carries_the_selected_documents(miaz, clean_view):
    """One selected document, dragged from either view."""
    wanted = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'
    _select(clean_view, {wanted})
    for key in DRAG_SOURCES:
        provider = _prepared(_drag_source(clean_view, key), clean_view)
        assert provider is not None, f'{key} refused a drag with a selection'
        assert provider.ref_formats().contain_gtype(Gdk.FileList.__gtype__)


def test_dragging_carries_every_selected_document(miaz, clean_view):
    """Pulling on one of several selected documents takes all of them, which
    is the whole point of selecting them first."""
    wanted = {'20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
              '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf'}
    _select(clean_view, wanted)
    workspace = clean_view.widget('workspace')
    assert {item.id for item in workspace.get_selected_items()} == wanted

    from MiAZ.frontend.desktop.widgets.dragout import document_files
    repository = clean_view.service('repo')
    files = document_files(workspace.get_selected_items(), repository.docs)
    assert {f.get_basename() for f in files} == wanted
    assert all(f.get_path().startswith(repository.docs) for f in files)


def test_nothing_selected_refuses_the_drag(miaz, clean_view):
    """A drag that would hand over nothing should not start."""
    view = clean_view.widget('workspace-view')
    view.get_selection().unselect_all()
    clean_view.pump(0.3)
    for key in DRAG_SOURCES:
        assert _prepared(_drag_source(clean_view, key), clean_view) is None


def test_the_document_keeps_its_repository_name(miaz, clean_view):
    """The file arrives under the name MiAZ filed it as."""
    from MiAZ.frontend.desktop.widgets.dragout import document_files
    wanted = '20240101-DE-ADM-CITY-NTF-permit-JOHNDOE.pdf'
    _select(clean_view, {wanted})
    repository = clean_view.service('repo')
    workspace = clean_view.widget('workspace')
    files = document_files(workspace.get_selected_items(), repository.docs)
    assert [f.get_basename() for f in files] == [wanted]


def test_selecting_still_works_with_the_drag_source_attached(miaz, clean_view):
    """A controller added to a view can swallow the clicks it was watching
    for. Selection is what everything else in the workspace reads."""
    view = clean_view.widget('workspace-view')
    selection = view.get_selection()
    selection.unselect_all()
    clean_view.pump(0.2)
    selection.select_item(0, True)
    clean_view.pump(0.3)
    workspace = clean_view.widget('workspace')
    assert len(workspace.get_selected_items()) == 1


# ---------------------------------------------------------------------------
# Dragging out of the workspace and back onto it
# ---------------------------------------------------------------------------

class _FakeDrop:
    """A Gdk.Drop carries the drag that started it only when that drag began
    in this application. A real one cannot be built without a real drag."""

    def __init__(self, drag=None):
        self._drag = drag

    def get_drag(self):
        return self._drag


def test_the_workspace_refuses_a_drag_that_started_in_it(miaz):
    """Dropping our own documents back on the workspace would copy every file
    onto itself. It is refused at accept, so the page never lights up."""
    workspace = miaz.widget('workspace')
    target = miaz.widget('workspace-drop-target')
    assert target is not None, 'no drop target on the workspace'
    assert workspace._on_drop_accept(target, _FakeDrop(drag=object())) is False


def test_the_workspace_still_accepts_files_from_elsewhere(miaz):
    """The refusal has to be narrow: dropping files in from a file manager is
    what the drop target is for."""
    workspace = miaz.widget('workspace')
    target = miaz.widget('workspace-drop-target')
    assert workspace._on_drop_accept(target, _FakeDrop(drag=None)) is True


def test_the_drop_target_asks_before_accepting(miaz):
    """The handler is only consulted if it is connected."""
    target = miaz.widget('workspace-drop-target')
    signal_id = GObject.signal_lookup('accept', target.__gtype__)
    handler = GObject.signal_handler_find(
        target, GObject.SignalMatchType.ID, signal_id, 0, None, None, None)
    assert handler != 0, 'nothing is connected to the drop target accept signal'
