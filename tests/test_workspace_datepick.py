#!/usr/bin/python3

"""
Unit tests for pick_date_preset, the pure date-filter chooser in the workspace.

Importing the workspace module needs the gi versions set (it imports GTK/Adw/
WebKit), but the function under test is pure: it takes preset ranges and document
dates and returns an index, with no GTK objects involved.
"""

from datetime import date

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
gi.require_version('WebKit', '6.0')

from MiAZ.frontend.desktop.widgets.workspace import pick_date_preset


def _presets():
    """Preset ranges as built for a 'today' of 2026-08-02, in dropdown order:
    the nested bounded chain (all ending today), then Future, then All."""
    today = date(2026, 8, 2)
    return [
        ('bounded', date(2026, 8, 1), today),   # 0 This month
        ('bounded', date(2026, 7, 1), today),   # 1 Since past month
        ('bounded', date(2026, 5, 1), today),   # 2 Since last 3 months
        ('bounded', date(2026, 2, 1), today),   # 3 Since last 6 months
        ('bounded', date(2026, 1, 1), today),   # 4 Since last year
        ('future',  date(2026, 8, 3), date(9999, 12, 31)),  # 5 Future
        ('all', None, None),                    # 6 All documents
    ]


def test_this_month_has_documents_is_kept():
    assert pick_date_preset(0, [date(2026, 8, 2)], _presets()) == 0


def test_only_last_month_picks_since_past_month():
    # The month-change case: nothing this month, newest doc is last month.
    assert pick_date_preset(0, [date(2026, 7, 15), date(2026, 6, 10)], _presets()) == 1


def test_two_months_ago_picks_three_month_window():
    # June is before "Since past month" (starts Jul 1), so the 3-month window wins.
    assert pick_date_preset(0, [date(2026, 6, 10)], _presets()) == 2


def test_empty_repository_keeps_current():
    assert pick_date_preset(0, [], _presets()) == 0


def test_future_only_falls_back_to_all():
    # Future is skipped, so a future-dated document falls back to All documents.
    assert pick_date_preset(0, [date(2026, 12, 25)], _presets()) == 6


def test_current_wide_and_nonempty_is_kept():
    # User already on the 3-month window with a matching document: leave it.
    assert pick_date_preset(2, [date(2026, 6, 10)], _presets()) == 2


def test_current_wide_but_empty_escalates_wider_only():
    # Current 3-month window (from May 1) is empty; a January document is only in
    # the wider "Since last year" window (index 4). It must not narrow to index 0.
    assert pick_date_preset(2, [date(2026, 1, 15)], _presets()) == 4


def test_out_of_range_current_index_is_returned_unchanged():
    assert pick_date_preset(99, [date(2026, 8, 2)], _presets()) == 99
    assert pick_date_preset(0, [date(2026, 8, 2)], []) == 0
