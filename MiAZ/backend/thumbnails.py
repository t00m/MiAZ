# File: thumbnails.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Preview images for documents. No GTK imports (backend layer).

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

from gi.repository import GLib

from MiAZ.backend.duplicates import file_digest
from MiAZ.backend.log import MiAZLog

log = MiAZLog('MiAZ.Thumbnails')

# One worker for the whole application. A thread per visible cell put hundreds
# of threads and pdftoppm processes between the user and the next frame; a page
# nobody has scrolled to yet is never worth a stall.
_renderer = ThreadPoolExecutor(max_workers=1, thread_name_prefix='thumbnail')

# What each request rendered to, so a recycled row costs a dictionary lookup
# instead of hashing the file again. None means there is no preview, so a
# document that cannot be rendered is not retried on every scroll.
_cache = {}

# Formats Gtk.Picture displays directly, no rendering step needed.
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}


def thumbnail_for(filepath: str, cache_dir: str, scale: int = 640):
    """Path to a preview image for filepath, or None when there is none.

    Images are their own preview. A PDF gets its first page rendered by
    pdftoppm into cache_dir, keyed by content hash so a renamed file keeps
    its thumbnail and an edited file gets a fresh one. Anything else has no
    preview.
    """
    if not os.path.isfile(filepath):
        return None
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return filepath
    if ext != '.pdf':
        return None
    digest = file_digest(filepath)
    if digest is None:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    target = os.path.join(cache_dir, f"{digest}-{scale}.png")
    if os.path.exists(target):
        return target
    # -singlefile makes pdftoppm write exactly <prefix>.png.
    prefix = target[:-4]
    try:
        subprocess.run(['pdftoppm', '-png', '-f', '1', '-l', '1', '-singlefile',
                        '-scale-to', str(scale), filepath, prefix],
                       check=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        log.debug(f"Cannot render '{filepath}': {error}")
        return None
    return target if os.path.exists(target) else None


def thumbnail_key(filepath: str, scale: int):
    """What identifies one rendered image, or None when the file cannot be read.

    The scale is part of the key. Without it a grid asking for 256px and a
    preview asking for 640px would answer each other's questions.
    """
    try:
        status = os.stat(filepath)
    except OSError:
        return None
    return (filepath, status.st_mtime_ns, status.st_size, scale)


def cached_thumbnail(key):
    """The path already rendered for key, or False when it has never been asked.

    None is a real answer here (no preview), so it cannot double as "unknown".
    """
    return _cache.get(key, False)


def request_thumbnail(filepath, cache_dir, scale, on_done, is_wanted=None):
    """Render filepath in the background and call on_done(path_or_None) later.

    on_done runs on the main loop. A cached answer is delivered straight away,
    still through the main loop, so callers see one behaviour either way.
    is_wanted is asked again just before the work starts: a fast scroll queues
    cells the user has already left behind, and rendering those costs a real
    PDF each while the cells that are on screen wait their turn.
    """
    key = thumbnail_key(filepath, scale)
    if key is None:
        GLib.idle_add(_deliver, on_done, None)
        return None
    known = _cache.get(key, False)
    if known is not False:
        GLib.idle_add(_deliver, on_done, known)
        return key

    def work():
        if is_wanted is not None and not is_wanted():
            return False
        return thumbnail_for(filepath, cache_dir, scale=scale)

    def done(future):
        try:
            path = future.result()
        except Exception as error:
            log.debug(f"Cannot render '{filepath}': {error}")
            path = None
        # False means the request was abandoned before it ran, so nothing is
        # remembered: the document may well be asked for again.
        if path is not False:
            _cache[key] = path
            GLib.idle_add(_deliver, on_done, path)

    _renderer.submit(work).add_done_callback(done)
    return key


def _deliver(on_done, path):
    on_done(path)
    return GLib.SOURCE_REMOVE
