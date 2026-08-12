# File: aggregate.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Pure aggregation for the insights page. No GTK, no file I/O, no
#              translation: callers pass the seven filename fields they already
#              parsed and get back the report model. Keeping the arithmetic here
#              makes it testable without a running application.

from collections import Counter
from datetime import datetime, timedelta

# Seven-field filename scheme: date-country-group-sentby-purpose-concept-sentto
FIELD_DATE = 0
FIELD_COUNTRY = 1
FIELD_GROUP = 2
FIELD_SENTBY = 3
FIELD_PURPOSE = 4
FIELD_CONCEPT = 5
FIELD_SENTTO = 6

# Counter name -> field position. The report ranks the first three and only
# counts distinct values for the rest.
COUNTED = (
    ('sender', FIELD_SENTBY),
    ('purpose', FIELD_PURPOSE),
    ('concept', FIELD_CONCEPT),
    ('group', FIELD_GROUP),
    ('country', FIELD_COUNTRY),
    ('sentto', FIELD_SENTTO),
)

TOP_N = 12


def month_index(date):
    """Return the 0-based month of a YYYYMMDD string, or None if unusable."""
    if not date or len(date) != 8 or not date.isdigit():
        return None
    month = int(date[4:6])
    if not 1 <= month <= 12:
        return None
    return month - 1


MONTHLY_BUCKETS_UP_TO = 24


def _empty_block():
    counters = {name: Counter() for name, _pos in COUNTED}
    counters.update({
        'total': 0,
        'first': '',
        'last': '',
        # Who sent the earliest and the latest document of the block. The
        # milestones block names them, and nothing else needs a second pass.
        'first_sender': '',
        'last_sender': '',
    })
    return counters


def _empty_year():
    block = _empty_block()
    block['months'] = [0] * 12
    return block


def _count(block, fields, date):
    """Add one record to a block. The caller has validated the date."""
    block['total'] += 1
    if not block['first'] or date < block['first']:
        block['first'] = date
        block['first_sender'] = fields[FIELD_SENTBY]
    if date > block['last']:
        block['last'] = date
        block['last_sender'] = fields[FIELD_SENTBY]
    for name, position in COUNTED:
        value = fields[position]
        if value:
            block[name][value] += 1


def build_stats(records):
    """Aggregate filename field sequences into {year: stats}.

    Records with fewer than seven fields or an unusable date are skipped, so the
    caller can hand over everything it finds without pre-filtering.
    """
    years = {}
    for fields in records:
        if len(fields) < 7:
            continue
        date = fields[FIELD_DATE]
        month = month_index(date)
        if month is None:
            continue

        year = date[:4]
        stats = years.get(year)
        if stats is None:
            stats = _empty_year()
            years[year] = stats

        stats['months'][month] += 1
        _count(stats, fields, date)
    return years


def month_span(start, end):
    """How many calendar months the inclusive range covers."""
    return ((int(end[:4]) * 12 + int(end[4:6])) -
            (int(start[:4]) * 12 + int(start[4:6])) + 1)


def bucket_keys(start, end):
    """Timeline buckets for a range: (keys, unit).

    Up to two years the timeline is monthly ("YYYYMM"), beyond that yearly
    ("YYYY"), so a ten year window does not turn into 120 columns.
    """
    span = month_span(start, end)
    if span <= MONTHLY_BUCKETS_UP_TO:
        keys = []
        year, month = int(start[:4]), int(start[4:6])
        for _step in range(span):
            keys.append(f"{year:04d}{month:02d}")
            month += 1
            if month > 12:
                month, year = 1, year + 1
        return keys, 'month'
    return [str(year) for year in range(int(start[:4]), int(end[:4]) + 1)], 'year'


def build_range_stats(records, start, end):
    """Aggregate every record dated within the inclusive [start, end] range.

    Same shape as one year of build_stats, with a `buckets` timeline instead of
    the twelve fixed months.
    """
    keys, unit = bucket_keys(start, end)
    block = _empty_block()
    block['unit'] = unit
    block['buckets'] = [{'key': key, 'count': 0} for key in keys]
    index = {entry['key']: entry for entry in block['buckets']}

    for fields in records:
        if len(fields) < 7:
            continue
        date = fields[FIELD_DATE]
        if month_index(date) is None or not start <= date <= end:
            continue
        entry = index.get(date[:6] if unit == 'month' else date[:4])
        if entry is not None:
            entry['count'] += 1
        _count(block, fields, date)
    return block


def year_delta(total, previous_total):
    """Year over year change, or None when there is no comparable prior year."""
    if not previous_total:
        return None
    diff = total - previous_total
    return {'diff': diff, 'pct': diff / previous_total * 100.0}


def busiest_month(months):
    """(index, count) of the fullest month, or (None, 0) for an empty year."""
    best = max(range(12), key=lambda i: months[i]) if any(months) else None
    return best, (months[best] if best is not None else 0)


def active_months(months):
    return sum(1 for count in months if count > 0)


def busiest_bucket(buckets):
    """(bucket, count) of the fullest timeline bucket, or (None, 0)."""
    filled = [entry for entry in buckets if entry['count']]
    if not filled:
        return None, 0
    best = max(filled, key=lambda entry: entry['count'])
    return best, best['count']


def active_buckets(buckets):
    return sum(1 for entry in buckets if entry['count'])


def previous_window(start, end):
    """The window of the same length ending the day before `start`.

    Used to say whether a period holds more or fewer documents than the stretch
    right before it.
    """
    first = datetime.strptime(start, '%Y%m%d')
    last = datetime.strptime(end, '%Y%m%d')
    if last < first:
        return start, end
    previous_end = first - timedelta(days=1)
    previous_start = previous_end - (last - first)
    return previous_start.strftime('%Y%m%d'), previous_end.strftime('%Y%m%d')


def longest_streak(years):
    """Longest run of consecutive months holding at least one document.

    The run crosses year boundaries: December 2024 and January 2025 count as
    consecutive. Returns {'months', 'start', 'end'} with start and end as
    (year, month_index) pairs, or None when nothing is active.
    """
    if not years:
        return None
    ordered = sorted(int(year) for year in years)
    best = current = 0
    best_end = current_end = None
    for year in range(ordered[0], ordered[-1] + 1):
        months = years.get(str(year), {}).get('months', [0] * 12)
        for index in range(12):
            if months[index]:
                current += 1
                current_end = (str(year), index)
                if current > best:
                    best, best_end = current, current_end
            else:
                current = 0
    if not best:
        return None
    end_year, end_month = best_end
    absolute_end = int(end_year) * 12 + end_month
    absolute_start = absolute_end - best + 1
    return {
        'months': best,
        'start': (str(absolute_start // 12), absolute_start % 12),
        'end': (end_year, end_month),
    }


def first_seen(years, counter_name):
    """{value: earliest year it appears in} for one counter."""
    earliest = {}
    for year in sorted(years):
        for value in years[year][counter_name]:
            if value not in earliest:
                earliest[value] = year
    return earliest


def new_in_year(years, year, counter_name):
    """Values appearing in `year` that never appeared in an earlier year."""
    earliest = first_seen(years, counter_name)
    return sorted(value for value, first in earliest.items() if first == year)


def lifetime_counter(years, counter_name):
    total = Counter()
    for stats in years.values():
        total.update(stats[counter_name])
    return total


def _ranks(counter):
    """{value: 1-based rank} ordered by count, ties broken by value."""
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return {value: position for position, (value, _count) in enumerate(ordered, 1)}


def rank_movers(years, counter_name, top_n=TOP_N):
    """All time leaders with how their rank moved in the most recent year.

    Movement compares the latest year against the one before it:
      new       present in the latest year only
      up/down   ranked in both, position improved or worsened
      same      ranked in both at the same position
      gone      ranked before, absent from the latest year
    """
    if not years:
        return []
    ordered_years = sorted(years, reverse=True)
    latest = ordered_years[0]
    previous = ordered_years[1] if len(ordered_years) > 1 else None

    lifetime = lifetime_counter(years, counter_name)
    latest_ranks = _ranks(years[latest][counter_name])
    previous_ranks = _ranks(years[previous][counter_name]) if previous else {}

    movers = []
    for value, count in lifetime.most_common(top_n):
        current = latest_ranks.get(value)
        before = previous_ranks.get(value)
        if current is None:
            movement = 'gone'
        elif before is None:
            movement = 'new'
        elif current < before:
            movement = 'up'
        elif current > before:
            movement = 'down'
        else:
            movement = 'same'
        movers.append({
            'value': value,
            'total': count,
            'rank': current,
            'previous_rank': before,
            'movement': movement,
        })
    return movers


def milestones(years):
    """Archive-wide facts: span, extremes and the longest active streak."""
    if not years:
        return {}
    ordered = sorted(years)
    totals = {year: years[year]['total'] for year in ordered}
    busiest = max(totals, key=lambda year: (totals[year], year))
    quietest = min(totals, key=lambda year: (totals[year], year))
    latest = ordered[-1]
    return {
        'first_date': years[ordered[0]]['first'],
        'last_date': years[latest]['last'],
        'busiest_year': {'year': busiest, 'total': totals[busiest]},
        'quietest_year': {'year': quietest, 'total': totals[quietest]},
        'streak': longest_streak(years),
        'latest_year': latest,
    }


def gone_quiet(years, counter_name='sender'):
    """Values present in the year before the latest one but not in the latest.

    Comparing against the whole archive instead would list every sender that
    ever wrote once, which says nothing. One year back is the signal: they were
    around, now they are not.
    """
    if len(years) < 2:
        return []
    ordered = sorted(years, reverse=True)
    latest, previous = ordered[0], ordered[1]
    return sorted(set(years[previous][counter_name]) - set(years[latest][counter_name]))
