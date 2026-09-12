# File: conversation.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The documents read as exchanges between parties. Pure Python.

"""A document is a letter: something one party sent another about a concept.

Read that way, a repository is a set of conversations, one per concept,
each a run of documents going back and forth. This works out those
conversations and which side of the exchange each document sits on, with no
GTK in it, so it can be tested headless.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from MiAZ.backend.util import UNKNOWN_DATE


def concept_key(concept):
    """A concept compared the way a person reads it.

    Case and the underscores that stand in for spaces are not what makes two
    concepts different.
    """
    return concept.replace('_', ' ').strip().upper()


@dataclass
class Message:
    """One document in a conversation; `payload` is whatever the caller keeps."""
    date: str
    sentby: str
    sentto: str
    concept: str = ''
    payload: object = None


@dataclass
class Conversation:
    key: str
    title: str
    messages: List[Message] = field(default_factory=list)

    @property
    def first_date(self):
        return self.messages[0].date if self.messages else ''

    @property
    def last_date(self):
        return self.messages[-1].date if self.messages else ''

    @property
    def parties(self):
        """Everyone in the exchange, in order of appearance."""
        seen = []
        for message in self.messages:
            for party in (message.sentby, message.sentto):
                if party not in seen:
                    seen.append(party)
        return seen


def owner_of(messages: Sequence[Message]) -> Optional[str]:
    """The party the collection belongs to: the one on the most documents.

    A personal archive has its keeper on nearly every document, as sender or
    as recipient, so the most frequent party is who "me" is. Nobody has to
    configure it. Ties go to the first name alphabetically, so the answer is
    stable between runs.
    """
    counts = Counter()
    for message in messages:
        counts[message.sentby] += 1
        counts[message.sentto] += 1
    if not counts:
        return None
    most = max(counts.values())
    return sorted(party for party, count in counts.items() if count == most)[0]


def home_party(conversation: 'Conversation', owner: Optional[str]) -> Optional[str]:
    """Whose side of this exchange is "mine".

    The owner, when they are in it. When they are not (a family member's
    letters kept in the same archive), the party who received most of it
    stands in: letters are kept by the one they were sent to.
    """
    parties = conversation.parties
    if owner in parties:
        return owner
    received = Counter(message.sentto for message in conversation.messages)
    if not received:
        return None
    most = max(received.values())
    return sorted(party for party, count in received.items() if count == most)[0]


def is_outgoing(message: Message, home: Optional[str]) -> bool:
    """Whether the home party sent it. Outgoing goes right, the way a chat reads."""
    return home is not None and message.sentby == home


def conversations(messages: Sequence[Message], titles=None) -> List[Conversation]:
    """Group messages by concept, most recent conversation first.

    `titles` maps a concept key to what to call the conversation; without it
    the key itself is the title. Messages inside a conversation run oldest to
    newest, so it reads top to bottom. Conversations are ordered by their
    latest message, newest first, the way a chat list is: what moved last is
    what the reader most likely wants.
    """
    titles = titles or {}
    grouped = {}
    for message in messages:
        grouped.setdefault(concept_key(message.concept), []).append(message)
    result = []
    for key, items in grouped.items():
        items.sort(key=lambda m: (m.date, m.sentby, m.sentto))
        result.append(Conversation(key=key, title=titles.get(key, key), messages=items))
    # A document with no date is filed as 9999-12-31, which would put every
    # undated conversation at the top of the list. They go to the bottom.
    def recency(conversation):
        last = conversation.last_date
        return ('' if last == UNKNOWN_DATE else last, conversation.title)

    result.sort(key=recency, reverse=True)
    return result


def exchanges(items: Sequence[Conversation]) -> List[Conversation]:
    """Only the conversations with more than one document.

    Most concepts are held by a single document, so the list is mostly
    entries with nothing to read as an exchange. This is the list without
    them.
    """
    return [conversation for conversation in items if len(conversation.messages) > 1]
