# File: render.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Turns the aggregated model into the payload the page renders from
#              and into the page itself. Pure: no GTK, no application services.
#              The caller passes the display-name maps it read from the repo
#              configuration and the CSS/JS it read from disk.

import json
from gettext import gettext as _

from . import aggregate as agg

TOP_N = agg.TOP_N

# Translators: three-letter month abbreviations used in the insights charts.
MONTH_NAMES = [_('Jan'), _('Feb'), _('Mar'), _('Apr'), _('May'), _('Jun'),
               _('Jul'), _('Aug'), _('Sep'), _('Oct'), _('Nov'), _('Dec')]


def labels():
    """Every string the page renders, resolved once on the Python side."""
    return {
        'all_years': _('All years'),
        'appeared_in': _('First seen in {year}'),
        'busiest_month': _('Busiest month'),
        'busiest_year': _('Busiest year'),
        'change': _('Change'),
        'concepts': _('Concepts'),
        'countries': _('Countries'),
        'distinct_senders': _('Distinct senders'),
        'docs_in': _('{n} documents in {year}'),
        'docs_on': _('{name}: {n} documents'),
        'documents': _('Documents'),
        'documents_in': _('documents in {year}'),
        'documents_over': _('documents over {n} years'),
        'empty': _('No normalized documents to report yet.'),
        'first_document': _('First document'),
        'firsts': _('Firsts and lasts'),
        'groups': _('Groups'),
        'heatmap': _('Activity'),
        'heatmap_note': _('One cell per month, shaded by how many documents it holds. Click a year to open it.'),
        'latest_document': _('Latest document'),
        'leading_purpose': _('Leading purpose'),
        'less': _('Less'),
        'month': _('Month'),
        'more': _('More'),
        'movers': _('Rank movers'),
        'movers_note': _('All-time leaders, with how their rank moved in {year} against the year before.'),
        'mv_down': _('down to {to} from {from}'),
        'mv_gone': _('not this year'),
        'mv_new': _('new'),
        'mv_same': _('holds {rank}'),
        'mv_up': _('up to {to} from {from}'),
        'n_documents': _('{n} documents'),
        'n_months': _('{n} months'),
        'new_note': _('Senders and purposes with no appearance in any earlier year.'),
        'and_more': _('and {n} more'),
        'new_this_year': _('New this year'),
        'no_prior': _('no prior year'),
        'none': _('None'),
        'map_head': _('Where it comes from'),
        'map_note': _('Countries in this selection, shaded by how many documents came from each.'),
        'no_period': _('No period'),
        'no_year': _('No year'),
        'nothing_here': _('No documents in this selection.'),
        'per_year': _('Documents per year'),
        'per_year_note': _('Click a year to open it.'),
        'period': _('Period'),
        'rhythm_period': _('Rhythm of the period'),
        'rhythm_note_year': _('{avg} documents per active year across {active} active years, busiest {busy}.'),
        'vs_period': _('vs previous window'),
        'purposes': _('Purposes'),
        'purposes_head': _('Purposes'),
        'purposes_note': _('Ranked by document count: the filename scheme carries no amount.'),
        'quietest_year': _('Quietest year'),
        'rhythm': _('Rhythm of the year'),
        'rhythm_note': _('{avg} documents per active month across {active} active months, busiest {busy}.'),
        'senders': _('Senders'),
        'show_table': _('Show the numbers'),
        'silent_in': _('Silent in {year}'),
        'streak': _('Longest streak'),
        'title_all': _('Insights'),
        'top_note': _('The names behind the documents in this selection.'),
        'total': _('Total'),
        'vs_previous': _('Year over year'),
        'vs_year': _('vs {year}'),
        'who_and_what': _('Who and what'),
        'year': _('Year'),
    }


def _name(names, field, key):
    """Human name for a field value, falling back to the raw key."""
    return names.get(field, {}).get(key, key) or key


def _ranked(counter):
    """Counter items, most first, ties broken by key so rebuilds are stable."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def _rows(counter, names, field, top=None):
    items = _ranked(counter)
    return [{'label': _name(names, field, key), 'count': count}
            for key, count in (items[:top] if top else items)]


def _date(value):
    if not value or len(value) != 8:
        return ''
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _month_label(index, count):
    if index is None:
        return ''
    return f"{MONTH_NAMES[index]} ({count})"


def _purpose_rows(counter, names, top=15):
    """Purposes ranked, with the long tail of one-offs folded into "Other"."""
    ordered = _ranked(counter)
    rows = [{'label': _name(names, 'purpose', key), 'count': count} for key, count in ordered[:top]]
    tail = sum(count for _key, count in ordered[top:])
    if tail:
        # Marked muted so the aggregate bar does not compete with the ranked
        # ones it stands for.
        rows.append({'label': _('Other ({n} purposes)').format(n=len(ordered) - top),
                     'count': tail, 'muted': True})
    return rows


def _countries(counter, names):
    """Country counts keyed by ISO code, which is what the map paints."""
    return [{'code': code, 'label': _name(names, 'country', code), 'count': count}
            for code, count in _ranked(counter)]


def _month_timeline(year, months):
    return [{'label': MONTH_NAMES[index], 'full': f"{MONTH_NAMES[index]} {year}", 'count': count}
            for index, count in enumerate(months)]


def _bucket_timeline(buckets, unit):
    """Timeline entries for a period, labelled by month or by year."""
    entries = []
    for bucket in buckets:
        key = bucket['key']
        if unit == 'month':
            month = MONTH_NAMES[int(key[4:6]) - 1]
            entries.append({'label': f"{month} {key[2:4]}", 'full': f"{month} {key[:4]}",
                            'count': bucket['count']})
        else:
            entries.append({'label': key, 'full': key, 'count': bucket['count']})
    return entries


def _scope_common(block, names, timeline, unit, active, busiest_label):
    """The fields a year view and a period view share."""
    purposes = _purpose_rows(block['purpose'], names)
    return {
        'total': block['total'],
        'timeline': timeline,
        'unit': unit,
        'active': active,
        'busiest_label': busiest_label,
        'span': f"{_date(block['first'])} → {_date(block['last'])}" if block['first'] else '',
        'average': f"{block['total'] / active:.1f}" if active else '0',
        'distinct': {name: len(block[name]) for name, _pos in agg.COUNTED},
        'senders': _rows(block['sender'], names, 'sender', TOP_N),
        'concepts': _rows(block['concept'], names, 'concept', TOP_N),
        'purposes': purposes,
        'countries': _countries(block['country'], names),
        'leading_purpose': purposes[0]['label'] if purposes else '',
        'leading_count': purposes[0]['count'] if purposes else 0,
    }


def _period_payload(records, period, names):
    """One preset date window, aggregated the same way a year is."""
    start, end = period['start'], period['end']
    block = agg.build_range_stats(records, start, end)
    busiest, busiest_count = agg.busiest_bucket(block['buckets'])
    active = agg.active_buckets(block['buckets'])
    timeline = _bucket_timeline(block['buckets'], block['unit'])
    label = ''
    if busiest is not None:
        entry = next(item for item in timeline if item['count'] == busiest_count)
        label = f"{entry['full']} ({busiest_count})"

    previous_start, previous_end = agg.previous_window(start, end)
    previous = agg.build_range_stats(records, previous_start, previous_end)

    payload = {
        'kind': 'period',
        'key': period['key'],
        'title': period['label'],
        'range': f"{_date(start)} → {_date(end)}",
        'delta': agg.year_delta(block['total'], previous['total']),
        'previous': f"{_date(previous_start)} → {_date(previous_end)}",
    }
    payload.update(_scope_common(block, names, timeline, block['unit'], active, label))
    return payload


def _year_payload(year, years, names, first_sender_year, first_purpose_year):
    stats = years[year]
    previous = str(int(year) - 1)
    previous_stats = years.get(previous)
    busiest_index, busiest_count = agg.busiest_month(stats['months'])
    active = agg.active_months(stats['months'])

    # Concepts are close to unique per document, so "new concepts" would list
    # nearly every concept of the year. Purposes are a small vocabulary, which
    # makes a new one worth pointing at.
    new_senders = sorted(_name(names, 'sender', key) for key, first in first_sender_year.items()
                         if first == year and key in stats['sender'])
    new_purposes = sorted(_name(names, 'purpose', key) for key, first in first_purpose_year.items()
                          if first == year and key in stats['purpose'])

    payload = {
        'kind': 'year',
        'key': year,
        'title': year,
        'year': year,
        'delta': agg.year_delta(stats['total'], previous_stats['total'] if previous_stats else 0),
        'previous': previous if previous_stats else None,
        'new_senders': new_senders,
        'new_purposes': new_purposes,
    }
    payload.update(_scope_common(stats, names, _month_timeline(year, stats['months']),
                                 'month', active, _month_label(busiest_index, busiest_count)))
    return payload


def _overview_payload(years, names):
    ordered = sorted(years, reverse=True)
    totals = {year: years[year]['total'] for year in ordered}
    milestones = agg.milestones(years)
    latest = milestones.get('latest_year')

    trend = []
    for year in ordered:
        previous = years.get(str(int(year) - 1))
        trend.append({
            'year': year,
            'total': totals[year],
            'delta': agg.year_delta(totals[year], previous['total'] if previous else 0),
        })

    rows = [{'year': year, 'months': years[year]['months'], 'total': totals[year]} for year in ordered]
    peak = max((max(row['months']) for row in rows), default=0)

    movers = {}
    for field in ('sender', 'purpose'):
        movers[field] = [dict(item, label=_name(names, field, item['value']))
                         for item in agg.rank_movers(years, field)]

    streak = milestones.get('streak')
    if streak:
        start_year, start_month = streak['start']
        end_year, end_month = streak['end']
        streak = {
            'months': streak['months'],
            'range': f"{MONTH_NAMES[start_month]} {start_year} → {MONTH_NAMES[end_month]} {end_year}",
        }

    facts = {
        'first_date': _date(milestones.get('first_date', '')),
        'last_date': _date(milestones.get('last_date', '')),
        'first_label': _name(names, 'sender', years[sorted(years)[0]].get('first_sender', '')),
        'last_label': _name(names, 'sender', years[latest].get('last_sender', '')) if latest else '',
        'busiest_year': milestones.get('busiest_year'),
        'quietest_year': milestones.get('quietest_year'),
        'streak': streak,
        'latest_year': latest,
    }

    return {
        'total': sum(totals.values()),
        'year_count': len(years),
        'span': f"{facts['first_date']} → {facts['last_date']}",
        'distinct': {name: len(agg.lifetime_counter(years, name)) for name, _pos in agg.COUNTED},
        'trend': trend,
        'countries': _countries(agg.lifetime_counter(years, 'country'), names),
        'heatmap': {'rows': rows, 'max': peak},
        'movers': movers,
        'milestones': facts,
        'new_senders': sorted(_name(names, 'sender', key)
                              for key in agg.new_in_year(years, latest, 'sender')) if latest else [],
        'quiet_senders': sorted(_name(names, 'sender', key) for key in agg.gone_quiet(years)),
    }


def build_payload(records, names, meta, periods=()):
    """Everything the page needs, as a JSON-serialisable dict.

    records: seven-field sequences, one per normalized document
    names:   {'sender': {id: label}, 'purpose': {...}, ...} display-name maps
    meta:    repo name, app name, version, generated timestamp, locale
    periods: [{'key', 'label', 'start', 'end'}] preset date windows, in the
             order they should appear in the period selector
    """
    years = agg.build_stats(records)
    payload = {
        'meta': meta,
        'labels': labels(),
        'months': MONTH_NAMES,
        'years': [],
        'periods': [],
        'overview': {},
    }
    if not years:
        return payload

    first_sender_year = agg.first_seen(years, 'sender')
    first_purpose_year = agg.first_seen(years, 'purpose')
    payload['years'] = [_year_payload(year, years, names, first_sender_year, first_purpose_year)
                        for year in sorted(years, reverse=True)]
    payload['periods'] = [_period_payload(records, period, names) for period in periods]
    payload['overview'] = _overview_payload(years, names)
    return payload


def render_page(payload, css, js, worldmap=''):
    """The single self-contained page. CSS and JS are inlined by the caller."""
    # '<' is escaped inside the JSON so no value can close the script element.
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')
    meta = payload['meta']
    title = f"{_('Insights')} · {meta.get('repo', '')}"
    return f"""<!DOCTYPE html>
<html lang="{meta.get('lang', 'en')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape(title)}</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <div>
      <h1>{_escape(_('Insights'))} <span class="scope" id="scope"></span></h1>
      <div class="repo">{_escape(meta.get('repo', ''))}</div>
    </div>
    <div class="tools no-print">
      <button id="theme" type="button" title="{_escape(_('Switch light and dark'))}">◑</button>
      <button id="print" type="button">{_escape(_('Print'))}</button>
    </div>
  </header>
  <div class="scopebar no-print">
    <label class="field"><span>{_escape(_('Year'))}</span><select id="year"></select></label>
    <label class="field"><span>{_escape(_('Period'))}</span><select id="period"></select></label>
  </div>
  <main id="view"></main>
  <footer>
    <span>{_escape(meta.get('app', 'MiAZ'))} {_escape(meta.get('version', ''))}</span>
    <span>{_escape(_('Generated'))} {_escape(meta.get('generated', ''))}</span>
  </footer>
</div>
<div id="tip" role="status"></div>
<template id="worldmap">{worldmap}</template>
<script>window.__MIAZ_REPORT__ = {data};</script>
<script>
{js}
</script>
</body>
</html>
"""


def _escape(value):
    return (str(value).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))
