#!/usr/bin/python3

"""Decoded preview images kept in memory.

The backend memo remembers which file a preview lives in. It does not remember
the pixels, so every Gtk.Picture.set_filename decoded the PNG again, on the
main thread, for a row the user had already scrolled past once. These cover the
layer that keeps the decoded image instead.

No display is needed: a texture is memory until something draws it.
"""

import cairo
import pytest

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from MiAZ.frontend.desktop.widgets import thumbnailcache
from MiAZ.frontend.desktop.widgets.thumbnailcache import (held_bytes,
                                                          set_thumbnail,
                                                          texture_for)


def make_png(path, width=100, height=100, shade=0.5):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)
    context.set_source_rgb(shade, shade, shade)
    context.paint()
    surface.write_to_png(str(path))
    return str(path)


@pytest.fixture(autouse=True)
def empty_cache():
    """Each test starts with nothing remembered."""
    thumbnailcache.forget()
    yield
    thumbnailcache.forget()


def test_the_same_image_is_decoded_once(tmp_path):
    """Scrolling back over a row already seen must not decode its PNG again."""
    path = make_png(tmp_path / 'page.png')
    assert texture_for(path) is texture_for(path)


def test_an_edited_image_is_decoded_again(tmp_path):
    """A PDF preview is keyed by digest, but a plain image is its own preview
    and can be edited in place under the same name."""
    path = make_png(tmp_path / 'photo.png', width=100)
    first = texture_for(path)
    make_png(tmp_path / 'photo.png', width=120)
    again = texture_for(path)
    assert again is not first
    assert again.get_width() == 120


def test_a_missing_file_has_no_texture(tmp_path):
    assert texture_for(str(tmp_path / 'gone.png')) is None


def test_an_unreadable_image_is_not_decoded_twice(tmp_path, monkeypatch):
    """A corrupt file would otherwise cost a failed decode on every bind."""
    broken = tmp_path / 'broken.png'
    broken.write_text('not a png')
    attempts = []
    original = thumbnailcache._load

    def counting(path):
        attempts.append(path)
        return original(path)

    monkeypatch.setattr(thumbnailcache, '_load', counting)
    assert texture_for(str(broken)) is None
    assert texture_for(str(broken)) is None
    assert len(attempts) == 1, 'the failure is remembered, not retried'


def test_the_budget_drops_the_least_recently_used(tmp_path, monkeypatch):
    """Memory is capped by decoded bytes, and what goes is what was not asked
    for most recently, not what arrived first."""
    # 100x100 RGBA is 40000 bytes, so two fit and the third pushes one out.
    monkeypatch.setattr(thumbnailcache, 'MEMORY_BUDGET', 90000)
    first = make_png(tmp_path / 'first.png', shade=0.1)
    second = make_png(tmp_path / 'second.png', shade=0.2)
    third = make_png(tmp_path / 'third.png', shade=0.3)
    kept = texture_for(first)
    dropped = texture_for(second)
    assert texture_for(first) is kept, 'asking again makes it the most recent'
    texture_for(third)
    assert texture_for(first) is kept, 'the one asked for last is still held'
    assert texture_for(second) is not dropped, 'the other one went'
    assert held_bytes() <= 90000


def test_an_image_too_large_is_shown_but_not_remembered(tmp_path, monkeypatch):
    """A full size photograph decodes to tens of megabytes. It is worth
    showing and not worth keeping."""
    monkeypatch.setattr(thumbnailcache, 'ITEM_LIMIT', 40000 - 1)
    path = make_png(tmp_path / 'huge.png')
    assert texture_for(path) is not None
    assert held_bytes() == 0
    assert texture_for(path) is not texture_for(path)


def test_a_picture_is_given_the_cached_texture(tmp_path):
    """What the call sites use instead of set_filename."""
    from gi.repository import Gtk
    path = make_png(tmp_path / 'page.png')
    picture = Gtk.Picture()
    assert set_thumbnail(picture, path) is True
    assert picture.get_paintable() is texture_for(path)


def test_a_picture_is_left_empty_when_there_is_nothing_to_show(tmp_path):
    from gi.repository import Gtk
    picture = Gtk.Picture()
    assert set_thumbnail(picture, str(tmp_path / 'gone.png')) is False
    assert picture.get_paintable() is None
