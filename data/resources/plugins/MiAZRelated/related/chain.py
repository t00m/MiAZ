# File: chain.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Which documents belong to the same case. Pure Python.

"""One document is rarely the whole story.

A cancellation has a request and a receipt; an invoice has a payment. They
share a concept, and often a sender. This works out which documents belong
together, with no GTK and no services, so it can be tested headless.
"""

CONCEPT = 5
SENTBY = 3
SENTTO = 6
DATE = 0


def fields(filename):
    """The seven filename fields, following MiAZUtil.get_fields."""
    name = filename
    dot = name.rfind('.')
    if dot > 0:
        name = name[:dot]
    parts = name.split('-')
    if len(parts) > 7:
        parts[6] = '-'.join(parts[6:])
        parts = parts[:7]
    return parts


def concept_key(concept):
    """A concept compared the way a person would read it.

    Case and the underscores that stand in for spaces are not what makes two
    concepts different.
    """
    return concept.replace('_', ' ').strip().upper()


def related(filenames, target):
    """Documents belonging to the same case as target, target excluded.

    Two groups, because they answer different questions. `same_party` is the
    same concept from or to the same party, which is the case as one side
    kept it. `other_party` is the same concept involving somebody else, which
    is how a request and its answer find each other.
    """
    parts = fields(target)
    if len(parts) != 7:
        return {'same_party': [], 'other_party': []}
    key = concept_key(parts[CONCEPT])
    if not key:
        return {'same_party': [], 'other_party': []}
    parties = {parts[SENTBY], parts[SENTTO]}

    same, other = [], []
    for filename in filenames:
        if filename == target:
            continue
        candidate = fields(filename)
        if len(candidate) != 7 or concept_key(candidate[CONCEPT]) != key:
            continue
        if {candidate[SENTBY], candidate[SENTTO]} & parties:
            same.append(filename)
        else:
            other.append(filename)

    def by_date(name):
        return (fields(name)[DATE], name)

    return {'same_party': sorted(same, key=by_date),
            'other_party': sorted(other, key=by_date)}


def chains(filenames, minimum=2):
    """Every concept held by at least `minimum` documents, largest first.

    The repository read as cases rather than as documents.
    """
    grouped = {}
    for filename in filenames:
        parts = fields(filename)
        if len(parts) != 7:
            continue
        key = concept_key(parts[CONCEPT])
        if key:
            grouped.setdefault(key, []).append(filename)
    found = [(key, sorted(names, key=lambda n: (fields(n)[DATE], n)))
             for key, names in grouped.items() if len(names) >= minimum]
    return sorted(found, key=lambda entry: (-len(entry[1]), entry[0]))
