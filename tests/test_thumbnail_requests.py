#!/usr/bin/python3

"""The shared thumbnail request path: keys, memo and abandoned work."""

import time

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib

from MiAZ.backend import thumbnails


def settle(predicate, timeout=10):
    """Pump the main loop until predicate holds. The work is on a thread."""
    context = GLib.MainContext.default()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if predicate():
            return True
        time.sleep(0.005)
    return False


def test_the_scale_is_part_of_the_key(tmp_path):
    """A grid at 256px and a preview at 640px must not answer each other.

    The key started as path, mtime and size only, which was correct while the
    timeline was the only caller and always asked for the same width.
    """
    doc = tmp_path / 'a.pdf'
    doc.write_text('x')
    small = thumbnails.thumbnail_key(str(doc), 256)
    large = thumbnails.thumbnail_key(str(doc), 640)
    assert small is not None and large is not None
    assert small != large


def test_key_is_none_for_a_missing_file(tmp_path):
    assert thumbnails.thumbnail_key(str(tmp_path / 'gone.pdf'), 256) is None


def test_a_missing_file_still_answers(tmp_path):
    """Callers get exactly one answer, whatever happens."""
    answers = []
    thumbnails.request_thumbnail(str(tmp_path / 'gone.pdf'), str(tmp_path),
                                 256, answers.append)
    assert settle(lambda: answers), 'the caller was never answered'
    assert answers == [None]


def test_a_wanted_request_is_rendered_and_remembered(tmp_path):
    doc = tmp_path / 'd.pdf'
    doc.write_text('not really a pdf')
    answers = []
    key = thumbnails.request_thumbnail(str(doc), str(tmp_path / 'c'), 256,
                                       answers.append)
    assert settle(lambda: answers), 'the caller was never answered'
    assert answers == [None], 'a broken pdf answers None'
    assert thumbnails.cached_thumbnail(key) is None, 'and that is remembered'
    # A second ask is served from the memo rather than run again.
    answers.clear()
    thumbnails.request_thumbnail(str(doc), str(tmp_path / 'c'), 256, answers.append)
    assert settle(lambda: answers)
    assert answers == [None]


def test_an_unwanted_request_is_not_rendered_and_not_remembered(tmp_path):
    """Scrolling past a cell must not cost a rendered PDF.

    is_wanted is asked again just before the work starts, so a cell that has
    moved on, or a grid that has changed size, abandons the job.
    """
    skipped = tmp_path / 'b.pdf'
    skipped.write_text('not really a pdf')
    follower = tmp_path / 'e.pdf'
    follower.write_text('not really a pdf either')

    rendered = []
    original = thumbnails.thumbnail_for

    def spy(filepath, cache_dir, scale=640):
        rendered.append(filepath)
        return original(filepath, cache_dir, scale)

    thumbnails.thumbnail_for = spy
    try:
        key = thumbnails.request_thumbnail(str(skipped), str(tmp_path / 'c'), 256,
                                           lambda path: None,
                                           is_wanted=lambda: False)
        # One worker, first in first out: once the request queued behind it has
        # answered, the abandoned one has certainly been dealt with. Without
        # this the assertions below would pass on work that had not run yet.
        answers = []
        thumbnails.request_thumbnail(str(follower), str(tmp_path / 'c'), 256,
                                     answers.append)
        assert settle(lambda: answers), 'the follower was never answered'

        assert str(skipped) not in rendered, 'the abandoned document was rendered'
        assert str(follower) in rendered, 'the follower should have rendered'
        # Nothing is remembered either: the document may be asked for again.
        assert thumbnails.cached_thumbnail(key) is False
    finally:
        thumbnails.thumbnail_for = original
