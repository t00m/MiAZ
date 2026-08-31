# File: duplicates.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Find documents with identical content. No GTK/Adw/Gdk imports
#              (backend layer), so it runs without a display.

import hashlib
import os

from MiAZ.backend.log import MiAZLog

log = MiAZLog('MiAZ.Duplicates')

# Read in chunks: the largest document in a real repository here is 47 MB and
# nothing may load a whole file into memory.
CHUNK = 1024 * 1024


def _digest(path):
    """The sha256 of a file, or None when it cannot be read.

    A file the scan cannot open is skipped rather than raising: one bad file
    must not cost the whole result.
    """
    try:
        digest = hashlib.sha256()
        with open(path, 'rb') as handle:
            for chunk in iter(lambda: handle.read(CHUNK), b''):
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, ValueError) as error:
        log.debug(f"Cannot hash '{path}': {error}")
        return None


def _by_size(paths):
    """{size: [path]}, skipping anything that is not a readable file."""
    sizes = {}
    for path in paths:
        try:
            if not os.path.isfile(path):
                continue
            sizes.setdefault(os.path.getsize(path), []).append(path)
        except OSError as error:
            log.debug(f"Cannot stat '{path}': {error}")
    return sizes


def find_duplicates(paths):
    """{path: [other paths with identical content]}, exact matches only.

    Files are grouped by size first, and a size holding one file is never
    hashed: two files of different sizes cannot be identical, so the prefilter
    is exact and costs nothing. On a 1336 document repository that hashes 302
    files instead of 1336.

    Exact means byte for byte. The same letter scanned twice does not match.
    """
    by_hash = {}
    for group in _by_size(paths).values():
        if len(group) < 2:
            continue
        for path in group:
            digest = _digest(path)
            if digest is not None:
                by_hash.setdefault(digest, []).append(path)

    duplicates = {}
    for group in by_hash.values():
        if len(group) < 2:
            continue
        for path in group:
            duplicates[path] = [other for other in group if other != path]
    return duplicates
