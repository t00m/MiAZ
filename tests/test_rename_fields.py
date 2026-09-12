#!/usr/bin/python3

"""
Tests for MiAZ.backend.rename, the seven fields of a document name.

The rename dialog splits a name, composes one back and checks each field
against the repository configuration, all inside the widget. `miaz rename`
needs the same three things without a display, so they live here, as functions
that read nothing but what they are given.
"""

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from MiAZ.backend.rename import (EMPTY, FIELDS, NOT_A_DATE, UNKNOWN, compose,
                                 normalize, problems, split)
from MiAZ.backend.util import MiAZUtil


class MockConfig:
    """Stands in for one vocabulary: the keys a repository has enabled."""

    def __init__(self, used=()):
        self._used = set(used)

    def exists_used(self, key):
        return key in self._used


class MockApp:
    def __init__(self, **configs):
        self._configs = {name: MockConfig(used) for name, used in configs.items()}

    def get_config(self, name):
        return self._configs.get(name)


def an_app():
    return MockApp(Country=['ES'], Group=['HOU'], SentBy=['BANK'],
                   Purpose=['INV'], SentTo=['JOHN'])


def util():
    return MiAZUtil(an_app())


DOC = '20240115-ES-HOU-BANK-INV-RENT-JOHN.pdf'


def good_fields():
    return {'date': '20240115', 'country': 'ES', 'group': 'HOU',
            'sentby': 'BANK', 'purpose': 'INV', 'concept': 'RENT',
            'sentto': 'JOHN'}


# ---------------------------------------------------------------------------
# split and compose
# ---------------------------------------------------------------------------

def test_a_name_splits_into_its_seven_fields():
    fields, extension = split(util(), DOC)
    assert fields == good_fields()
    assert extension == 'pdf'


def test_the_fields_are_in_the_order_they_are_written():
    assert FIELDS == ('date', 'country', 'group', 'sentby', 'purpose',
                      'concept', 'sentto')


def test_composing_the_fields_gives_the_name_back():
    fields, extension = split(util(), DOC)
    assert compose(fields, extension) == DOC


def test_a_name_that_is_not_seven_fields_is_all_concept():
    """What filename_normalize does with it: the whole name is what the
    document is about, and every other field is still to be filled in."""
    fields, extension = split(util(), 'bank statement.pdf')
    assert fields['concept'] == 'BANK_STATEMENT'
    assert fields['country'] == ''
    assert extension == 'pdf'


def test_a_name_with_no_extension_composes_without_a_dot():
    fields, extension = split(util(), '20240115-ES-HOU-BANK-INV-RENT-JOHN')
    assert extension == ''
    assert compose(fields, extension) == '20240115-ES-HOU-BANK-INV-RENT-JOHN'


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

def test_a_value_is_upper_cased():
    """A repository stores its names uppercase, so `--country es` is ES."""
    assert normalize(util(), {'country': 'es'}) == {'country': 'ES'}


def test_the_concept_loses_what_a_field_cannot_hold():
    """Spaces and separators would make a second field out of one."""
    assert normalize(util(), {'concept': 'rent march'})['concept'] == 'RENT_MARCH'
    assert normalize(util(), {'concept': 'a-b'})['concept'] == 'A_B'


def test_a_field_not_given_is_not_in_the_result():
    assert normalize(util(), {'country': 'es', 'group': None}) == {'country': 'ES'}


# ---------------------------------------------------------------------------
# problems
# ---------------------------------------------------------------------------

def test_a_name_the_repository_knows_has_no_problems():
    assert problems(an_app(), good_fields()) == []


def test_a_key_the_repository_does_not_have_is_a_problem():
    fields = good_fields()
    fields['country'] = 'FR'
    assert problems(an_app(), fields) == [('country', 'FR', UNKNOWN)]


def test_every_field_with_a_vocabulary_is_checked():
    fields = good_fields()
    for field in ('country', 'group', 'sentby', 'purpose', 'sentto'):
        broken = dict(fields, **{field: 'NOPE'})
        assert problems(an_app(), broken) == [(field, 'NOPE', UNKNOWN)]


def test_a_date_that_is_not_a_date_is_a_problem():
    fields = good_fields()
    fields['date'] = '20240230'
    assert problems(an_app(), fields) == [('date', '20240230', NOT_A_DATE)]


def test_an_empty_concept_is_a_problem():
    fields = good_fields()
    fields['concept'] = ''
    assert problems(an_app(), fields) == [('concept', '', EMPTY)]


def test_a_field_nobody_has_filled_in_is_empty_not_unknown():
    """Every field of a document that has just arrived is blank, and telling
    somebody to add '' to a vocabulary helps nobody."""
    fields = good_fields()
    fields['country'] = ''
    fields['date'] = ''
    assert problems(an_app(), fields) == [('date', '', EMPTY),
                                          ('country', '', EMPTY)]


def test_every_problem_is_reported_not_only_the_first():
    """One run says everything there is to fix, rather than one thing per try."""
    fields = good_fields()
    fields['date'] = 'nope'
    fields['country'] = 'FR'
    fields['concept'] = ''
    assert problems(an_app(), fields) == [('date', 'nope', NOT_A_DATE),
                                          ('country', 'FR', UNKNOWN),
                                          ('concept', '', EMPTY)]


def test_the_problems_are_in_the_order_the_fields_are_written():
    fields = good_fields()
    fields['sentto'] = 'NOPE'
    fields['country'] = 'NOPE'
    assert [problem[0] for problem in problems(an_app(), fields)] == [
        'country', 'sentto']
