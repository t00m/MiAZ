"""
# File: notes.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: notes attached to documents: storage, categories, backup

Notes were MiAZNotes, a plugin, until 0.3. A note is part of what MiAZ knows
about a document, and reading or writing one has nothing to do with a window:
`miaz ocr` files the text it extracts as a note on a machine with no display.
So the store moved here and the views stayed in the frontend.

This is a move. The classes are the plugin's own, and the on-disk location is
unchanged, so every repository written by an older MiAZ is read by this one
with nothing to migrate.

Nothing here imports Gtk, Adw or Gdk. tests/test_notes.py fails if that
changes.
"""

import getpass
import glob
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.util import check_zip_members

_module_log = MiAZLog('MiAZ.Notes')


def notes_dir(repo_docs: str) -> str:
    """Where a repository keeps its notes."""
    return os.path.join(repo_docs, '.conf', 'MiAZNotes', 'data')


def legacy_notes_dir(repo_docs: str) -> str:
    """Where notes were kept while they were a plugin."""
    return os.path.join(repo_docs, '.conf', 'plugins', 'MiAZNotes', 'data')


def _unique_name(path: str) -> str:
    """`path`, or the next free name beside it.

    Same shape the store uses for two notes filed in one second: a counter
    before the extension, which document_id_of, list_for_document and
    rename_for_document all ignore.
    """
    if not os.path.exists(path):
        return path
    stem, extension = os.path.splitext(path)
    counter = 2
    while os.path.exists(f'{stem}-{counter}{extension}'):
        counter += 1
    return f'{stem}-{counter}{extension}'


def migrate_notes(repo_docs: str, log=None) -> int:
    """Move a repository's notes out of the plugins directory.

    Notes were written to .conf/plugins/MiAZNotes while they were a plugin.
    They are core now, and this runs whenever a repository is opened, by the
    window or by a command, so a repository migrates the first time either one
    touches it. Returns how many files were moved, which is 0 for a repository
    that has nothing to move: the common case after the first open.

    Nothing is ever overwritten. Both directories can hold a note of the same
    name, because a 0.2 MiAZ and a 0.3 one can be pointed at one repository in
    turn, and losing either note is not acceptable. A file whose name is taken
    arrives beside the one already there.
    """
    log = log or _module_log
    legacy = os.path.join(repo_docs, '.conf', 'plugins', 'MiAZNotes')
    target = os.path.join(repo_docs, '.conf', 'MiAZNotes')
    if not os.path.isdir(legacy):
        return 0

    moved = 0
    for root, _dirs, files in os.walk(legacy):
        relative = os.path.relpath(root, legacy)
        destination = target if relative == '.' else os.path.join(target, relative)
        os.makedirs(destination, exist_ok=True)
        for filename in files:
            source_file = os.path.join(root, filename)
            target_file = _unique_name(os.path.join(destination, filename))
            try:
                shutil.move(source_file, target_file)
                moved += 1
                if os.path.basename(target_file) != filename:
                    log.warning(f"Note '{filename}' already existed at the new "
                                f"location; kept both, the moved one as "
                                f"'{os.path.basename(target_file)}'")
            except OSError as error:
                log.error(f"Could not move '{source_file}': {error}")

    # Only an empty tree is removed. Anything left behind is something that
    # could not be moved, and it stays where it is rather than being deleted.
    # os.listdir rather than walk's `dirs` and `files`: those are read before
    # the children are removed, so the parent still looks occupied and the
    # directory this exists to clear away is the one that survives.
    try:
        for root, _dirs, _files in os.walk(legacy, topdown=False):
            if not os.listdir(root):
                os.rmdir(root)
    except OSError as error:
        log.debug(f"Old notes directory not removed: {error}")

    if moved:
        log.info(f"Notes migrated out of the plugins directory: {moved} "
                 f"file(s) now in {target}")
    return moved


HEADER_KEYS = ('Author', 'Category', 'Date', 'Priority', 'Status')
DEFAULT_CATEGORY = 'General'
DEFAULT_PRIORITY = 'Medium'
DEFAULT_STATUS = 'Draft'
NOTE_EXTENSION = '.md'
FRONTMATTER_DELIMITER = '---'


class NotesStore:
    """File-based store for plain Markdown notes with a YAML-style header."""

    def __init__(self, data_dir: str, log):
        self.data_dir = data_dir
        self.log = log
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir, exist_ok=True)
            except Exception as error:
                self.log.error(f"Could not create notes data dir '{self.data_dir}': {error}")

    # CRUD
    def create(self, document_id: str, header: Dict[str, str], body: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        note_path = self._free_path(document_id, timestamp)
        merged = self.default_header()
        merged.update({k: v for k, v in header.items() if v is not None})
        merged['Date'] = self._now_local()
        self._write(note_path, merged, body)
        self.log.debug(f"Note created: {note_path}")
        return note_path

    def _free_path(self, document_id: str, timestamp: str) -> str:
        """A note path nothing is using yet.

        The name is stamped to the second, so two notes filed against one
        document inside the same second used to land on the same path and the
        second silently overwrote the first. A person clicking twice rarely
        managed it; `miaz ocr A.pdf A.pdf` manages it every time.

        The suffix goes after the timestamp, where document_id_of (which
        splits on the last '_'), list_for_document (which globs '<id>_*') and
        rename_for_document (which keeps everything after the id) all ignore
        it.
        """
        base = os.path.join(self.data_dir, f"{document_id}_{timestamp}")
        candidate = f"{base}{NOTE_EXTENSION}"
        counter = 2
        while os.path.exists(candidate):
            candidate = f"{base}-{counter}{NOTE_EXTENSION}"
            counter += 1
        return candidate

    def read(self, note_path: str) -> Tuple[Dict[str, str], str]:
        try:
            with open(note_path, 'r', encoding='utf-8') as fin:
                text = fin.read()
        except Exception as error:
            self.log.warning(f"Could not read note '{note_path}': {error}")
            return self.default_header(), ''
        return self.parse_header(text)

    def update(self, note_path: str, header: Dict[str, str], body: str) -> None:
        merged = self.default_header()
        merged.update({k: v for k, v in header.items() if v is not None})
        merged['Date'] = self._now_local()
        self._write(note_path, merged, body)
        self.log.debug(f"Note updated: {note_path}")

    def delete(self, note_path: str) -> None:
        try:
            os.unlink(note_path)
            self.log.debug(f"Note deleted: {note_path}")
        except OSError as error:
            self.log.error(f"Could not delete note '{note_path}': {error}")

    # Queries
    def list_for_document(self, document_id: str) -> List[str]:
        pattern = os.path.join(self.data_dir, f"{document_id}_*{NOTE_EXTENSION}")
        return sorted(glob.glob(pattern))

    def count_for_document(self, document_id: str) -> int:
        return len(self.list_for_document(document_id))

    def has_notes(self, document_id: str) -> bool:
        if not document_id:
            return False
        return self.count_for_document(document_id) > 0

    def list_all(self) -> List[str]:
        pattern = os.path.join(self.data_dir, f"*{NOTE_EXTENSION}")
        return sorted(glob.glob(pattern))

    def document_id_of(self, note_path: str) -> str:
        name = os.path.basename(note_path)
        if name.endswith(NOTE_EXTENSION):
            name = name[: -len(NOTE_EXTENSION)]
        sep = name.rfind('_')
        if sep < 0:
            return name
        return name[:sep]

    def rename_for_document(self, old_id: str, new_id: str) -> List[Tuple[str, str]]:
        moves = []
        for note_path in self.list_for_document(old_id):
            basename = os.path.basename(note_path)
            new_basename = new_id + basename[len(old_id):]
            new_path = os.path.join(self.data_dir, new_basename)
            try:
                os.rename(note_path, new_path)
                moves.append((note_path, new_path))
                self.log.debug(f"Note renamed: {note_path} -> {new_path}")
            except OSError as error:
                self.log.error(f"Could not rename note '{note_path}': {error}")
        return moves

    # Header helpers
    def parse_header(self, text: str) -> Tuple[Dict[str, str], str]:
        header = self.default_header()
        lines = text.splitlines()

        idx = 0
        while idx < len(lines) and lines[idx].strip() == '':
            idx += 1

        if idx >= len(lines) or lines[idx].strip() != FRONTMATTER_DELIMITER:
            self.log.warning("Note has no YAML frontmatter; loading as body-only")
            return header, text

        idx += 1
        while idx < len(lines):
            line = lines[idx]
            if line.strip() == FRONTMATTER_DELIMITER:
                idx += 1
                break
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                if key in HEADER_KEYS:
                    header[key] = value
            idx += 1
        else:
            self.log.warning("Note frontmatter is not closed; loading as body-only")
            return self.default_header(), text

        if idx < len(lines) and lines[idx].strip() == '':
            idx += 1

        body = '\n'.join(lines[idx:])
        return header, body

    def serialize_header(self, header: Dict[str, str]) -> str:
        out = [FRONTMATTER_DELIMITER]
        for key in HEADER_KEYS:
            value = header.get(key, '')
            if value is None:
                value = ''
            out.append(f"{key}: {value}")
        out.append(FRONTMATTER_DELIMITER)
        out.append('')
        return '\n'.join(out)

    def default_header(self) -> Dict[str, str]:
        return {
            'Author': self._username(),
            'Category': DEFAULT_CATEGORY,
            'Date': self._now_local(),
            'Priority': DEFAULT_PRIORITY,
            'Status': DEFAULT_STATUS,
        }

    @staticmethod
    def summary_of(body: str) -> str:
        for line in body.splitlines():
            stripped = line.strip().lstrip('#').strip()
            if stripped:
                if len(stripped) > 80:
                    return stripped[:77] + '...'
                return stripped
        return ''

    # Internals
    def _write(self, note_path: str, header: Dict[str, str], body: str) -> None:
        content = self.serialize_header(header) + '\n' + (body or '')
        try:
            with open(note_path, 'w', encoding='utf-8', newline='\n') as fout:
                fout.write(content)
        except Exception as error:
            self.log.error(f"Could not write note '{note_path}': {error}")

    @staticmethod
    def _now_local() -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def _username() -> str:
        try:
            return getpass.getuser()
        except Exception:
            return ''


class CategoryStore:
    """Persists user-added note categories alongside the note files."""

    FILENAME = 'categories.json'

    def __init__(self, data_dir: str, log):
        self.data_dir = data_dir
        self.log = log
        self._path = os.path.join(self.data_dir, self.FILENAME)

    def list(self) -> List[str]:
        if not os.path.isfile(self._path):
            return []
        try:
            with open(self._path, 'r', encoding='utf-8') as fin:
                data = json.load(fin)
        except Exception as error:
            self.log.warning(f"Could not read categories '{self._path}': {error}")
            return []
        if not isinstance(data, list):
            return []
        return sorted({str(x).strip() for x in data
                       if isinstance(x, str) and x.strip()})

    def has(self, name: str) -> bool:
        return (name or '').strip() in set(self.list())

    def add(self, name: str) -> bool:
        name = (name or '').strip()
        if not name:
            return False
        items = set(self.list())
        if name in items:
            return False
        items.add(name)
        return self._save(items)

    def remove(self, name: str) -> bool:
        name = (name or '').strip()
        if not name:
            return False
        items = set(self.list())
        if name not in items:
            return False
        items.discard(name)
        return self._save(items)

    def _save(self, items) -> bool:
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self._path, 'w', encoding='utf-8') as fout:
                json.dump(sorted(items), fout, ensure_ascii=False, indent=2)
            return True
        except Exception as error:
            self.log.error(f"Could not save categories '{self._path}': {error}")
            return False


def _report(progress, message: str, fraction: float = None):
    """Send one progress update, when the caller asked for them.

    Called from wherever the backup runs, a worker thread included: this module
    knows nothing about the UI, so marshalling is the caller's job.
    """
    if progress is not None:
        progress(message, fraction)


class NotesBackup:
    """Zip/unzip the plugin's notes data directory."""

    def __init__(self, data_dir: str, log):
        self.data_dir = data_dir
        self.log = log

    @staticmethod
    def default_backup_name() -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"MiAZNotes-backup-{timestamp}.zip"

    def backup(self, dest_zip: str, progress=None) -> int:
        """Zip the data directory. progress(message, fraction) is optional and
        is called once per note, so the caller can drive a progress bar."""
        if not os.path.exists(self.data_dir):
            self.log.warning(f"Notes data dir does not exist: {self.data_dir}")
            return 0

        # Listed before writing anything: the total is what makes the caller's
        # progress bar a bar rather than a spinner.
        entries = []
        for root, _dirs, files in os.walk(self.data_dir):
            for filename in files:
                absolute = os.path.join(root, filename)
                entries.append((absolute, os.path.relpath(absolute, self.data_dir)))

        count = 0
        try:
            with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zfile:
                for absolute, relative in entries:
                    zfile.write(absolute, relative)
                    count += 1
                    _report(progress, relative, count / len(entries))
        except Exception as error:
            self.log.error(f"Backup failed ({dest_zip}): {error}")
            return 0
        self.log.info(f"Backed up {count} notes to {dest_zip}")
        return count

    def restore(self, source_zip: str, merge: bool = True, progress=None) -> int:
        if not os.path.exists(source_zip):
            self.log.error(f"Backup file not found: {source_zip}")
            return 0

        if not merge and os.path.exists(self.data_dir):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_dir = f"{self.data_dir}.bak-{timestamp}"
            try:
                os.rename(self.data_dir, backup_dir)
                self.log.info(f"Existing notes preserved at {backup_dir}")
            except OSError as error:
                self.log.error(f"Could not rename '{self.data_dir}': {error}")
                return 0

        os.makedirs(self.data_dir, exist_ok=True)

        count = 0
        try:
            with zipfile.ZipFile(source_zip, 'r') as zfile:
                # A restore archive is a file the user picked, so it is as
                # untrusted as an imported plugin zip. Same check, and it runs
                # over the whole listing before anything is written.
                check_zip_members(zfile.namelist(), self.data_dir)
                members = [info for info in zfile.infolist() if not info.is_dir()]
                for info in members:
                    zfile.extract(info, self.data_dir)
                    count += 1
                    _report(progress, info.filename, count / len(members))
        except Exception as error:
            self.log.error(f"Restore failed ({source_zip}): {error}")
            return 0
        self.log.info(f"Restored {count} notes from {source_zip}")
        return count

    def reset_data_dir(self) -> None:
        if os.path.exists(self.data_dir):
            try:
                shutil.rmtree(self.data_dir)
            except OSError as error:
                self.log.error(f"Could not remove '{self.data_dir}': {error}")
        os.makedirs(self.data_dir, exist_ok=True)
