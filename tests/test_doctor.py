#!/usr/bin/python3

"""The repository health report: what it finds and how it ranks it.

Pure Python. Reading the repository is the caller's job, so every check here
takes data already gathered.
"""

from MiAZ.backend.doctor import (
    NOTE, PROBLEM, WARNING, build_report, check_names, check_vocabulary,
    is_healthy, summarise)


def name(date='20260101', country='ES', group='FIN', sentby='BANKX',
         purpose='INV', concept='rent', sentto='JOHNDOE'):
    return f"{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.pdf"


VOCABULARY = {
    'Country': {'ES': 'Spain'},
    'Group': {'FIN': 'Finance'},
    'SentBy': {'BANKX': 'Bank X'},
    'Purpose': {'INV': 'Invoice'},
    'SentTo': {'JOHNDOE': 'John Doe'},
}


def test_a_healthy_repository_reports_nothing():
    report = build_report([name()], VOCABULARY)
    assert report == []
    assert is_healthy(report) is True


def test_a_name_that_is_not_seven_fields_is_a_problem():
    assert check_names(['holiday.pdf']) == ['holiday.pdf']
    assert check_names([name()]) == []


def test_an_empty_field_is_not_a_valid_name():
    assert check_names(['20260101-ES-FIN--INV-rent-JOHNDOE.pdf']) != []


def test_a_name_whose_date_is_not_a_date_is_a_problem():
    assert check_names([name(date='20261301')]) != []
    assert check_names([name(date='99991231')]) == [], 'the unknown date is a date'


def test_unknown_codes_are_reported_per_field():
    found = check_vocabulary([name(sentby='STRANGER')], VOCABULARY)
    assert ('SentBy', 'STRANGER', 1) in found['unknown']


def test_findings_are_ordered_worst_first():
    documents = [name(sentby='STRANGER'), 'holiday.pdf']
    vocab = dict(VOCABULARY, Group={'FIN': 'FIN', 'GONE': 'Retired'})
    report = build_report(documents, vocab, duplicates=[['a.pdf', 'b.pdf']],
                          empty=['void.pdf'], unreadable=['locked.pdf'])
    severities = [finding.severity for finding in report]
    assert severities == sorted(
        severities, key=lambda s: (PROBLEM, WARNING, NOTE).index(s))
    assert severities[0] == PROBLEM
    assert severities[-1] == NOTE


def test_a_check_with_nothing_to_say_is_left_out():
    """A report is what needs attention, not a list of things that are fine."""
    report = build_report([name()], VOCABULARY, duplicates=[['a.pdf', 'b.pdf']])
    assert [finding.check for finding in report] == ['duplicates']


def test_every_kind_of_trouble_is_counted():
    documents = [name(sentby='STRANGER'), 'holiday.pdf']
    vocab = dict(VOCABULARY, Group={'FIN': 'FIN', 'GONE': 'Retired'})
    report = build_report(documents, vocab, duplicates=[['a.pdf', 'b.pdf']],
                          empty=['void.pdf'], unreadable=['locked.pdf'])
    checks = {finding.check: finding for finding in report}
    assert set(checks) == {'unreadable', 'names', 'unknown-codes',
                           'empty', 'duplicates', 'undescribed-codes',
                           'unused-codes'}
    assert checks['duplicates'].count == 1
    assert checks['undescribed-codes'].count == 1, 'FIN describes nothing'
    # GONE was retired, and BANKX stopped being used the moment the only
    # document that had it was filed under STRANGER instead.
    unused = {code for _field, code, _count in checks['unused-codes'].items}
    assert unused == {'GONE', 'BANKX'}
    assert summarise(report) == {PROBLEM: 3, WARNING: 3, NOTE: 1}


def test_every_finding_carries_a_hint():
    report = build_report(['holiday.pdf'], VOCABULARY)
    assert all(finding.hint for finding in report)
    assert all(finding.summary for finding in report)


def test_a_finding_names_the_documents_it_is_about():
    """The report has to be actionable: the view is narrowed to these."""
    documents = [name(sentby='STRANGER'), 'holiday.pdf', name()]
    report = build_report(documents, VOCABULARY,
                          duplicates=[['a.pdf', 'b.pdf']], empty=['void.pdf'])
    checks = {finding.check: finding for finding in report}
    assert checks['names'].documents == ['holiday.pdf']
    assert checks['empty'].documents == ['void.pdf']
    assert checks['duplicates'].documents == ['a.pdf', 'b.pdf']
    # A value the vocabulary does not know points at the documents using it.
    assert checks['unknown-codes'].documents == [name(sentby='STRANGER')]


def test_a_vocabulary_value_nothing_uses_points_at_no_document():
    """There is nothing to show, so the report must not offer to show it."""
    vocab = dict(VOCABULARY, Group={'FIN': 'Finance', 'GONE': 'Retired'})
    report = build_report([name()], vocab)
    checks = {finding.check: finding for finding in report}
    assert checks['unused-codes'].count == 1
    assert checks['unused-codes'].documents == []


def test_the_same_document_is_not_listed_twice_for_one_finding():
    """Two undescribed values on one document is still one document."""
    vocab = dict(VOCABULARY, Group={'FIN': 'FIN'}, SentBy={'BANKX': 'BANKX'})
    report = build_report([name()], vocab)
    checks = {finding.check: finding for finding in report}
    assert checks['undescribed-codes'].count == 2, 'two values are undescribed'
    assert checks['undescribed-codes'].documents == [name()], 'one document'
