# File: store.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: One vCard file per person key, and the import and export of them

import os
import re
import glob
import unicodedata
from dataclasses import dataclass, field

from contacts import vcard
from contacts.model import Contact

EXTENSION = '.vcf'

# What a key is made of once a name has been folded down to it.
KEY_CHARS = re.compile(r'[^A-Z0-9]')

# The key a card with no usable name gets, before any collision suffix.
FALLBACK_KEY = 'CONTACT'


@dataclass
class ImportResult:
    """What one import did, so the user can be told in one line."""
    added: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    failed: list = field(default_factory=list)

    @property
    def total(self):
        return len(self.added) + len(self.updated)


def mint_key(name, taken, valid_key=None):
    """A key for a card that arrived without one, unique among those taken.

    With valid_key given, the result is shaped like util.valid_key would shape
    it, so a minted key and one typed by hand never diverge for the same name.
    """
    folded = unicodedata.normalize('NFKD', str(name or ''))
    stripped = ''.join(char for char in folded if not unicodedata.combining(char))
    if valid_key is not None:
        base = valid_key(stripped).upper() or FALLBACK_KEY
    else:
        base = KEY_CHARS.sub('', stripped.upper()) or FALLBACK_KEY
    base = base[:32]
    if base not in taken:
        return base
    number = 2
    while f'{base}{number}' in taken:
        number += 1
    return f'{base}{number}'


class ContactStore:
    """Every contact of one repository, one file per person key."""

    def __init__(self, data_dir, log=None):
        self.data_dir = data_dir
        self.log = log
        self._contacts = None
        self._broken = {}
        os.makedirs(self.data_dir, exist_ok=True)

    def path_for(self, key):
        # An imported key is untrusted, so only a bare filename may pass.
        if not key or key.startswith('.') or os.path.basename(key) != key:
            raise ValueError(f"'{key}' is not a usable contact key")
        return os.path.join(self.data_dir, f'{key}{EXTENSION}')

    def load(self, force=False):
        """Every contact on disk, read once and remembered."""
        if self._contacts is not None and not force:
            return self._contacts
        contacts = {}
        self._broken = {}
        for path in sorted(glob.glob(os.path.join(self.data_dir, f'*{EXTENSION}'))):
            key = os.path.basename(path)[:-len(EXTENSION)]
            try:
                with open(path, encoding='utf-8') as handle:
                    cards = vcard.parse(handle.read())
                if not cards:
                    raise ValueError('no card in the file')
                contacts[key] = Contact.from_card(cards[0], key=key)
            except (OSError, ValueError, UnicodeError) as error:
                self._broken[key] = str(error)
                if self.log is not None:
                    self.log.warning(f"Contact '{key}' could not be read: {error}")
        self._contacts = contacts
        return contacts

    def keys(self):
        return sorted(self.load())

    def get(self, key):
        return self.load().get(key)

    def broken(self):
        self.load()
        return dict(self._broken)

    def save(self, contact):
        """Write one contact, atomically, and return where it went."""
        path = self.path_for(contact.key)
        temporary = f'{path}.tmp'
        text = vcard.serialize([contact.to_card()])
        with open(temporary, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
        os.replace(temporary, path)
        self.load()[contact.key] = contact
        return path

    def delete(self, key):
        """Remove one contact. The person stays in the vocabulary."""
        path = self.path_for(key)
        if not os.path.exists(path):
            return False
        os.unlink(path)
        self.load().pop(key, None)
        return True

    def import_file(self, path, known_names=None, valid_key=None):
        """Read a file of cards into the store, matching each to a key."""
        result = ImportResult()
        names = {name.lower(): key for name, key in (known_names or {}).items()}
        try:
            with open(path, encoding='utf-8', errors='replace') as handle:
                cards = vcard.parse(handle.read())
        except OSError as error:
            if self.log is not None:
                self.log.error(f"Could not read '{path}': {error}")
            result.failed.append(os.path.basename(path))
            return result
        for card in cards:
            try:
                contact = Contact.from_card(card)
                key = contact.key
                if not key:
                    name = (card.get('FN').text() if card.get('FN') else '')
                    key = names.get(name.lower(), '')
                if not key:
                    taken = set(self.load()) | set(names.values())
                    name = (card.get('FN').text() if card.get('FN') else '')
                    key = mint_key(name, taken, valid_key=valid_key)
                existed = key in self.load()
                contact.key = key
                self.save(contact)
                (result.updated if existed else result.added).append(key)
            except (ValueError, OSError, UnicodeError) as error:
                if self.log is not None:
                    self.log.warning(f"A card could not be imported: {error}")
                result.failed.append(str(error))
        return result

    def export_file(self, path, keys=None):
        """Write contacts as one file of cards. Returns how many were written."""
        contacts = self.load()
        chosen = sorted(keys) if keys is not None else sorted(contacts)
        cards = [contacts[key].to_card() for key in chosen if key in contacts]
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(vcard.serialize(cards))
        return len(cards)
