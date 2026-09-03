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
    ANY, DATE_ALL, DATE_NONE, DATE_PRESET_ALL, DATE_PRESET_THIS_MONTH,
    DATE_PRESETS, DATE_RANGE, NONE, DocumentQuery, parse_date)


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


# ---------------------------------------------------------------------------
# Date presets: what a saved search should remember instead of raw dates
# ---------------------------------------------------------------------------

def test_a_query_has_no_date_preset_by_default():
    assert DocumentQuery().date_preset == ''


def test_a_query_can_carry_a_date_preset():
    query = DocumentQuery(date_preset=DATE_PRESET_THIS_MONTH)
    assert query.date_preset == 'this-month'


def test_the_preset_does_not_decide_what_matches():
    """The preset says which sidebar entry produced the range. Filtering still
    reads date_mode and the bounds, so a stale preset cannot hide a document.
    """
    query = DocumentQuery(
        date_preset=DATE_PRESET_THIS_MONTH,
        date_mode=DATE_RANGE,
        date_since=date(2024, 1, 1),
        date_until=date(2024, 12, 31))
    assert query.matches(item()) is True


def test_a_preset_round_trips_through_a_dict():
    query = DocumentQuery(date_preset=DATE_PRESET_THIS_MONTH,
                          date_mode=DATE_RANGE,
                          date_since=date(2024, 1, 1),
                          date_until=date(2024, 12, 31))
    assert DocumentQuery.from_dict(query.to_dict()) == query


def test_the_preset_survives_without_bounds():
    """What a saved search stores: the preset alone. The bounds are resolved
    from the sidebar when the search is applied, so 'this month' means the month
    it is opened in, not the month it was saved in.
    """
    restored = DocumentQuery.from_dict({'date_preset': DATE_PRESET_THIS_MONTH})
    assert restored.date_preset == DATE_PRESET_THIS_MONTH
    assert restored.date_since is None


def test_every_preset_token_is_unique():
    assert len(DATE_PRESETS) == len(set(DATE_PRESETS))


def test_the_all_documents_preset_is_a_token_too():
    """Selecting "All documents" is a choice, not the absence of one, so it has
    to survive a round trip like the others."""
    assert DATE_PRESET_ALL in DATE_PRESETS


# ---------------------------------------------------------------------------
# resolve_preset
# ---------------------------------------------------------------------------
# The arithmetic behind the preset tokens used to sit in the workspace widget,
# inside the loop building the sidebar entries, so nothing else could ask what
# 'last-6-months' means without copying it.

from datetime import datetime, timedelta

from MiAZ.backend.query import (DATE_PRESET_FUTURE, DATE_PRESET_LAST_6_MONTHS,
                                resolve_preset)
from MiAZ.backend.util import MiAZUtil

NOW = datetime(2026, 8, 13)


class NoServices:
    def get_service(self, name):
        return None


def util():
    """MiAZUtil owns the date helpers, and needs nothing from the app here."""
    return MiAZUtil(NoServices())


def test_resolve_this_month_starts_on_the_first():
    since, until = resolve_preset(DATE_PRESET_THIS_MONTH, NOW, util())
    assert (since.year, since.month, since.day) == (2026, 8, 1)
    assert until == NOW.date()


def test_resolve_last_6_months_matches_the_util_helper():
    since, _until = resolve_preset(DATE_PRESET_LAST_6_MONTHS, NOW, util())
    assert since == util().since_date_last_n_months(NOW, 6).date()


def test_resolve_years_start_on_the_first_of_january():
    since, _until = resolve_preset('2-years', NOW, util())
    assert (since.year, since.month, since.day) == (2024, 1, 1)


def test_resolve_future_starts_tomorrow():
    since, until = resolve_preset(DATE_PRESET_FUTURE, NOW, util())
    assert since == (NOW + timedelta(days=1)).date()
    assert until.year == 9999


def test_resolve_all_documents_has_no_bounds():
    assert resolve_preset(DATE_PRESET_ALL, NOW, util()) == (None, None)


def test_resolve_unknown_token_has_no_bounds():
    assert resolve_preset('last-week', NOW, util()) == (None, None)


def test_every_token_resolves():
    """A preset cannot be added without giving it a meaning."""
    for token in DATE_PRESETS:
        since, _until = resolve_preset(token, NOW, util())
        assert since is not None or token == DATE_PRESET_ALL


def test_resolve_returns_dates_not_datetimes():
    """Bounds are compared against parse_date(), which returns date objects.

    A datetime here raises TypeError inside matches() the moment a --since
    search runs, which unit tests asserting 'is not None' never noticed.
    """
    from datetime import date
    for token in DATE_PRESETS:
        since, until = resolve_preset(token, NOW, util())
        for value in (since, until):
            if value is not None:
                assert type(value) is date, f'{token} produced {type(value)}'


def test_a_preset_query_actually_filters():
    """The end to end check the type test exists to protect."""
    query = DocumentQuery(date_mode=DATE_RANGE, date_preset='last-12-months')
    query.date_since, query.date_until = resolve_preset(
        'last-12-months', NOW, util())
    recent = item(date='20260601')
    old = item(date='20200101')
    assert query.matches(recent) is True
    assert query.matches(old) is False


def test_only_ids_restricts_the_view_to_an_explicit_list():
    """Putting a list somebody already worked out in front of the user.

    A health check names the documents it found; the view has to be able to
    show exactly those, whatever the dropdowns say.
    """
    wanted = item(id='a.pdf')
    unwanted = item(id='b.pdf')
    query = DocumentQuery(only_ids=frozenset({'a.pdf'}),
                          ignore_date=True, ignore_active=True)
    assert query.matches(wanted) is True
    assert query.matches(unwanted) is False


def test_no_restriction_is_not_the_same_as_an_empty_one():
    """None means every document; an empty set means none, and both are real."""
    document = item(id='a.pdf')
    assert DocumentQuery(ignore_date=True,
                         ignore_active=True).matches(document) is True
    assert DocumentQuery(only_ids=frozenset(), ignore_date=True,
                         ignore_active=True).matches(document) is False


def test_only_ids_still_obeys_the_other_filters():
    """It narrows the view, it does not override what else is being asked."""
    document = item(id='a.pdf', country='ES')
    query = DocumentQuery(only_ids=frozenset({'a.pdf'}), country='DE',
                          ignore_date=True, ignore_active=True)
    assert query.matches(document) is False
