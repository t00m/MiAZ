
"""
# File: rename.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The seven fields of a document name, split, composed and checked
"""

from MiAZ.backend.util import date_is_valid

# The fields of a document name, in the order they are written.
FIELDS = ('date', 'country', 'group', 'sentby', 'purpose', 'concept', 'sentto')

# Which configuration holds the values a field may take. The date is checked
# as a date and the concept is whatever the document is about, so neither has
# one.
CONFIG_OF = {
    'country': 'Country',
    'group': 'Group',
    'sentby': 'SentBy',
    'purpose': 'Purpose',
    'sentto': 'SentTo',
}

# What can be wrong with a field. Returned rather than written out, so the
# message is the frontend's to phrase and to translate.
UNKNOWN = 'unknown'
NOT_A_DATE = 'not-a-date'
EMPTY = 'empty'


def split(util, basename):
    """The fields of a document name, and its extension.

    A name that is not seven fields is read the way filename_normalize reads
    it: the whole of it is what the document is about, and every other field
    is still to be filled in. That is the state a document arrives in, and it
    is the one somebody renames from.
    """
    name, extension = util.filename_details(basename)
    parts = name.split('-')
    if len(parts) == len(FIELDS):
        return dict(zip(FIELDS, parts)), extension
    fields = {field: '' for field in FIELDS}
    fields['concept'] = util.valid_key(name).upper()
    return fields, extension


def compose(fields, extension):
    """The document name these fields make."""
    name = '-'.join(fields[field] for field in FIELDS)
    return f'{name}.{extension}' if extension else name


def normalize(util, changes):
    """What each given value becomes in a filename.

    Uppercase, because that is how a repository stores its names, and the
    concept without the characters a field cannot hold: a space or a separator
    in it would make two fields out of one.
    """
    normalized = {}
    for field, value in changes.items():
        if value is None:
            continue
        if field == 'concept':
            normalized[field] = util.valid_key(value).upper()
        else:
            normalized[field] = value.strip().upper()
    return normalized


def problems(app, fields):
    """What stops these fields being a document name.

    A list of (field, value, reason), in the order the fields are written, and
    empty when there is nothing wrong. Every problem is reported rather than
    the first, so one run says everything there is to fix.

    The vocabulary check is exists_used, the same question the rename dialog's
    button asks: a value the repository has not enabled is not one its
    documents may carry.
    """
    found = []
    for field in FIELDS:
        value = fields.get(field, '')
        if not value:
            # A field nobody has filled in yet, which is every field of a
            # document that has just arrived. It is not an unknown key, and
            # telling somebody to add '' to the vocabulary helps nobody.
            found.append((field, value, EMPTY))
        elif field == 'date':
            if not date_is_valid(value):
                found.append((field, value, NOT_A_DATE))
        elif field == 'concept':
            continue
        else:
            config = app.get_config(CONFIG_OF[field])
            if config is None or not config.exists_used(value):
                found.append((field, value, UNKNOWN))
    return found
