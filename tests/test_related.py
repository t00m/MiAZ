#!/usr/bin/python3

"""Which documents the MiAZRelated plugin calls one case.

The `related` package lives under the plugin directory, which is not on the
default path, so the test inserts it the way the plugin does at runtime.
"""

import os
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZRelated')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def name(date='20260101', sentby='BANKX', concept='mortgage', sentto='JOHNDOE',
         purpose='INV'):
    return f"{date}-ES-FIN-{sentby}-{purpose}-{concept}-{sentto}.pdf"


def test_the_same_concept_with_a_shared_party_is_the_same_case():
    from related.chain import related
    target = name(purpose='REQ', date='20260101')
    answer = name(purpose='RCP', date='20260215')
    other = name(concept='electricity')
    report = related([target, answer, other], target)
    assert report['same_party'] == [answer]
    assert report['other_party'] == []


def test_the_same_concept_from_a_stranger_is_the_other_side():
    from related.chain import related
    target = name(sentby='BANKX', sentto='JOHNDOE')
    reply = name(sentby='LAWYER', sentto='COURT')
    report = related([target, reply], target)
    assert report['same_party'] == []
    assert report['other_party'] == [reply]


def test_case_and_underscores_do_not_split_a_concept():
    from related.chain import related
    target = name(concept='CAR_INSURANCE')
    same = name(concept='car insurance', date='20260303')
    report = related([target, same], target)
    assert report['same_party'] == [same]


def test_the_document_itself_is_never_related_to_itself():
    from related.chain import related
    target = name()
    assert related([target], target) == {'same_party': [], 'other_party': []}


def test_results_are_ordered_by_date():
    from related.chain import related
    target = name(date='20260601', purpose='REQ')
    older = name(date='20240101', purpose='INF')
    newer = name(date='20261231', purpose='RCP')
    report = related([target, newer, older], target)
    assert report['same_party'] == [older, newer]


def test_a_filename_that_is_not_seven_fields_relates_to_nothing():
    from related.chain import related
    assert related([name()], 'random.pdf') == {'same_party': [], 'other_party': []}


def test_an_empty_concept_relates_to_nothing():
    from related.chain import related
    target = "20260101-ES-FIN-BANKX-INV--JOHNDOE.pdf"
    assert related([target, name()], target) == {'same_party': [], 'other_party': []}


def test_chains_groups_the_repository_by_concept_largest_first():
    from related.chain import chains
    documents = [name(concept='mortgage', date='20260101'),
                 name(concept='mortgage', date='20260202', purpose='RCP'),
                 name(concept='MORTGAGE', date='20260303', purpose='REQ'),
                 name(concept='electricity'),
                 name(concept='water', date='20250101'),
                 name(concept='water', date='20250202', purpose='RCP')]
    found = chains(documents)
    assert [key for key, _names in found] == ['MORTGAGE', 'WATER']
    assert len(found[0][1]) == 3
    # Ordered by date inside a chain.
    assert found[0][1][0].startswith('20260101')


def test_a_concept_used_once_is_not_a_chain():
    from related.chain import chains
    assert chains([name(concept='alone')]) == []
    assert chains([name(concept='alone')], minimum=1) != []
