# File: thumbnailcache.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Decoded preview images, kept in memory between binds

import os
from collections import OrderedDict

import gi
gi.require_version('Gdk', '4.0')

from gi.repository import Gdk
from gi.repository import GLib

from MiAZ.backend.log import MiAZLog

log = MiAZLog('MiAZ.ThumbnailCache')

# MiAZ.backend.thumbnails remembers which file holds the preview for a
# document. It cannot remember the pixels: decoded images are Gdk types and the
# backend imports no GUI toolkit. So every bind handed the path to
# Gtk.Picture.set_filename, which decodes the PNG again, on the main thread,
# for a row the user had already scrolled past once. This holds the decoded
# image instead, keyed by the path the backend answered with.

# How much decoded image to hold. A grid cell at 256px is about 370 KB and a
# 640px preview about 2.3 MB, so this covers a full screen of cells and the
# panel with room to spare. GTK uploads a texture to the GPU while it is on
# screen, so the resident cost is roughly double for what is being drawn.
MEMORY_BUDGET = 64 * 1024 * 1024

# Images pass through MiAZ.backend.thumbnails unrendered, at whatever size
# they are: a photograph from a phone decodes to tens of megabytes. Anything
# past this is shown and then let go, rather than spending the whole budget on
# one document.
ITEM_LIMIT = 8 * 1024 * 1024

# What an entry costs even when it holds nothing, so that files which cannot be
# decoded are still bounded by the budget rather than accumulating for free.
_ENTRY_COST = 4096

# key -> texture or None. Ordered by when each was last asked for, oldest
# first, which is the order they are dropped in.
_textures = OrderedDict()
_held = 0


def _key(path):
    """What identifies one decoded image, or None when the file is gone.

    The path already carries the content digest for a rendered PDF page, but a
    plain image is its own preview and can be edited in place under the same
    name. Size and modification time are what tell that apart, the same three
    values MiAZ.backend.thumbnails.thumbnail_key is built from. A stat costs
    microseconds; the decode it guards costs milliseconds.
    """
    try:
        status = os.stat(path)
    except OSError:
        return None
    return (path, status.st_mtime_ns, status.st_size)


def _load(path):
    """Decode path into a texture, or None when it cannot be read."""
    try:
        return Gdk.Texture.new_from_filename(path)
    except GLib.Error as error:
        log.debug(f"Cannot decode '{path}': {error}")
        return None


def _cost(texture):
    if texture is None:
        return _ENTRY_COST
    return max(_ENTRY_COST, texture.get_width() * texture.get_height() * 4)


def _remember(key, texture):
    global _held
    _textures[key] = texture
    _held += _cost(texture)
    while _held > MEMORY_BUDGET and len(_textures) > 1:
        _held -= _cost(_textures.popitem(last=False)[1])


def texture_for(path):
    """The decoded image for path, or None when there is nothing to show.

    A file that cannot be decoded is remembered as having no image, so a
    corrupt document does not cost a failed decode on every bind.
    """
    key = _key(path)
    if key is None:
        return None
    if key in _textures:
        _textures.move_to_end(key)
        return _textures[key]
    texture = _load(path)
    # Held only if it is worth holding. An oversized image is still returned,
    # so the document shows; it is just decoded again next time.
    if texture is None or _cost(texture) <= ITEM_LIMIT:
        _remember(key, texture)
    return texture


def set_thumbnail(picture, path):
    """Show path in picture, and say whether there was anything to show."""
    texture = texture_for(path)
    picture.set_paintable(texture)
    return texture is not None


def held_bytes():
    """Decoded bytes currently remembered."""
    return _held


def forget():
    """Drop everything. A texture still shown by a widget stays alive through
    that widget: this gives up the cache's own claim on it, nothing more."""
    global _held
    _textures.clear()
    _held = 0
