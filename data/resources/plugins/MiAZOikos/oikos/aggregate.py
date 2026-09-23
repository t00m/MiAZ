# File: aggregate.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Income and expense totals, by currency, no GTK

from dataclasses import dataclass, field
from decimal import Decimal

from oikos.money import INCOME

# Documents filed without a known date carry this one (MiAZ.backend.util).
UNKNOWN_DATE = '99991231'

# How the view can split the totals. 'total' is one row per currency.
GROUP_TOTAL = 'total'
GROUP_YEAR = 'year'
GROUP_MONTH = 'month'
GROUP_GROUP = 'group'
GROUP_SENTBY = 'sentby'
GROUP_PURPOSE = 'purpose'
GROUPINGS = (GROUP_TOTAL, GROUP_YEAR, GROUP_MONTH,
             GROUP_GROUP, GROUP_SENTBY, GROUP_PURPOSE)

# Groupings whose rows have a natural order (time). The others are sorted by
# how much money went through them, largest first.
CHRONOLOGICAL = (GROUP_YEAR, GROUP_MONTH)


@dataclass
class Totals:
    """What went in and what went out, in one currency."""
    income: Decimal = field(default_factory=Decimal)
    expense: Decimal = field(default_factory=Decimal)
    incomes: int = 0
    expenses: int = 0

    def add(self, entry):
        if entry.kind == INCOME:
            self.income += entry.amount
            self.incomes += 1
        else:
            self.expense += entry.amount
            self.expenses += 1

    @property
    def net(self) -> Decimal:
        return self.income - self.expense

    @property
    def count(self) -> int:
        return self.incomes + self.expenses

    @property
    def volume(self) -> Decimal:
        return self.income + self.expense


@dataclass
class Row:
    """One bar pair of the chart: a label and its totals."""
    key: str
    label: str
    totals: Totals


def summarize(entries) -> dict:
    """{currency: Totals} over the entries, currencies in code order.

    Currencies are never added together: that needs an exchange rate, and a
    total made with a guessed one is worse than two honest totals.
    """
    result = {}
    for entry in entries:
        result.setdefault(entry.currency, Totals()).add(entry)
    return dict(sorted(result.items()))


def date_key(date: str, grouping: str):
    """The year or month a filename date falls in, or None when unknown."""
    if not date or len(date) < 6 or not date[:6].isdigit() or date == UNKNOWN_DATE:
        return None
    if grouping == GROUP_YEAR:
        return date[:4]
    return f'{date[:4]}-{date[4:6]}'


def breakdown(pairs, grouping: str, unknown_label: str = '?') -> dict:
    """{currency: [Row]} from (key, label, Entry) triples.

    `key` is what the rows are grouped on; `label` is what the chart prints
    for it (a description rather than a code). A key of None collects under
    `unknown_label`, last.
    """
    rows = {}
    labels = {}
    for key, label, entry in pairs:
        per_currency = rows.setdefault(entry.currency, {})
        per_currency.setdefault(key, Totals()).add(entry)
        labels.setdefault(key, label if key is not None else unknown_label)

    def order(item):
        key, totals = item
        if grouping in CHRONOLOGICAL:
            return (key is None, key or '')
        return (key is None, -totals.volume, labels[key].casefold())

    result = {}
    for currency in sorted(rows):
        items = sorted(rows[currency].items(), key=order)
        result[currency] = [Row(key=key or '', label=labels[key], totals=totals)
                            for key, totals in items]
    return result
