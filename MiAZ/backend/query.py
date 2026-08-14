
"""
# File: query.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The workspace filter, as a value instead of widget state
"""

import functools
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta
from typing import Optional

# Dropdown sentinels. They travel from the dropdown item ids straight into the
# query, so there is no second vocabulary to keep in sync.
ANY = 'Any'
NONE = 'None'

# Date filter modes. 'all' accepts every document, 'none' only the ones whose
# date cannot be parsed, 'range' the ones inside [date_since, date_until].
DATE_ALL = 'all'
DATE_NONE = 'none'
DATE_RANGE = 'range'

# Which sidebar date entry produced the range, as a stable token. The entries
# are relative to today ("this month") and their titles are translated, so
# neither the resolved dates nor the visible label can identify one later. A
# saved search stores the token, and the range is resolved again when it is
# applied: "this month" then means the month it is opened in.
DATE_PRESET_THIS_MONTH = 'this-month'
DATE_PRESET_PAST_MONTH = 'past-month'
DATE_PRESET_LAST_3_MONTHS = 'last-3-months'
DATE_PRESET_LAST_6_MONTHS = 'last-6-months'
DATE_PRESET_LAST_12_MONTHS = 'last-12-months'
DATE_PRESET_2_YEARS = '2-years'
DATE_PRESET_3_YEARS = '3-years'
DATE_PRESET_5_YEARS = '5-years'
DATE_PRESET_10_YEARS = '10-years'
DATE_PRESET_FUTURE = 'future'
DATE_PRESET_ALL = 'all-documents'

DATE_PRESETS = (
    DATE_PRESET_THIS_MONTH,
    DATE_PRESET_PAST_MONTH,
    DATE_PRESET_LAST_3_MONTHS,
    DATE_PRESET_LAST_6_MONTHS,
    DATE_PRESET_LAST_12_MONTHS,
    DATE_PRESET_2_YEARS,
    DATE_PRESET_3_YEARS,
    DATE_PRESET_5_YEARS,
    DATE_PRESET_10_YEARS,
    DATE_PRESET_FUTURE,
    DATE_PRESET_ALL,
)


@functools.lru_cache(maxsize=4096)
def parse_date(value: str):
    """Parse a filename date field. None when it is not a date."""
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


# How many months or years back each preset reaches. Kept as data so a new
# preset is one entry here and one token above, not a new branch.
_PRESET_MONTHS = {
    DATE_PRESET_PAST_MONTH: 1,
    DATE_PRESET_LAST_3_MONTHS: 3,
    DATE_PRESET_LAST_6_MONTHS: 6,
    DATE_PRESET_LAST_12_MONTHS: 12,
}
_PRESET_YEARS = {
    DATE_PRESET_2_YEARS: 2,
    DATE_PRESET_3_YEARS: 3,
    DATE_PRESET_5_YEARS: 5,
    DATE_PRESET_10_YEARS: 10,
}


def _as_date(value):
    """Bounds are compared against parse_date(), which returns date objects.

    The util helpers return datetime, and datetime cannot be compared with
    date, so everything leaving here is normalised.
    """
    return value.date() if isinstance(value, datetime) else value


def resolve_preset(token: str, now: datetime, util):
    """The date range a preset token means, resolved against `now`.

    This used to live in MiAZWorkspace, inside the loop that builds the sidebar
    entries, so anything else wanting the same answer had to copy the table.
    The labels stay in the widget, where they belong; the arithmetic lives here,
    next to the tokens it explains.

    Returns (since, until), or (None, None) for 'all documents' and for a token
    with no meaning. `util` is the MiAZUtil service, which owns the date
    helpers.
    """
    if token == DATE_PRESET_THIS_MONTH:
        since = util.since_date_this_month(now)
    elif token in _PRESET_MONTHS:
        since = util.since_date_last_n_months(now, _PRESET_MONTHS[token])
    elif token in _PRESET_YEARS:
        since = util.since_date_past_n_years_ago(now, _PRESET_YEARS[token])
    elif token == DATE_PRESET_FUTURE:
        return _as_date(now + timedelta(days=1)), _as_date(datetime(9999, 12, 31))
    else:
        return None, None
    return _as_date(since), _as_date(now)


@dataclass
class DocumentQuery:
    """What the workspace is currently showing.

    matches() is pure: it reads the item and this object, never a widget and
    never the app. That is what makes the filter testable, storable as a saved
    search, and settable by a plugin without walking dropdown models.
    """

    search: str = ''
    concept: str = ''
    country: str = ANY
    group: str = ANY
    sentby: str = ANY
    purpose: str = ANY
    sentto: str = ANY
    date_mode: str = DATE_ALL
    date_since: Optional[object] = None
    date_until: Optional[object] = None
    # Which sidebar entry the range came from, when it came from one. Carried so
    # the query can be written back to the sidebar and so a saved search can
    # re-resolve it. Filtering never reads it: date_mode and the bounds decide.
    date_preset: str = ''
    only_pending: bool = False
    # Lifted checks. A plugin filtering on its own membership (a project, say)
    # needs documents whose fields or dates the repository config does not
    # recognise, so it can switch off the two checks that would hide them.
    ignore_date: bool = False
    ignore_active: bool = False

    def matches(self, item) -> bool:
        """True when the document belongs in the current view."""
        active = True if self.ignore_active else item.active
        in_range = True if self.ignore_date else self._matches_date(item)

        conditions = (
            self._matches_search(item),
            self._matches_concept(item),
            _matches_value(self.country, item.country),
            _matches_value(self.group, item.group),
            _matches_value(self.sentby, item.sentby_id),
            _matches_value(self.purpose, item.purpose),
            _matches_value(self.sentto, item.sentto_id),
        )
        if not all(conditions):
            return False

        if self.only_pending:
            # Review lists what needs attention, whatever its date.
            return not active
        return active and in_range

    def _matches_search(self, item) -> bool:
        if not self.search:
            return True
        return self.search.upper() in item.search_text_upper

    def _matches_concept(self, item) -> bool:
        if not self.concept:
            return True
        return self.concept.upper() in item.subtitle.upper()

    def _matches_date(self, item) -> bool:
        if self.date_mode == DATE_ALL:
            return True
        item_date = parse_date(item.date)
        if self.date_mode == DATE_NONE:
            return item_date is None
        if item_date is None:
            return False
        return self.date_since <= item_date <= self.date_until

    def to_dict(self) -> dict:
        """Plain types only, so a saved search is JSON."""
        data = asdict(self)
        for key in ('date_since', 'date_until'):
            value = data[key]
            data[key] = value.strftime('%Y%m%d') if value is not None else None
        return data

    @classmethod
    def from_dict(cls, data: dict):
        """Rebuild a query, ignoring keys this version does not know."""
        known = {f.name for f in fields(cls)}
        values = {k: v for k, v in data.items() if k in known}
        for key in ('date_since', 'date_until'):
            if values.get(key):
                values[key] = parse_date(values[key])
        return cls(**values)


def _matches_value(selected: str, value: str) -> bool:
    """One dropdown against one field value."""
    if selected == ANY:
        return True
    if selected == NONE:
        return len(value) == 0
    return selected.upper() == value.upper()
