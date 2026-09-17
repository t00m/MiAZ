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


# needs_batch also weighs the bytes, because the count alone said nothing


def test_a_few_large_documents_are_batched():
    """The case GNOME reported as "not responding".

    Twenty 40 MB scans is 800 MB copied on the main loop and never reached a
    count threshold of twenty. The compositor puts up its dialog after about
    five seconds of a window not answering, so a handful of large files from a
    slow source is enough.
    """
    assert m.needs_batch(3, m.BATCH_BYTES + 1) is True


def test_many_tiny_documents_are_still_batched_on_count():
    """The count rule is not replaced. A hundred small files is a hundred
    workspace refreshes and a hundred watcher events, whatever they weigh."""
    assert m.needs_batch(m.BATCH_THRESHOLD + 1, 0) is True


def test_a_small_light_import_stays_on_the_main_loop():
    """The machinery costs more than it saves for a couple of invoices."""
    assert m.needs_batch(2, 1024) is False
    assert m.needs_batch(m.BATCH_THRESHOLD, m.BATCH_BYTES) is False


def test_total_size_adds_up_what_will_be_copied(tmp_path):
    first = tmp_path / 'a.pdf'
    first.write_bytes(b'x' * 100)
    second = tmp_path / 'b.pdf'
    second.write_bytes(b'y' * 50)
    assert m.total_size([str(first), str(second)]) == 150


def test_total_size_ignores_a_path_it_cannot_measure(tmp_path):
    """A path that vanished between the chooser and the copy is the copy's
    problem to report, not a reason to fail the decision."""
    real = tmp_path / 'a.pdf'
    real.write_bytes(b'x' * 10)
    assert m.total_size([str(real), str(tmp_path / 'gone.pdf')]) == 10
