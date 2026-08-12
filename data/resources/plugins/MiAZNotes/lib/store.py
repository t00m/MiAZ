# pylint: disable=E1101

"""
# File: store.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Notes storage backend (file I/O, frontmatter, naming)
"""

import os
import glob
import getpass
from datetime import datetime, timezone
from typing import Tuple, List, Dict


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
        filename = f"{document_id}_{timestamp}{NOTE_EXTENSION}"
        note_path = os.path.join(self.data_dir, filename)
        merged = self.default_header()
        merged.update({k: v for k, v in header.items() if v is not None})
        merged['Date'] = self._now_local()
        self._write(note_path, merged, body)
        self.log.debug(f"Note created: {note_path}")
        return note_path

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
