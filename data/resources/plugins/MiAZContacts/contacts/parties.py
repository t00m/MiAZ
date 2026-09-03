# File: parties.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The distinct senders and recipients of a set of documents

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


def parties(items):
    """One entry per distinct party, most documents first.

    A party that both sends and receives is one entry, not two: the cards are
    about people, and a person is not two people for having answered.
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
    return sorted(found.values(), key=lambda one: (-one.total, one.description))


def documents_for(key, items):
    """The documents this party is named in, either way round."""
    names = {item.id for item in items
             if key in (item.sentby_id, item.sentto_id)}
    return sorted(names)
