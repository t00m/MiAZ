#!/usr/bin/python3

"""What the vocabulary analysis reports.

Used by MiAZDoctor, so it lives in the backend,
next to the duplicate scan. Pure Python: no GTK, no services, no file I/O.
"""

from MiAZ.backend.vocabhealth import (
    analyse, analyse_field, count_codes, is_unnamed, totals, FIELD_POSITION)


def name(country='ES', group='FIN', sentby='BANKX', purpose='INV',
         concept='rent', sentto='JOHNDOE', date='20260101'):
    return f"{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.pdf"


def test_a_description_that_repeats_the_code_says_nothing():
    assert is_unnamed('BANKX', 'BANKX') is True
    assert is_unnamed('BANKX', '  ') is True
    assert is_unnamed('BANKX', '') is True
    assert is_unnamed('BANKX', 'Bank X') is False


def test_separators_do_not_make_a_description():
    """"TRV INS" describes TRV_INS no better than the code does."""
    assert is_unnamed('TRV_INS', 'TRV INS') is True
    assert is_unnamed('TRV-INS', 'TRVINS') is True


def test_case_is_a_real_difference():
    """Codes are upper case, so "Health" for HEALTH is somebody typing a word.

    Comparing case-insensitively flagged 234 documents worth of HEALTH as a
    problem and pushed the values that really say nothing down the list.
    """
    assert is_unnamed('HEALTH', 'Health') is False
    assert is_unnamed('LIFE', 'Life') is False
    assert is_unnamed('GENERALI', 'GENERALI') is True


def test_unused_codes_are_the_ones_no_document_references():
    documents = [name(sentby='BANKX'), name(sentby='BANKX')]
    used = {'BANKX': 'Bank X', 'GONE': 'Former bank'}
    report = analyse_field(documents, used, FIELD_POSITION['SentBy'])
    assert report['unused'] == [('GONE', 'Former bank', 0)]
    assert report['unnamed'] == []
    assert report['unknown'] == []


def test_unknown_codes_are_used_by_documents_and_absent_from_the_vocabulary():
    documents = [name(sentby='STRANGER'), name(sentby='BANKX')]
    used = {'BANKX': 'Bank X'}
    report = analyse_field(documents, used, FIELD_POSITION['SentBy'])
    assert report['unknown'] == [('STRANGER', '', 1)]


def test_unnamed_codes_are_ranked_by_how_many_documents_they_affect():
    documents = [name(sentby='AAA')] + [name(sentby='BBB')] * 3
    used = {'AAA': 'AAA', 'BBB': 'BBB'}
    report = analyse_field(documents, used, FIELD_POSITION['SentBy'])
    assert [code for code, _d, _c in report['unnamed']] == ['BBB', 'AAA']
    assert report['unnamed'][0][2] == 3


def test_a_used_code_that_is_named_is_not_a_problem():
    report = analyse_field([name(sentby='BANKX')], {'BANKX': 'Bank X'},
                           FIELD_POSITION['SentBy'])
    assert report == {'unnamed': [], 'unused': [], 'unknown': []}


def test_a_filename_that_is_not_seven_fields_is_ignored():
    assert count_codes(['not-a-miaz-name.pdf'], FIELD_POSITION['SentBy']) == {}
    assert count_codes(['20260101-ES-FIN-BANKX-INV-rent-JOHNDOE.pdf'],
                       FIELD_POSITION['SentBy']) == {'BANKX': 1}


def test_a_concept_holding_hyphens_does_not_shift_the_fields():
    # get_fields folds the extra parts back into SentTo, so SentBy is safe.
    documents = ['20260101-ES-FIN-BANKX-INV-a-b-c-JOHNDOE.pdf']
    assert count_codes(documents, FIELD_POSITION['SentBy']) == {'BANKX': 1}


def test_every_field_is_analysed_and_totalled():
    documents = [name(country='ES', group='FIN', sentby='BANKX',
                      purpose='INV', sentto='JOHNDOE')]
    vocabularies = {
        'Country': {'ES': 'Spain', 'DE': 'Germany'},
        'Group': {'FIN': 'FIN'},
        'SentBy': {'BANKX': 'Bank X'},
        'Purpose': {'INV': 'Invoice'},
        'SentTo': {'JOHNDOE': 'John Doe'},
    }
    report = analyse(documents, vocabularies)
    assert set(report) == {'Country', 'Group', 'SentBy', 'Purpose', 'SentTo'}
    assert report['Country']['unused'] == [('DE', 'Germany', 0)]
    assert report['Group']['unnamed'] == [('FIN', 'FIN', 1)]
    assert totals(report) == {'unnamed': 1, 'unused': 1, 'unknown': 0}


def test_a_field_with_no_vocabulary_is_skipped():
    assert analyse([name()], {'SentBy': {'BANKX': 'Bank X'}}) == {
        'SentBy': {'unnamed': [], 'unused': [], 'unknown': []}}
