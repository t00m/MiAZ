# pylint: disable=E1101

"""
# File: categories.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: JSON-backed list of user-defined note categories
"""

import json
import os
from typing import List


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
