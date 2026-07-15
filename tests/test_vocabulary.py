#!/usr/bin/python3

"""
Tests that the translatable default labels in MiAZ.backend.vocabulary stay in
sync with the bundled JSON vocabularies. If they drift, util.humanize_value()
would look up a string that is not in the catalog and the label would show
untranslated, so this guards the translation path.
"""

import json
import os

from MiAZ.backend import vocabulary

ROOT = os.path.join(os.path.dirname(__file__), '..')


def _json_values(name):
    with open(os.path.join(ROOT, 'data', 'resources', 'conf', name), encoding='utf-8') as handler:
        return set(json.load(handler).values())


def test_group_labels_match_json():
    assert set(vocabulary.GROUP_LABELS) == _json_values('MiAZ-groups.json')


def test_purpose_labels_match_json():
    assert set(vocabulary.PURPOSE_LABELS) == _json_values('MiAZ-purposes.json')
