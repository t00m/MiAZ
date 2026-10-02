# File: ledger.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: What each document is worth, kept beside the repository

import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal

from oikos.money import KINDS, EXPENSE, parse_amount, is_currency_code

# Bumped when the file changes shape, so a later version can migrate it.
FORMAT = 1

log = logging.getLogger('Plugin.MiAZOikos.Ledger')


@dataclass(frozen=True)
class Entry:
    """One document as money: which way it went, how much and in what."""
    kind: str
    amount: Decimal
    currency: str

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f'unknown kind: {self.kind!r}')
        if not is_currency_code(self.currency):
            raise ValueError(f'not a currency code: {self.currency!r}')
        # Through the parser, so an Entry holds the same values whether it
        # was typed or read back from disk.
        object.__setattr__(self, 'amount', parse_amount(self.amount))

    @property
    def signed(self) -> Decimal:
        """The amount with the sign the kind gives it."""
        return -self.amount if self.kind == EXPENSE else self.amount

    def to_json(self) -> dict:
        # A string, never a float: 0.1 + 0.2 must stay 0.3 on the way back.
        return {'kind': self.kind, 'amount': str(self.amount),
                'currency': self.currency}

    @classmethod
    def from_json(cls, data) -> 'Entry':
        if not isinstance(data, dict):
            raise ValueError(f'not an entry: {data!r}')
        return cls(kind=data.get('kind'), amount=str(data.get('amount', '')),
                   currency=data.get('currency'))


def _read(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _write(path, data):
    # Imported here, not at the top: the pure tests of this module then need
    # nothing from MiAZ at all, and the plugin always passes util.json_save.
    from MiAZ.backend.util import atomic_json_save
    atomic_json_save(path, data)


class Ledger:
    """Document name to Entry, stored as one JSON file.

    Every change is written at once, so a crash loses nothing that the user
    saw applied. The file is read once; this object is the only writer.
    """

    def __init__(self, path, load=None, save=None):
        self.path = path
        self._load = load or _read
        self._save = save or _write
        # Bumped on every change, so a view can tell whether its totals are
        # still current without comparing the whole ledger.
        self.revision = 0
        self._entries = self._read_entries()

    def _read_entries(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        try:
            data = self._load(self.path)
        except (OSError, ValueError) as error:
            log.error(f"Could not read {self.path}: {error}")
            return {}
        documents = data.get('documents', {}) if isinstance(data, dict) else {}
        entries = {}
        for doc, raw in documents.items():
            try:
                entries[doc] = Entry.from_json(raw)
            except ValueError as error:
                # One bad line must not cost the user every other document.
                log.warning(f"Ignoring the entry for '{doc}': {error}")
        return entries

    def _write(self):
        documents = {doc: entry.to_json()
                     for doc, entry in sorted(self._entries.items())}
        self._save(self.path, {'format': FORMAT, 'documents': documents})
        self.revision += 1

    def __len__(self):
        return len(self._entries)

    def __contains__(self, doc):
        return doc in self._entries

    def get(self, doc):
        """The Entry for a document, or None when it has none."""
        return self._entries.get(doc)

    def documents(self) -> dict:
        """A copy of every entry, keyed by document name."""
        return dict(self._entries)

    def set_many(self, entries: dict) -> int:
        """Record {doc: Entry}. Returns how many documents changed."""
        changed = 0
        for doc, entry in entries.items():
            if not isinstance(entry, Entry):
                raise TypeError(f'not an Entry: {entry!r}')
            if self._entries.get(doc) != entry:
                self._entries[doc] = entry
                changed += 1
        if changed:
            self._write()
        return changed

    def set(self, doc, entry) -> bool:
        return self.set_many({doc: entry}) == 1

    def clear(self, docs) -> int:
        """Forget these documents. Returns how many had an entry."""
        removed = 0
        for doc in docs:
            if self._entries.pop(doc, None) is not None:
                removed += 1
        if removed:
            self._write()
        return removed

    def rename(self, source, target) -> bool:
        """Carry an entry to a document's new name."""
        entry = self._entries.pop(source, None)
        if entry is None:
            return False
        self._entries[target] = entry
        self._write()
        return True
