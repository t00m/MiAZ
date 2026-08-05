#!/usr/bin/python3

"""
Regression guard for the MiAZInsights plugin.

The `insights` package lives under the plugin directory, which is not on the
default path, so the test inserts it the same way the plugin does at runtime.
Both modules are pure Python: no GTK, no application services, no file I/O.
"""

import json
import os
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZInsights')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def record(date, sentby='BANK', purpose='INV', concept='rent',
           country='ES', group='HOU', sentto='JOHN'):
    return [date, country, group, sentby, purpose, concept, sentto]


# Aggregation

def test_build_stats_counts_per_year_and_month():
    from insights.aggregate import build_stats
    years = build_stats([
        record('20240115'), record('20240220'), record('20250301'),
    ])
    assert set(years) == {'2024', '2025'}
    assert years['2024']['total'] == 2
    assert years['2024']['months'][0] == 1
    assert years['2024']['months'][1] == 1
    assert years['2025']['months'][2] == 1


def test_build_stats_skips_unusable_records():
    from insights.aggregate import build_stats
    years = build_stats([
        record('20240115'),
        ['20240115', 'ES', 'HOU'],          # too few fields
        record('2024'),                     # short date
        record('2024AB15'),                 # not digits
        record('20241315'),                 # month out of range
    ])
    assert list(years) == ['2024']
    assert years['2024']['total'] == 1


def test_build_stats_tracks_span_and_its_senders():
    from insights.aggregate import build_stats
    years = build_stats([
        record('20240620', sentby='MIDDLE'),
        record('20240115', sentby='FIRST'),
        record('20241231', sentby='LAST'),
    ])
    stats = years['2024']
    assert stats['first'] == '20240115'
    assert stats['last'] == '20241231'
    assert stats['first_sender'] == 'FIRST'
    assert stats['last_sender'] == 'LAST'


def test_month_index():
    from insights.aggregate import month_index
    assert month_index('20240101') == 0
    assert month_index('20241231') == 11
    assert month_index('20240001') is None
    assert month_index('') is None
    assert month_index('2024-01-01') is None


# Derived figures

def test_year_delta():
    from insights.aggregate import year_delta
    assert year_delta(150, 100) == {'diff': 50, 'pct': 50.0}
    assert year_delta(50, 100) == {'diff': -50, 'pct': -50.0}
    assert year_delta(10, 0) is None


def test_busiest_and_active_months():
    from insights.aggregate import active_months, busiest_month
    months = [0, 3, 0, 7, 0, 0, 0, 0, 0, 0, 0, 1]
    assert busiest_month(months) == (3, 7)
    assert active_months(months) == 3
    assert busiest_month([0] * 12) == (None, 0)


def test_longest_streak_crosses_the_year_boundary():
    from insights.aggregate import build_stats, longest_streak
    years = build_stats([
        record('20241105'), record('20241205'),
        record('20250105'), record('20250205'),
        record('20250805'),                       # isolated, breaks the run
    ])
    streak = longest_streak(years)
    assert streak['months'] == 4
    assert streak['start'] == ('2024', 10)
    assert streak['end'] == ('2025', 1)


def test_longest_streak_ignores_empty_years_in_between():
    from insights.aggregate import build_stats, longest_streak
    years = build_stats([record('20200105'), record('20230105')])
    assert longest_streak(years)['months'] == 1


def test_longest_streak_without_data():
    from insights.aggregate import longest_streak
    assert longest_streak({}) is None


def test_first_seen_and_new_in_year():
    from insights.aggregate import build_stats, first_seen, new_in_year
    years = build_stats([
        record('20240101', sentby='OLD'),
        record('20250101', sentby='OLD'),
        record('20250201', sentby='FRESH'),
    ])
    assert first_seen(years, 'sender') == {'OLD': '2024', 'FRESH': '2025'}
    assert new_in_year(years, '2025', 'sender') == ['FRESH']
    assert new_in_year(years, '2024', 'sender') == ['OLD']


def test_rank_movers_classifies_movement():
    from insights.aggregate import build_stats, rank_movers
    records = []
    # 2024: A leads with 3, B has 2, GONE has 1
    records += [record('20240101', sentby='A')] * 3
    records += [record('20240101', sentby='B')] * 2
    records += [record('20240101', sentby='GONE')]
    # 2025: B leads with 5, A drops to 1, FRESH appears with 2
    records += [record('20250101', sentby='B')] * 5
    records += [record('20250101', sentby='A')]
    records += [record('20250101', sentby='FRESH')] * 2

    movement = {item['value']: item['movement'] for item in rank_movers(build_stats(records), 'sender')}
    assert movement == {'B': 'up', 'A': 'down', 'FRESH': 'new', 'GONE': 'gone'}


def test_rank_movers_single_year_marks_everything_new():
    from insights.aggregate import build_stats, rank_movers
    years = build_stats([record('20250101', sentby='ONLY')])
    assert rank_movers(years, 'sender')[0]['movement'] == 'new'


def test_gone_quiet_lists_senders_missing_from_the_latest_year():
    from insights.aggregate import build_stats, gone_quiet
    years = build_stats([
        record('20240101', sentby='LEFT'),
        record('20240101', sentby='STAYED'),
        record('20250101', sentby='STAYED'),
    ])
    assert gone_quiet(years) == ['LEFT']


def test_gone_quiet_only_looks_one_year_back():
    from insights.aggregate import build_stats, gone_quiet
    years = build_stats([
        record('20230101', sentby='ANCIENT'),
        record('20240101', sentby='RECENT'),
        record('20250101', sentby='STAYED'),
    ])
    # ANCIENT stopped writing before the year being compared against, so it is
    # not news any more.
    assert gone_quiet(years) == ['RECENT']


def test_milestones():
    from insights.aggregate import build_stats, milestones
    years = build_stats([
        record('20240115'), record('20240220'), record('20250301'),
    ])
    facts = milestones(years)
    assert facts['first_date'] == '20240115'
    assert facts['last_date'] == '20250301'
    assert facts['busiest_year'] == {'year': '2024', 'total': 2}
    assert facts['quietest_year'] == {'year': '2025', 'total': 1}
    assert facts['latest_year'] == '2025'


# Ranges and periods

def test_bucket_keys_switch_from_months_to_years():
    from insights.aggregate import bucket_keys, month_span
    assert month_span('20250101', '20250301') == 3
    keys, unit = bucket_keys('20251101', '20260215')
    assert unit == 'month'
    assert keys == ['202511', '202512', '202601', '202602']
    keys, unit = bucket_keys('20200101', '20260805')
    assert unit == 'year'
    assert keys == ['2020', '2021', '2022', '2023', '2024', '2025', '2026']


def test_build_range_stats_counts_only_the_window():
    from insights.aggregate import build_range_stats
    block = build_range_stats([
        record('20241231', sentby='BEFORE'),
        record('20250115', sentby='INSIDE'),
        record('20250228', sentby='INSIDE'),
        record('20250301', sentby='AFTER'),
    ], '20250101', '20250228')
    assert block['total'] == 2
    assert set(block['sender']) == {'INSIDE'}
    assert block['unit'] == 'month'
    assert [entry['count'] for entry in block['buckets']] == [1, 1]
    assert block['first'] == '20250115'
    assert block['last'] == '20250228'


def test_build_range_stats_buckets_long_windows_by_year():
    from insights.aggregate import build_range_stats
    block = build_range_stats([record('20200105'), record('20230105'), record('20230210')],
                              '20200101', '20260805')
    assert block['unit'] == 'year'
    assert len(block['buckets']) == 7
    assert block['buckets'][0] == {'key': '2020', 'count': 1}
    assert block['buckets'][3] == {'key': '2023', 'count': 2}


def test_busiest_and_active_buckets():
    from insights.aggregate import active_buckets, busiest_bucket
    buckets = [{'key': '202501', 'count': 0}, {'key': '202502', 'count': 4},
               {'key': '202503', 'count': 1}]
    assert busiest_bucket(buckets) == ({'key': '202502', 'count': 4}, 4)
    assert active_buckets(buckets) == 2
    assert busiest_bucket([{'key': '202501', 'count': 0}]) == (None, 0)


def test_previous_window_is_the_same_length_right_before():
    from insights.aggregate import previous_window
    # Equal length in days, ending the day before the window starts: the second
    # quarter (91 days) is compared against the 91 days that precede it.
    assert previous_window('20250401', '20250630') == ('20241231', '20250331')
    assert previous_window('20250101', '20250101') == ('20241231', '20241231')


# Payload and page

SAMPLE_RECORDS = [
    record('20240115', sentby='BANK', purpose='INV', country='ES'),
    record('20240220', sentby='UTIL', purpose='BILL', country='ES'),
    record('20250301', sentby='BANK', purpose='INV', country='MX'),
    record('20250405', sentby='NEWONE', purpose='INV', country='ES'),
]

SAMPLE_NAMES = {'sender': {'BANK': 'My Bank', 'UTIL': 'Water Co'},
                'purpose': {'INV': 'Invoice', 'BILL': 'Bill'},
                'country': {'ES': 'Spain', 'MX': 'Mexico'}}


def sample_payload(periods=()):
    from insights.render import build_payload
    meta = {'repo': 'Test', 'app': 'MiAZ', 'version': '0.1', 'generated': 'now', 'locale': 'en_GB'}
    return build_payload(SAMPLE_RECORDS, SAMPLE_NAMES, meta, periods)


def test_payload_is_serialisable_and_ordered():
    payload = sample_payload()
    json.dumps(payload)
    assert [item['year'] for item in payload['years']] == ['2025', '2024']
    assert payload['overview']['total'] == 4
    assert payload['overview']['year_count'] == 2


def test_payload_resolves_display_names():
    payload = sample_payload()
    latest = payload['years'][0]
    assert latest['senders'][0]['label'] in ('My Bank', 'NEWONE')
    assert latest['leading_purpose'] == 'Invoice'
    assert 'NEWONE' in latest['new_senders']
    assert 'Water Co' in payload['overview']['quiet_senders']


def test_payload_folds_the_purpose_tail_into_other():
    from insights.render import build_payload
    records = [record('20250101', purpose='TOP')] * 10
    for index in range(18):
        records.append(record('20250101', purpose=f"P{index:02d}"))
    payload = build_payload(records, {}, {'repo': 'Test'})
    purposes = payload['years'][0]['purposes']
    assert len(purposes) == 16                      # 15 ranked plus "Other"
    assert purposes[0]['label'] == 'TOP'
    assert purposes[-1]['count'] == 4               # the 4 purposes past the cap
    assert sum(row['count'] for row in purposes) == 28


def test_payload_new_this_year_covers_senders_and_purposes():
    from insights.render import build_payload
    payload = build_payload([
        record('20240101', sentby='OLD', purpose='INV'),
        record('20250101', sentby='OLD', purpose='INV'),
        record('20250201', sentby='FRESH', purpose='TAX'),
    ], {}, {'repo': 'Test'})
    latest = payload['years'][0]
    assert latest['new_senders'] == ['FRESH']
    assert latest['new_purposes'] == ['TAX']
    assert payload['years'][1]['new_purposes'] == ['INV']


def test_payload_period_block_matches_the_year_shape():
    payload = sample_payload([
        {'key': 'q1-2025', 'label': 'First quarter', 'start': '20250101', 'end': '20250331'},
    ])
    period = payload['periods'][0]
    year = payload['years'][0]
    assert period['kind'] == 'period'
    assert period['key'] == 'q1-2025'
    assert period['title'] == 'First quarter'
    assert period['total'] == 1                      # only the March document
    assert period['range'] == '2025-01-01 → 2025-03-31'
    assert period['unit'] == 'month'
    assert [entry['label'] for entry in period['timeline']] == ['Jan 25', 'Feb 25', 'Mar 25']
    # Both kinds feed the same view, so they carry the same keys.
    shared = {'total', 'timeline', 'unit', 'active', 'busiest_label', 'span', 'average',
              'distinct', 'senders', 'concepts', 'purposes', 'countries', 'delta'}
    assert shared <= set(period) and shared <= set(year)


def test_payload_year_timeline_is_twelve_labelled_months():
    payload = sample_payload()
    timeline = payload['years'][0]['timeline']
    assert len(timeline) == 12
    assert timeline[0] == {'label': 'Jan', 'full': 'Jan 2025', 'count': 0}
    assert timeline[2]['count'] == 1                 # 2025-03-01


def test_payload_carries_country_counts_for_the_map():
    payload = sample_payload()
    assert payload['overview']['countries'] == [
        {'code': 'ES', 'label': 'Spain', 'count': 3},
        {'code': 'MX', 'label': 'Mexico', 'count': 1},
    ]
    assert payload['years'][0]['countries'] == [
        {'code': 'ES', 'label': 'Spain', 'count': 1},
        {'code': 'MX', 'label': 'Mexico', 'count': 1},
    ]


def test_payload_without_documents():
    from insights.render import build_payload
    payload = build_payload([], {}, {'repo': 'Empty'})
    assert payload['years'] == []
    assert payload['periods'] == []
    assert payload['overview'] == {}
    assert payload['labels']['all_years']


def test_render_page_is_self_contained():
    from insights.render import render_page
    page = render_page(sample_payload(), 'body{color:red}', 'var x = 1;')
    assert page.startswith('<!DOCTYPE html>')
    assert 'body{color:red}' in page
    assert 'window.__MIAZ_REPORT__' in page
    assert 'src=' not in page          # nothing is fetched at load time
    assert '</script>' in page


def test_render_page_escapes_markup_in_the_payload():
    from insights.render import render_page
    payload = sample_payload()
    payload['meta']['repo'] = '</script><img src=x>'
    page = render_page(payload, '', '')
    assert '<img src=x>' not in page
