#!/usr/bin/python3

"""
Tests for MiAZ.backend.query — the workspace filter as a value object.

The filter used to be the combined state of six widgets read inside
MiAZWorkspace._do_filter_view_main, so none of it could be tested. These tests
pin the exact truth table that code implemented.
"""

from datetime import date

import gi
gi.require_version('GLib', '2.0')

from MiAZ.backend.models import MiAZItem
from MiAZ.backend.query import (
    ANY, DATE_ALL, DATE_NONE, DATE_RANGE, NONE, DocumentQuery, parse_date)


def item(**kwargs):
    """A MiAZItem with sane defaults, overridable per test."""
    fields = {
        'id': '20240315-ES-HOU-BANK-INV-Q1invoice-JOHNDOE.pdf',
        'date': '20240315',
        'country': 'ES',
        'group': 'HOU',
        'sentby_id': 'BANK',
        'purpose': 'INV',
        'subtitle': 'Q1invoice',
        'sentto_id': 'JOHNDOE',
        'active': True,
    }
    fields.update(kwargs)
    return MiAZItem(**fields)


# ---------------------------------------------------------------------------
# The active check
# ---------------------------------------------------------------------------

def test_default_query_matches_an_active_document():
    assert DocumentQuery().matches(item()) is True


def test_default_query_rejects_an_inactive_document():
    assert DocumentQuery().matches(item(active=False)) is False


# ---------------------------------------------------------------------------
# Free text
# ---------------------------------------------------------------------------

def test_search_matches_any_field():
    assert DocumentQuery(search='BANK').matches(item()) is True


def test_search_is_case_insensitive():
    assert DocumentQuery(search='bank').matches(item()) is True


def test_search_rejects_a_document_that_does_not_contain_it():
    assert DocumentQuery(search='NOTHERE').matches(item()) is False


def test_empty_search_matches_everything():
    assert DocumentQuery(search='').matches(item()) is True


# ---------------------------------------------------------------------------
# Concept
# ---------------------------------------------------------------------------

def test_concept_matches_a_substring():
    assert DocumentQuery(concept='invoice').matches(item()) is True


def test_concept_is_case_insensitive():
    assert DocumentQuery(concept='INVOICE').matches(item()) is True


def test_concept_rejects_a_document_that_does_not_contain_it():
    assert DocumentQuery(concept='receipt').matches(item()) is False


def test_empty_concept_matches_everything():
    assert DocumentQuery(concept='').matches(item()) is True


# ---------------------------------------------------------------------------
# Field values
# ---------------------------------------------------------------------------

def test_any_matches_every_value():
    assert DocumentQuery(country=ANY).matches(item()) is True


def test_a_field_code_matches_that_value():
    assert DocumentQuery(country='ES').matches(item()) is True


def test_a_field_code_is_case_insensitive():
    assert DocumentQuery(country='es').matches(item()) is True


def test_a_field_code_rejects_a_different_value():
    assert DocumentQuery(country='FR').matches(item()) is False


def test_none_matches_an_empty_value():
    assert DocumentQuery(country=NONE).matches(item(country='')) is True


def test_none_rejects_a_non_empty_value():
    assert DocumentQuery(country=NONE).matches(item(country='ES')) is False


def test_none_still_obeys_the_active_check():
    """A document with an empty field is normally pending, so the plain query
    hides it. Review mode or ignore_active is what surfaces it.
    """
    query = DocumentQuery(country=NONE)
    assert query.matches(item(country='', active=False)) is False
    assert DocumentQuery(country=NONE, only_pending=True).matches(
        item(country='', active=False)) is True


def test_every_field_is_checked():
    assert DocumentQuery(group='HOU').matches(item()) is True
    assert DocumentQuery(group='FIN').matches(item()) is False
    assert DocumentQuery(sentby='BANK').matches(item()) is True
    assert DocumentQuery(sentby='OTHER').matches(item()) is False
    assert DocumentQuery(purpose='INV').matches(item()) is True
    assert DocumentQuery(purpose='REQ').matches(item()) is False
    assert DocumentQuery(sentto='JOHNDOE').matches(item()) is True
    assert DocumentQuery(sentto='JANEDOE').matches(item()) is False


def test_field_conditions_are_combined_with_and():
    assert DocumentQuery(country='ES', group='FIN').matches(item()) is False


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def test_date_mode_all_matches_everything():
    assert DocumentQuery().matches(item(date='19990101')) is True


def test_date_mode_all_matches_an_unparseable_date():
    assert DocumentQuery().matches(item(date='NODATE')) is True


def test_date_mode_none_matches_only_an_unparseable_date():
    query = DocumentQuery(date_mode='none')
    assert query.matches(item(date='NODATE')) is True
    assert query.matches(item(date='20240315')) is False


def test_date_range_matches_inside_the_bounds():
    query = DocumentQuery(
        date_mode='range',
        date_since=date(2024, 1, 1),
        date_until=date(2024, 12, 31))
    assert query.matches(item()) is True


def test_date_range_is_inclusive_on_both_ends():
    query = DocumentQuery(
        date_mode='range',
        date_since=date(2024, 3, 15),
        date_until=date(2024, 3, 15))
    assert query.matches(item()) is True


def test_date_range_rejects_a_document_outside_it():
    query = DocumentQuery(
        date_mode='range',
        date_since=date(2025, 1, 1),
        date_until=date(2025, 12, 31))
    assert query.matches(item()) is False


def test_date_range_rejects_an_unparseable_date():
    query = DocumentQuery(
        date_mode='range',
        date_since=date(2024, 1, 1),
        date_until=date(2024, 12, 31))
    assert query.matches(item(date='NODATE')) is False


# ---------------------------------------------------------------------------
# Review mode and the bypasses
# ---------------------------------------------------------------------------

def test_only_pending_shows_inactive_documents():
    assert DocumentQuery(only_pending=True).matches(item(active=False)) is True


def test_only_pending_hides_active_documents():
    assert DocumentQuery(only_pending=True).matches(item()) is False


def test_only_pending_still_applies_the_field_filters():
    query = DocumentQuery(only_pending=True, country='FR')
    assert query.matches(item(active=False)) is False


def test_only_pending_ignores_the_date_filter():
    """Review lists everything needing attention, whatever its date."""
    query = DocumentQuery(
        only_pending=True,
        date_mode='range',
        date_since=date(2025, 1, 1),
        date_until=date(2025, 12, 31))
    assert query.matches(item(active=False)) is True


def test_ignore_date_lifts_the_range_check():
    query = DocumentQuery(
        ignore_date=True,
        date_mode='range',
        date_since=date(2025, 1, 1),
        date_until=date(2025, 12, 31))
    assert query.matches(item()) is True


def test_ignore_active_lets_a_pending_document_through():
    assert DocumentQuery(ignore_active=True).matches(item(active=False)) is True


def test_ignore_active_with_only_pending_matches_nothing():
    """Preserved from the widget version: the project bypass forced the active
    check to True before the review branch inverted it, so the two together
    always produced an empty view.
    """
    query = DocumentQuery(only_pending=True, ignore_active=True)
    assert query.matches(item(active=False)) is False
    assert query.matches(item()) is False


# ---------------------------------------------------------------------------
# Equivalence with the widget version this replaces
# ---------------------------------------------------------------------------

def _legacy_matches(item, search, concept, values, date_ll, date_ul,
                    date_start, date_end, review, bypass):
    """MiAZWorkspace._do_filter_view_main, transcribed verbatim.

    Including the quirk in _do_eval_cond_matches: selecting 'None' against a
    non-empty value fell off the end of the elif chain and returned None, which
    is falsy, so it read as a rejection.
    """
    def cond_matches(selected, value):
        if selected == 'Any':
            return True
        elif selected == 'None':
            if len(value) == 0:
                return True
        else:
            return selected.upper() == value.upper()

    def cond_date(value):
        item_dt = parse_date(value)
        if date_ll == 'All' and date_ul == 'All':
            return True
        elif date_ll == 'None' and date_ul == 'None':
            return item_dt is None
        elif item_dt is None:
            return False
        return date_start <= item_dt <= date_end

    c0 = search.upper() in item.search_text_upper
    ca = item.active
    cd = cond_date(item.date)
    c1 = cond_matches(values['Country'], item.country)
    c2 = cond_matches(values['Group'], item.group)
    c4 = cond_matches(values['SentBy'], item.sentby_id)
    c5 = cond_matches(values['Purpose'], item.purpose)
    c6 = cond_matches(values['SentTo'], item.sentto_id)
    cc = True if not concept else concept.upper() in item.subtitle.upper()

    if bypass:
        cd = True
        ca = True

    if review:
        return bool(not ca and c0 and c1 and c2 and c4 and c5 and c6 and cc)
    return bool(ca and c0 and c1 and c2 and c4 and c5 and c6 and cd and cc)


def test_matches_agrees_with_the_widget_version_it_replaces():
    """Walk a matrix of filter states against a matrix of documents and require
    the same verdict from both implementations.
    """
    items = [
        item(),
        item(active=False),
        item(country='', active=False),
        item(date='NODATE'),
        item(date='20200101'),
        item(country='FR', group='FIN', sentby_id='OTHER'),
        item(subtitle='receipt'),
    ]
    searches = ['', 'BANK', 'nothere']
    concepts = ['', 'invoice']
    value_sets = [
        {'Country': ANY, 'Group': ANY, 'SentBy': ANY, 'Purpose': ANY, 'SentTo': ANY},
        {'Country': 'ES', 'Group': ANY, 'SentBy': ANY, 'Purpose': ANY, 'SentTo': ANY},
        {'Country': NONE, 'Group': ANY, 'SentBy': ANY, 'Purpose': ANY, 'SentTo': ANY},
        {'Country': ANY, 'Group': 'HOU', 'SentBy': 'BANK', 'Purpose': 'INV', 'SentTo': 'JOHNDOE'},
    ]
    dates = [
        ('All', 'All', None, None, DATE_ALL),
        ('None', 'None', None, None, DATE_NONE),
        ('20240101', '20241231', date(2024, 1, 1), date(2024, 12, 31), DATE_RANGE),
    ]

    checked = 0
    for doc in items:
        for search in searches:
            for concept in concepts:
                for values in value_sets:
                    for ll, ul, start, end, mode in dates:
                        for review in (False, True):
                            for bypass in (False, True):
                                expected = _legacy_matches(
                                    doc, search, concept, values,
                                    ll, ul, start, end, review, bypass)
                                query = DocumentQuery(
                                    search=search, concept=concept,
                                    country=values['Country'],
                                    group=values['Group'],
                                    sentby=values['SentBy'],
                                    purpose=values['Purpose'],
                                    sentto=values['SentTo'],
                                    date_mode=mode,
                                    date_since=start, date_until=end,
                                    only_pending=review,
                                    ignore_date=bypass,
                                    ignore_active=bypass)
                                assert query.matches(doc) is expected, (
                                    f"{doc.id} search={search!r} concept={concept!r} "
                                    f"values={values} date={mode} review={review} "
                                    f"bypass={bypass}")
                                checked += 1
    # 7 items x 3 searches x 2 concepts x 4 value sets x 3 dates x review x bypass
    assert checked == 2016


# ---------------------------------------------------------------------------
# Serialization, which is what saved searches will need
# ---------------------------------------------------------------------------

def test_a_query_survives_a_round_trip_through_a_dict():
    query = DocumentQuery(
        search='bank', concept='invoice', country='ES',
        date_mode='range',
        date_since=date(2024, 1, 1), date_until=date(2024, 12, 31))
    assert DocumentQuery.from_dict(query.to_dict()) == query


def test_an_empty_query_round_trips():
    assert DocumentQuery.from_dict(DocumentQuery().to_dict()) == DocumentQuery()


def test_from_dict_ignores_unknown_keys():
    """A saved search written by a newer version must not crash an older one."""
    restored = DocumentQuery.from_dict({'country': 'ES', 'nonexistent': 1})
    assert restored.country == 'ES'
