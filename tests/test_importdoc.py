#!/usr/bin/python3

"""
Tests for the desktop import service (MiAZ.frontend.desktop.services.importdoc).

What is left here is the half that only means something with a window: whether
an import is big enough to go to a worker with the workspace held back. The
path expansion and the copying moved to MiAZ.backend.importer, where `miaz
add` can reach them, and are tested in tests/test_importer.py.

The module imports GTK and Adw, so the test sets the gi versions first (the
app does the same in miaz.py). Importing it creates no widgets and needs no
display.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from MiAZ.frontend.desktop.services import importdoc as m


# needs_batch: a big import holds the workspace back and runs off the main loop


def test_a_small_import_is_not_batched():
    assert m.needs_batch(1) is False
    assert m.needs_batch(m.BATCH_THRESHOLD) is False


def test_a_big_import_is_batched():
    assert m.needs_batch(m.BATCH_THRESHOLD + 1) is True


def test_nothing_to_import_is_not_batched():
    assert m.needs_batch(0) is False
