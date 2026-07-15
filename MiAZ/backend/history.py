#!/usr/bin/python3

"""
# File: history.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Per-repository, append-only journal of document changes.
"""

import os
import json
import datetime

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog

# Hidden directory inside each repository that holds the change journal.
# It is dot-prefixed so the document scanner (get_files / get_files_recursively)
# ignores it and it never shows up as a document.
HISTORY_DIRNAME = '.history'


class MiAZHistory(GObject.GObject):
    """Record every document change MiAZ makes in a repository.

    The journal is stored inside the repository under HISTORY_DIRNAME as
    append-only JSON Lines, one file per month (YYYYMM.jsonl). Paths are kept
    relative to the repository root so the journal stays valid when the
    repository is moved, copied or synced.
    """
    __gtype_name__ = 'MiAZHistory'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZHistory')
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        # Maps an imported target path to its original source, set by
        # filename-imported just before filename-added fires for the same file.
        self._pending_imports = {}
        self.util.connect('filename-imported', self._on_imported)
        self.util.connect('filename-added', self._on_added)
        self.util.connect('filename-renamed', self._on_renamed)
        self.util.connect('filename-deleted', self._on_deleted)

    # Signal handlers
    def _on_imported(self, util, origin, target):
        # Importing copies a file under a normalized name. Remember its
        # provenance so the added record can keep where it came from.
        self._pending_imports[os.path.abspath(target)] = origin

    def _on_added(self, util, target):
        origin = self._pending_imports.pop(os.path.abspath(target), None)
        self._record('added', path=target, provenance=origin)

    def _on_renamed(self, util, source, target):
        self._record('renamed', source=source, target=target)

    def _on_deleted(self, util, filepaths):
        # filename-deleted carries a set of absolute paths.
        for filepath in filepaths:
            self._record('deleted', path=filepath)

    # Core
    def _record(self, event, path=None, source=None, target=None, provenance=None):
        root = self.repository.docs
        if not root:
            self.log.debug("No active repository; change not journaled")
            return
        record = {
            'ts': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
            'event': event,
            'origin': 'app',
        }
        if path is not None:
            record.update(self._path_field('path', path, root))
        if source is not None:
            record.update(self._path_field('source', source, root))
        if target is not None:
            record.update(self._path_field('target', target, root))
        # Provenance is a structured object (where an imported file came from):
        # {'type': 'file'|'zip'|'scan'|..., ...}. Stored verbatim under 'source'.
        if provenance is not None:
            record['source'] = provenance
        self._append(root, record)

    def _path_field(self, key, path, root):
        # Store the path relative to the repository root. If it falls outside
        # the repository (should not happen for document changes), keep it
        # absolute and flag it so readers can tell.
        abspath = os.path.abspath(path)
        rel = os.path.relpath(abspath, os.path.abspath(root))
        if rel.startswith('..') or os.path.isabs(rel):
            return {key: abspath, f'{key}_absolute': True}
        return {key: rel}

    def _append(self, root, record):
        try:
            history_dir = os.path.join(root, HISTORY_DIRNAME)
            os.makedirs(history_dir, exist_ok=True)
            month = datetime.datetime.now().strftime('%Y%m')
            fpath = os.path.join(history_dir, f'{month}.jsonl')
            line = json.dumps(record, ensure_ascii=False)
            # Write the whole record in one call and flush it to disk. A crash
            # can at worst leave a torn final line, which iter_records skips.
            with open(fpath, 'a', encoding='utf-8') as handler:
                handler.write(line + '\n')
                handler.flush()
                os.fsync(handler.fileno())
        except Exception as error:
            self.log.error(f"Could not write change journal: {error}")

    # Reader API
    def iter_records(self, root=None):
        """Yield parsed change records for a repository in chronological order
        (oldest month first). Defaults to the active repository."""
        root = root or self.repository.docs
        if not root:
            return
        history_dir = os.path.join(root, HISTORY_DIRNAME)
        if not os.path.isdir(history_dir):
            return
        for name in sorted(os.listdir(history_dir)):
            if not name.endswith('.jsonl'):
                continue
            fpath = os.path.join(history_dir, name)
            try:
                with open(fpath, encoding='utf-8') as handler:
                    for line in handler:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            self.log.warning(f"Skipping malformed journal line in {fpath}")
            except OSError as error:
                self.log.error(f"Could not read {fpath}: {error}")
