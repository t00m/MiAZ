# File: doctor.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Every repository health check in one pass. No GTK imports.

"""What is wrong with a repository, gathered once and reported together.

The checks live here rather than in the plugin so they can run without a
display, and so the plugin is only the part that draws them. Reading the
repository is the caller's job: everything below takes data already gathered,
which is what makes it testable and what keeps one slow check from deciding
how the rest are written.
"""

from MiAZ.backend.util import date_is_valid
from MiAZ.backend.vocabhealth import (
    analyse, documents_using, fields, FIELD_POSITION)

# How much a finding matters. A problem stops documents being usable, a
# warning is drift worth cleaning, a note is informational.
PROBLEM = 'problem'
WARNING = 'warning'
NOTE = 'note'

# Ordered worst first, which is the order a report should be read in.
SEVERITY_ORDER = (PROBLEM, WARNING, NOTE)


class Finding:
    """One check's answer: what it looked at and what it found."""

    def __init__(self, check, severity, summary, items=None, hint='',
                 documents=None):
        self.check = check
        self.severity = severity
        self.summary = summary
        self.items = items or []
        self.hint = hint
        # The documents this finding is about, so the view can be narrowed to
        # them. Empty when a finding is about the vocabulary and no document
        # is involved, which is the case for a value nothing references.
        self.documents = sorted(documents or [])

    @property
    def count(self):
        return len(self.items)

    def __repr__(self):
        return f"<Finding {self.check} {self.severity} {self.count}>"


def check_names(filenames):
    """Documents whose name is not the seven-field convention."""
    bad = []
    for filename in sorted(filenames):
        parts = fields(filename)
        if len(parts) != 7 or not all(part.strip() for part in parts):
            bad.append(filename)
        elif not date_is_valid(parts[0]):
            bad.append(filename)
    return bad


def check_vocabulary(filenames, vocabularies):
    """The three vocabulary problems, flattened to (field, code, count)."""
    report = analyse(filenames, vocabularies)
    found = {'unknown': [], 'undescribed': [], 'unused': []}
    naming = {'unknown': 'unknown', 'unnamed': 'undescribed', 'unused': 'unused'}
    for field in sorted(report):
        for problem, target in naming.items():
            for code, _description, count in report[field][problem]:
                found[target].append((field, code, count))
    return found


def documents_for(filenames, entries):
    """Every document using any of these (field, code, count) entries."""
    found = set()
    for field, code, count in entries:
        if not count:
            continue
        position = FIELD_POSITION.get(field)
        if position is not None:
            found.update(documents_using(filenames, position, [code]))
    return found


def build_report(filenames, vocabularies, duplicates=None, unreadable=None,
                 empty=None):
    """Every finding, worst first.

    `duplicates` is the list of groups the duplicate scan returned, `empty` the
    documents of zero length and `unreadable` the ones that could not be read.
    A check with nothing to say is left out: a report should be what needs
    attention, not a list of things that are fine.
    """
    vocabulary = check_vocabulary(filenames, vocabularies)
    bad_names = check_names(filenames)
    duplicates = list(duplicates or [])
    unreadable = list(unreadable or [])
    empty = list(empty or [])

    in_groups = {member for group in duplicates for member in group}
    candidates = [
        Finding('unreadable', PROBLEM,
                'Documents that cannot be read', unreadable,
                'Check the permissions, or whether the file is still there.',
                documents=unreadable),
        Finding('names', PROBLEM,
                'Documents not named in seven fields', bad_names,
                'Rename them, or MiAZ cannot file them.',
                documents=bad_names),
        Finding('unknown-codes', PROBLEM,
                'Values used by documents and missing from the vocabulary',
                vocabulary['unknown'],
                'Add them to the repository, or those documents stay in Review.',
                documents=documents_for(filenames, vocabulary['unknown'])),
        Finding('empty', WARNING,
                'Documents of zero length', empty,
                'Nothing was copied. Import them again.',
                documents=empty),
        Finding('duplicates', WARNING,
                'Groups of documents with identical content', duplicates,
                'Keep one of each group and delete the rest.',
                documents=in_groups),
        Finding('undescribed-codes', WARNING,
                'Values described by nothing but themselves',
                vocabulary['undescribed'],
                'Name them and every list in MiAZ reads better.',
                documents=documents_for(filenames, vocabulary['undescribed'])),
        Finding('unused-codes', NOTE,
                'Values in the vocabulary that no document uses',
                vocabulary['unused'],
                'Removing them shortens every dropdown.'),
    ]
    found = [finding for finding in candidates if finding.count]
    return sorted(found, key=lambda f: (SEVERITY_ORDER.index(f.severity), f.check))


def summarise(report):
    """How many findings of each severity, for a one line verdict."""
    counted = {PROBLEM: 0, WARNING: 0, NOTE: 0}
    for finding in report:
        counted[finding.severity] += 1
    return counted


def is_healthy(report):
    return not report
