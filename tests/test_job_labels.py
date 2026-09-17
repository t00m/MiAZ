#!/usr/bin/python3

"""The jobs a user watches carry words, not slugs.

MiAZJob falls back to a prettified slug, so nothing breaks without a label:
'autoscan-scan' reads as 'Autoscan scan'. That fallback is deliberately plain,
because a developer's slug in front of a user is the signal that the call site
deserves a label. These are the call sites that deserve one.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The long, user-initiated operations: the file that starts each one, and
# whether it takes the lane.
#
# autoscan-detect is labelled but takes no lane. It probes hardware and touches
# no repository document, and the lane exists to keep two operations off the
# same repository. Behind a five minute import the scanner dialog would hang.
LABELLED = {
    'MiAZ/frontend/desktop/services/importdoc.py': ['importdoc-batch'],
    'data/resources/plugins/MiAZImportFromZip/importfromzip.py': ['importfromzip'],
    'data/resources/plugins/MiAZOCR/ocr.py': ['ocr-process'],
    'data/resources/plugins/MiAZAutoScan/autoscan.py': ['autoscan-scan',
                                                        'autoscan-detect'],
}

TAKES_THE_LANE = {'importdoc-batch', 'importfromzip', 'ocr-process',
                  'autoscan-scan'}


def background_calls(text):
    """Every run_in_background call in the source, as one string each."""
    calls = []
    for match in re.finditer(r'run_in_background\(', text):
        depth = 0
        for position in range(match.end() - 1, len(text)):
            if text[position] == '(':
                depth += 1
            elif text[position] == ')':
                depth -= 1
                if depth == 0:
                    calls.append(text[match.start():position + 1])
                    break
    return calls


def named_calls(relative):
    """Every run_in_background call in one file, paired with its name."""
    with open(os.path.join(ROOT, relative), encoding='utf-8') as handle:
        for call in background_calls(handle.read()):
            found = re.search(r"name='([^']+)'", call)
            yield (found.group(1) if found else ''), call


def test_every_long_job_names_itself_for_the_user():
    missing = []
    for relative, names in LABELLED.items():
        for name, call in named_calls(relative):
            if name in names and 'label=' not in call:
                missing.append(f'{relative}: {name}')
    assert missing == [], 'these jobs would show a slug:\n' + '\n'.join(missing)


def test_the_repository_jobs_take_the_lane():
    """Two of these running at once is two processes over one repository."""
    missing = []
    for relative, names in LABELLED.items():
        for name, call in named_calls(relative):
            if name in TAKES_THE_LANE and 'queued=True' not in call:
                missing.append(f'{relative}: {name}')
    assert missing == [], 'these jobs would run over each other:\n' + '\n'.join(missing)


def test_probing_for_a_scanner_does_not_take_the_lane():
    """It touches no repository document. Behind a long import the scanner
    dialog would hang waiting for a lane it never needed."""
    for name, call in named_calls(
            'data/resources/plugins/MiAZAutoScan/autoscan.py'):
        if name == 'autoscan-detect':
            assert 'queued=True' not in call, \
                'looking for a scanner should not wait behind an import'
