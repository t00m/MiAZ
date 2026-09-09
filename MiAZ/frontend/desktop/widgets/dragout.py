# File: dragout.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Dragging documents out of MiAZ into another application

"""Documents leave MiAZ by being dragged, as well as by being exported.

The repository is a directory of real files, so a drag can hand another
application the document itself rather than a copy of a copy. What it offers is
a Gdk.FileList, which is what a file manager, a mail client and a chat window
all read as "these files".

The decisions live in the two functions below rather than in the signal
handler, so they can be tested without a display. What is attached to which
widget is in tests/ui/test_ui_dnd.py.
"""

import os

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk


def document_files(items, repo_dir) -> list:
    """The files behind these documents, those that are on disk.

    A document the watcher has not caught up with is left out. Handing over a
    path to nothing gives the other application an error to report, while
    leaving it out gives it the documents that are really there.

    The name is the one the repository uses. Renaming to something readable,
    the way MiAZExport2Dir can, means writing a copy somewhere first, and a
    drag has nowhere to write it to.
    """
    if not repo_dir:
        return []
    files = []
    for item in items or []:
        name = getattr(item, 'id', None)
        if not name:
            continue
        path = os.path.join(repo_dir, name)
        if os.path.isfile(path):
            files.append(Gio.File.new_for_path(path))
    return files


def content_for(files):
    """What the drag offers, or None when there is nothing to carry.

    Returning None from a prepare handler refuses the drag, which is what
    should happen when nothing is selected.
    """
    if not files:
        return None
    value = GObject.Value(Gdk.FileList, Gdk.FileList.new_from_list(files))
    return Gdk.ContentProvider.new_for_value(value)


def install_document_drag_source(widget, get_documents, get_repo_dir):
    """Let the documents shown in `widget` be dragged into another application.

    Both arguments are callables, read when the drag starts rather than when
    this runs: the selection and the open repository both change underneath.

    COPY, and nothing else. A drop target offered MOVE is entitled to delete
    what it took, and in MiAZ the file in the repository is the document, not a
    copy of one. There is no gesture here that should be able to empty a
    repository into somebody's mail client.
    """
    source = Gtk.DragSource()
    source.set_actions(Gdk.DragAction.COPY)

    def prepare(_source, _x, _y):
        return content_for(document_files(get_documents(), get_repo_dir()))

    source.connect('prepare', prepare)
    widget.add_controller(source)
    return source


def install_for_workspace_selection(widget, app, widget_key=None):
    """Drag whatever the workspace has selected out of `widget`.

    The grid and the document list share one selection model on purpose, so
    both ask the same question and a drag started in either carries the same
    documents. Neither is resolved until the drag begins: the grid is built
    before the workspace finishes registering itself.
    """
    def documents():
        workspace = app.get_widget('workspace')
        return workspace.get_selected_items() if workspace is not None else []

    def repo_dir():
        repository = app.get_service('repo')
        return repository.docs if repository is not None else None

    source = install_document_drag_source(widget, documents, repo_dir)
    if widget_key is not None:
        app.add_widget(widget_key, source)
    return source
