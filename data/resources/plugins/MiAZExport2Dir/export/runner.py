"""
# File: runner.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Copy a set of documents out of the repository, and say what happened

The copying is passed in rather than done here: the plugin hands over the
repository's own copy function, and a test hands over one that counts calls.
That is also what keeps this module free of GTK, so it can run in the worker
thread the plugin starts.
"""

import os
from gettext import gettext as _

from export.layout import directory_parts, readable_name, unique_target


def export_documents(documents, target_dir, docs_dir, copy,
                     pattern='', readable=False, report=None):
    """Copy every document under target_dir. Returns (copied, failures).

    documents are (doc_id, fields, labels, extension) tuples; fields and
    labels come from the filename and from the vocabulary. copy(source,
    target) returns True when the file was written. failures pairs a document
    with the reason it was left behind, so the caller can show them.
    """
    copied = 0
    failures = []
    taken = set()
    total = len(documents)
    for number, (doc_id, fields, labels, extension) in enumerate(documents, start=1):
        if report is not None:
            report(doc_id, number / total)
        try:
            target = _target_for(doc_id, fields, labels, extension,
                                 target_dir, pattern, readable, taken)
        except ValueError:
            failures.append((doc_id, _('the name is not in MiAZ format')))
            continue
        except IndexError:
            failures.append((doc_id, _('the name has too few fields')))
            continue
        except OSError as error:
            failures.append((doc_id, str(error)))
            continue

        if copy(os.path.join(docs_dir, doc_id), target):
            taken.add(target)
            copied += 1
        else:
            failures.append((doc_id, _('the file could not be copied')))
    return copied, failures


def _target_for(doc_id, fields, labels, extension,
                target_dir, pattern, readable, taken):
    """Where this document goes, with its directories already created."""
    directory = target_dir
    if pattern:
        # Without readable names the directories keep the keys, which is what
        # a pattern is for: short, sortable, the same as the filename.
        parts = directory_parts(fields, pattern, labels if readable else None)
        directory = os.path.join(target_dir, *parts)
        os.makedirs(directory, exist_ok=True)
    if readable:
        basename = readable_name(fields, extension, labels)
    else:
        basename = os.path.basename(doc_id)
    return unique_target(os.path.join(directory, basename), taken)
