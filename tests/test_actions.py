#!/usr/bin/python3

"""
Tests for the pure helpers in the actions service
(MiAZ.frontend.desktop.services.actions).

document_names_text is what "Copy document names" puts on the clipboard. It
was the MiAZCopy2Clipboard plugin until the action moved into the core. The
composition is tested here rather than through the clipboard itself: on
Wayland a client may only set the clipboard while its window has the focus,
so a test that reads the value back is testing the compositor.

The module imports GTK and Adw, so the test sets the gi versions first (the
app does the same in miaz.py). Importing it creates no widgets.
"""

import collections

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from MiAZ.frontend.desktop.services import actions as m


Item = collections.namedtuple('Item', ['id'])


def test_one_document_is_its_own_name():
    item = Item('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    assert m.document_names_text([item]) == item.id


def test_several_documents_are_one_per_line():
    items = [Item('a.pdf'), Item('b.pdf'), Item('c.pdf')]
    assert m.document_names_text(items) == 'a.pdf\nb.pdf\nc.pdf'


def test_the_order_is_the_selection_order():
    items = [Item('c.pdf'), Item('a.pdf')]
    assert m.document_names_text(items) == 'c.pdf\na.pdf'


def test_no_documents_is_empty_text():
    """Never used by the action, which stops on an empty selection, but a
    trailing newline or a stray separator here would show up in a paste."""
    assert m.document_names_text([]) == ''
