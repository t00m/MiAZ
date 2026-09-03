"""
# File: layout.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Where an exported document lands: pattern, directories and name

Pure Python: no GTK, no repository, no application. The plugin gathers the
fields of each document and asks this module where the copy goes, which is
what makes both answerable in a test.
"""

import os
import re
from datetime import datetime
from gettext import gettext as _

# The letters accepted in the pattern, and what each one means.
PATTERNS = {
    'Y': _('Year'),
    'm': _('Month'),
    'd': _('Day'),
    'C': _('Country'),
    'G': _('Group'),
    'P': _('Purpose'),
    'B': _('Sent by'),
    'T': _('Sent to'),
}

# Position of each pattern letter in the seven filename fields. The date has
# no entry: Y, m and d are parts of field 0, not fields of their own.
FIELD = {
    'C': 1,
    'G': 2,
    'B': 3,
    'P': 4,
    'T': 6,
}

# A document whose field is empty still has to go somewhere. Without this it
# went one directory higher than the rest, because os.path.join drops an empty
# segment silently.
UNKNOWN = '_unknown'

# Anything that could turn one directory into two, or point outside the target.
_UNSAFE = re.compile(r'[\\/\x00-\x1f]')


def invalid_keys(pattern: str) -> list:
    """The letters of the pattern this module does not know, in order."""
    unknown = []
    for key in pattern:
        if key not in PATTERNS and key not in unknown:
            unknown.append(key)
    return unknown


def sanitize(segment: str) -> str:
    """One path segment, with nothing in it that could escape the target."""
    text = _UNSAFE.sub('_', segment or '').strip()
    # '.' and '..' name a directory that already exists somewhere else.
    if set(text) == {'.'}:
        text = text.replace('.', '_')
    return text


def directory_parts(fields: list, pattern: str, labels: list = None) -> list:
    """The directories a document gets under the target, one per letter.

    fields are the seven filename fields; labels, when given, are their
    descriptions and replace the keys. Raises ValueError when the pattern asks
    for a part of a date the document does not have.
    """
    return [sanitize(_value_for(key, fields, labels)) or UNKNOWN
            for key in pattern]


def readable_name(fields: list, extension: str, labels: list = None) -> str:
    """The document renamed for someone who does not know MiAZ filenames.

    Every field is kept, so two documents cannot collapse into one name, but
    the date is written the way it is read and each key becomes its
    description. A field with no value is left out.
    """
    parts = [_readable_date(fields[0])]
    for index in range(1, 7):
        value = sanitize(_label(fields, labels, index))
        if value:
            parts.append(value)
    name = ' - '.join(part for part in parts if part)
    return f"{name}.{extension}" if extension else name


def unique_target(path: str, taken: set) -> str:
    """The given path, or the next free '(n)' variant of it.

    Two documents can produce the same readable name (the same day, the same
    parties, a concept that differs only in case). Overwriting one with the
    other would lose it without saying so.
    """
    if path not in taken:
        return path
    stem, extension = os.path.splitext(path)
    number = 2
    while f"{stem} ({number}){extension}" in taken:
        number += 1
    return f"{stem} ({number}){extension}"


def _value_for(key: str, fields: list, labels: list = None) -> str:
    if key in ('Y', 'm', 'd'):
        # Numbers, never month names: these directories are read in order.
        moment = datetime.strptime(fields[0], '%Y%m%d')
        return {'Y': f'{moment.year:04d}',
                'm': f'{moment.month:02d}',
                'd': f'{moment.day:02d}'}[key]
    return _label(fields, labels, FIELD[key])


def _label(fields: list, labels: list, index: int) -> str:
    """The description of a field, or the key when there is no description."""
    value = fields[index] if index < len(fields) else ''
    if labels is not None:
        text = labels[index] if index < len(labels) else ''
        return text or value
    return value


def _readable_date(value: str) -> str:
    try:
        return datetime.strptime(value, '%Y%m%d').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # Not a date. The plugin still exports the document, and the name it
        # carries is the honest thing to show.
        return sanitize(value)
