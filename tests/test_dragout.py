#!/usr/bin/python3

"""
Tests for dragging documents out of MiAZ into another application.

The two halves that carry the decisions are pure: which files a drag carries,
and what it offers them as. Both run without a display. Whether the drag source
is actually attached to the two views, and only offers COPY, is checked by
tests/ui/test_ui_dnd.py against the running application.
"""

import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gdk

from MiAZ.backend.models import MiAZItem
from MiAZ.frontend.desktop.widgets.dragout import (content_for, document_files,
                                                    started_here)


def item(name):
    return MiAZItem(id=name, title=name)


DOC = '20240315-ES-HOU-BANK-INV-Q1invoice-JOHNDOE.pdf'
OTHER = '20240316-ES-HOU-BANK-INV-second-JOHNDOE.pdf'


def touch(tmp_path, name):
    (tmp_path / name).write_text('x')
    return str(tmp_path / name)


def test_a_document_becomes_the_file_behind_it(tmp_path):
    """The repository holds real files, so a drag hands over the document
    itself and not a copy of it."""
    touch(tmp_path, DOC)
    files = document_files([item(DOC)], str(tmp_path))
    assert [f.get_basename() for f in files] == [DOC]
    assert files[0].get_path() == os.path.join(str(tmp_path), DOC)


def test_every_selected_document_is_carried(tmp_path):
    touch(tmp_path, DOC)
    touch(tmp_path, OTHER)
    files = document_files([item(DOC), item(OTHER)], str(tmp_path))
    assert sorted(f.get_basename() for f in files) == sorted([DOC, OTHER])


def test_the_raw_name_is_kept(tmp_path):
    """The file arrives under its MiAZ name. Renaming it to something readable
    would mean writing a copy somewhere first, which a drag cannot do."""
    touch(tmp_path, DOC)
    files = document_files([item(DOC)], str(tmp_path))
    assert files[0].get_basename() == DOC


def test_a_document_that_is_not_on_disk_is_left_out(tmp_path):
    """The list can name a document the watcher has not caught up with yet.
    Handing over a path to nothing gives the other application an error to
    report; leaving it out gives it the documents that are really there."""
    touch(tmp_path, DOC)
    files = document_files([item(DOC), item('gone.pdf')], str(tmp_path))
    assert [f.get_basename() for f in files] == [DOC]


def test_nothing_selected_carries_nothing(tmp_path):
    assert document_files([], str(tmp_path)) == []


def test_no_repository_carries_nothing():
    assert document_files([item(DOC)], None) == []


def test_the_offer_is_a_list_of_files(tmp_path):
    """Gdk.FileList is what a file manager, a mail client and a chat window
    all understand as 'these files'."""
    touch(tmp_path, DOC)
    provider = content_for(document_files([item(DOC)], str(tmp_path)))
    assert provider is not None
    assert provider.ref_formats().contain_gtype(Gdk.FileList.__gtype__)


def test_there_is_no_offer_when_there_are_no_files():
    """A drag source that prepares nothing refuses the drag, which is what
    should happen when the selection is empty."""
    assert content_for([]) is None


# ---------------------------------------------------------------------------
# A drag that starts here and ends here
# ---------------------------------------------------------------------------

class FakeDrop:
    """Gdk.Drop fills in the originating drag only when the drag began in this
    application, which is the whole question here."""

    def __init__(self, drag=None):
        self._drag = drag

    def get_drag(self):
        return self._drag


def test_a_drop_from_another_application_did_not_start_here():
    assert started_here(FakeDrop(drag=None)) is False


def test_a_drop_from_our_own_drag_started_here():
    """Dragging documents out of the workspace and back onto it asks MiAZ to
    import its own repository into itself."""
    assert started_here(FakeDrop(drag=object())) is True


def test_no_drop_at_all_did_not_start_here():
    """get_current_drop() is None outside a drag, and the question still has
    to have an answer."""
    assert started_here(None) is False
