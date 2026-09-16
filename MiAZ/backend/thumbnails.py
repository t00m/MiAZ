# File: thumbnails.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Preview images for documents. No GTK imports (backend layer).

import json
import os
import stat
import subprocess
import tempfile
import threading
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

# Rendered images are named after the content digest of the document, so a
# renamed document keeps its image. Computing that digest reads the whole file,
# which on a remote repository means fetching it, so the digest of a document
# already seen is remembered here against its identity. A rename changes none
# of the four values below, an edit changes the last two.
_INDEX_NAME = 'index.json'
_indexes = {}
_index_lock = threading.Lock()

# A cache file that only grows is a leak. Past this many entries the index
# starts again, which costs one re-read per document still in use.
_INDEX_LIMIT = 50000


def _identity(status):
    """What tells one version of one document from another."""
    return f"{status.st_dev}:{status.st_ino}:{status.st_size}:{status.st_mtime_ns}"


def _index_for(cache_dir):
    """The digests remembered for cache_dir, read from disk once per run.

    Callers hold _index_lock. A missing or damaged index is an empty one: it
    is a cache, and the worst an empty one costs is the reads it was meant to
    save.
    """
    index = _indexes.get(cache_dir)
    if index is not None:
        return index
    try:
        with open(os.path.join(cache_dir, _INDEX_NAME), encoding='utf-8') as handle:
            index = json.load(handle)
        if not isinstance(index, dict):
            index = {}
    except (OSError, ValueError):
        index = {}
    _indexes[cache_dir] = index
    return index


def _known_digest(cache_dir, identity):
    """The digest already computed for this exact file, or None."""
    with _index_lock:
        return _index_for(cache_dir).get(identity)


def _remember_digest(cache_dir, identity, digest):
    """Record a digest and write the index out.

    Written to a temporary file and moved into place, so an interrupted write
    leaves the previous index rather than a truncated one. A write that fails
    is logged and otherwise ignored: the next run recomputes what it needs.
    """
    with _index_lock:
        index = _index_for(cache_dir)
        if len(index) >= _INDEX_LIMIT:
            index.clear()
        index[identity] = digest
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    'w', encoding='utf-8', dir=cache_dir, prefix='index-',
                    suffix='.tmp', delete=False) as handle:
                temporary = handle.name
                json.dump(index, handle)
            os.replace(temporary, os.path.join(cache_dir, _INDEX_NAME))
        except OSError as error:
            log.debug(f"Cannot write the thumbnail index: {error}")
            if temporary is not None and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass


def thumbnail_for(filepath: str, cache_dir: str, scale: int = 640):
    """Path to a preview image for filepath, or None when there is none.

    Images are their own preview. A PDF gets its first page rendered by
    pdftoppm into cache_dir, keyed by content hash so a renamed file keeps
    its thumbnail and an edited file gets a fresh one. Anything else has no
    preview.

    The hash is computed once per version of a document and then remembered
    against the file identity, so a later call finds the rendered image with a
    stat rather than by reading the document again. A document whose bytes
    change without its size or modification time changing keeps the old image,
    which is the same trade every thumbnailer makes.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return filepath if os.path.isfile(filepath) else None
    if ext != '.pdf':
        return None
    try:
        status = os.stat(filepath)
    except OSError:
        return None
    if not stat.S_ISREG(status.st_mode):
        return None

    os.makedirs(cache_dir, exist_ok=True)
    identity = _identity(status)
    digest = _known_digest(cache_dir, identity)
    if digest is None:
        digest = file_digest(filepath)
        if digest is None:
            return None
        _remember_digest(cache_dir, identity, digest)

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
