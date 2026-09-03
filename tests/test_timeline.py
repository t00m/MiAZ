#!/usr/bin/python3

"""Timeline layout logic: party split, gaps and year separators."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from MiAZ.frontend.desktop.widgets.timelineview import (
    GAP_MONTHS, months_between, timeline_marks, two_party_split)


def test_two_parties_split_left_and_right():
    pairs = [('ACME', 'JOHNDOE'), ('JOHNDOE', 'ACME'), ('ACME', 'JOHNDOE')]
    assert two_party_split(pairs) == ('ACME', 'JOHNDOE')


def test_more_than_two_parties_is_single_sided():
    pairs = [('ACME', 'JOHNDOE'), ('BANKX', 'JOHNDOE')]
    assert two_party_split(pairs) is None


def test_empty_set_is_single_sided():
    assert two_party_split([]) is None


def test_months_between():
    assert months_between('20250110', '20250225') == 1
    assert months_between('20250110', '20250120') == 0
    assert months_between('20241201', '20260101') == 13
    assert months_between('bogus', '20250110') == 0


def test_first_card_gets_a_year_and_no_gap():
    assert timeline_marks(None, '20260612') == ('2026', None)


def test_close_dates_in_one_year_get_no_marks():
    assert timeline_marks('20260505', '20260612') == (None, None)


def test_long_stretch_gets_a_gap_marker():
    year, gap = timeline_marks('20250910', '20260612')
    assert year == '2026'
    assert gap == 9
    assert gap >= GAP_MONTHS


def test_unknown_date_never_makes_a_gap():
    year, gap = timeline_marks('20240101', '99991231')
    assert gap is None
