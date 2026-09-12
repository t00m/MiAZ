# File: parties.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The distinct senders and recipients of a set of documents

import unicodedata
from dataclasses import dataclass


@dataclass
class Party:
    """One person or organisation, and how the documents name it."""
    key: str
    description: str = ''
    sent: int = 0
    received: int = 0

    @property
    def total(self):
        return self.sent + self.received


def sort_key(text):
    """Alphabetical the way a person reads it.

    Case folded, so Bank X and BANKX sort together rather than every capital
    coming before every small letter. Accents folded too: Ecole and École are
    the same word and belong next to each other, not one of them after Z.
    """
    decomposed = unicodedata.normalize('NFKD', text or '')
    unaccented = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return unaccented.casefold()


def parties(items, name_of=None):
    """One entry per distinct party, in alphabetical order.

    A party that both sends and receives is one entry, not two: the cards are
    about people, and a person is not two people for having answered.

    `name_of` says what a card will call the party, so the order matches what
    is read on screen. A party with a contact record is shown under the name
    on the record, which is not always the description the documents use, and
    sorting on the description would then put the cards in an order the names
    on them do not explain. Without it the description is used.
    """
    found = {}
    for item in items:
        for key, description, sent in (
                (item.sentby_id, item.sentby_dsc, True),
                (item.sentto_id, item.sentto_dsc, False)):
            if not key:
                continue
            party = found.get(key)
            if party is None:
                party = Party(key=key, description=description or key)
                found[key] = party
            if sent:
                party.sent += 1
            else:
                party.received += 1
    if name_of is None:
        def name_of(party):
            return party.description
    # The key breaks a tie between two parties shown under the same name, so
    # the order is the same on every rebuild rather than however the dict fell.
    return sorted(found.values(),
                  key=lambda one: (sort_key(name_of(one)), one.key))


def documents_for(key, items):
    """The documents this party is named in, either way round."""
    names = {item.id for item in items
             if key in (item.sentby_id, item.sentto_id)}
    return sorted(names)
