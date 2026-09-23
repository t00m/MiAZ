#!/usr/bin/python3

"""What the MiAZOikos core does: amounts, the ledger and the totals.

The `oikos` package lives under the plugin directory, which is not on the
default path, so the test inserts it the way the plugin does at runtime.
"""

import json
import os
import sys
from decimal import Decimal

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZOikos')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


# Amounts

@pytest.mark.parametrize('text, expected', [
    ('1234.50', '1234.50'),
    ('1234,50', '1234.50'),
    ('1.234,50', '1234.50'),
    ('1,234.50', '1234.50'),
    ('1.234.567', '1234567'),
    ('1,234,567.8', '1234567.8'),
    ("1'234.50", '1234.50'),
    (' 1 234,5 ', '1234.5'),
    ('+12', '12'),
    ('0', '0'),
    ('0,05', '0.05'),
])
def test_an_amount_is_read_whichever_separator_was_typed(text, expected):
    from oikos.money import parse_amount
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize('text', [
    '', '   ', 'abc', '12a', '-5', '−12', '1.2.3,4,5', '12,34.5',
    '1,23,456', '1.23456', 'NaN', 'Infinity', '1e5',
])
def test_what_is_not_an_amount_is_refused(text):
    from oikos.money import parse_amount
    with pytest.raises(ValueError):
        parse_amount(text)


def test_a_single_separator_is_always_the_decimal_one():
    """1,234 and 1.234 are one and a bit, not twelve hundred: one rule, both ways."""
    from oikos.money import parse_amount
    assert parse_amount('1,234') == Decimal('1.234')
    assert parse_amount('1.234') == Decimal('1.234')


def test_an_amount_is_formatted_in_the_separators_asked_for():
    from oikos.money import format_amount
    value = Decimal('1234567.5')
    assert format_amount(value, decimal_point='.', thousands_sep=',') == '1,234,567.50'
    assert format_amount(value, decimal_point=',', thousands_sep='.') == '1.234.567,50'
    assert format_amount(Decimal('-3'), decimal_point='.', thousands_sep=',') == '−3.00'
    assert format_amount(Decimal('3'), signed=True, decimal_point='.',
                         thousands_sep=',') == '+3.00'
    assert format_amount(Decimal('0'), signed=True, decimal_point='.',
                         thousands_sep=',') == '0.00'


def test_every_listed_currency_has_an_iso_shaped_code():
    from oikos.money import CURRENCIES, DEFAULT_CURRENCY, is_currency_code
    assert DEFAULT_CURRENCY in CURRENCIES
    assert all(is_currency_code(code) for code in CURRENCIES)
    assert not is_currency_code('eur')
    assert not is_currency_code('EURO')


# Entries

def test_an_entry_keeps_its_amount_exactly():
    from oikos.ledger import Entry
    entry = Entry('expense', '0.10', 'EUR')
    assert entry.amount == Decimal('0.10')
    assert entry.signed == Decimal('-0.10')
    assert Entry.from_json(entry.to_json()) == entry
    assert entry.to_json()['amount'] == '0.10', 'a string, never a float'


@pytest.mark.parametrize('kind, amount, currency', [
    ('gift', '1', 'EUR'),
    ('income', '-1', 'EUR'),
    ('income', '1', 'euro'),
    ('income', 'x', 'EUR'),
])
def test_an_entry_refuses_what_it_cannot_hold(kind, amount, currency):
    from oikos.ledger import Entry
    with pytest.raises(ValueError):
        Entry(kind, amount, currency)


# The ledger

@pytest.fixture
def ledger_path(tmp_path):
    return str(tmp_path / 'MiAZOikos.json')


def _saver(path, data):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)


def _ledger(path):
    from oikos.ledger import Ledger
    return Ledger(path, save=_saver)


def test_what_is_set_is_read_back_by_the_next_ledger(ledger_path):
    from oikos.ledger import Entry
    ledger = _ledger(ledger_path)
    assert len(ledger) == 0
    changed = ledger.set_many({
        'a.pdf': Entry('income', '800', 'EUR'),
        'b.pdf': Entry('expense', '19.99', 'USD'),
    })
    assert changed == 2
    again = _ledger(ledger_path)
    assert again.get('a.pdf') == Entry('income', '800', 'EUR')
    assert again.get('b.pdf').amount == Decimal('19.99')
    assert again.get('c.pdf') is None


def test_setting_the_same_entry_again_writes_nothing(ledger_path):
    from oikos.ledger import Entry
    ledger = _ledger(ledger_path)
    ledger.set('a.pdf', Entry('income', '800', 'EUR'))
    revision = ledger.revision
    assert ledger.set_many({'a.pdf': Entry('income', '800.00', 'EUR')}) == 0
    assert ledger.revision == revision


def test_an_entry_follows_its_document_when_renamed(ledger_path):
    from oikos.ledger import Entry
    ledger = _ledger(ledger_path)
    ledger.set('old.pdf', Entry('expense', '5', 'EUR'))
    assert ledger.rename('old.pdf', 'new.pdf')
    assert ledger.get('old.pdf') is None
    assert ledger.get('new.pdf') == Entry('expense', '5', 'EUR')
    assert not ledger.rename('missing.pdf', 'other.pdf')
    assert _ledger(ledger_path).get('new.pdf') is not None


def test_clear_forgets_documents(ledger_path):
    from oikos.ledger import Entry
    ledger = _ledger(ledger_path)
    ledger.set_many({name: Entry('income', '1', 'EUR')
                     for name in ('a.pdf', 'b.pdf')})
    assert ledger.clear(['a.pdf', 'zzz.pdf']) == 1
    assert ledger.clear(['zzz.pdf']) == 0
    assert list(_ledger(ledger_path).documents()) == ['b.pdf']


def test_one_bad_entry_does_not_cost_the_others(ledger_path):
    with open(ledger_path, 'w', encoding='utf-8') as handle:
        json.dump({'format': 1, 'documents': {
            'good.pdf': {'kind': 'income', 'amount': '10', 'currency': 'EUR'},
            'bad.pdf': {'kind': 'income', 'amount': 'lots', 'currency': 'EUR'},
            'worse.pdf': 'not even a dict',
        }}, handle)
    ledger = _ledger(ledger_path)
    assert list(ledger.documents()) == ['good.pdf']


def test_an_unreadable_file_gives_an_empty_ledger(ledger_path):
    with open(ledger_path, 'w', encoding='utf-8') as handle:
        handle.write('{ this is not json')
    assert len(_ledger(ledger_path)) == 0


# Totals

def test_totals_add_up_exactly_and_per_currency():
    from oikos.aggregate import summarize
    from oikos.ledger import Entry
    entries = [Entry('income', '0.1', 'EUR'), Entry('income', '0.2', 'EUR'),
               Entry('expense', '0.3', 'EUR'), Entry('expense', '10', 'USD')]
    totals = summarize(entries)
    assert list(totals) == ['EUR', 'USD'], 'currencies are never mixed'
    assert totals['EUR'].income == Decimal('0.3')
    assert totals['EUR'].net == Decimal('0')
    assert totals['EUR'].count == 3
    assert totals['USD'].expense == Decimal('10')
    assert totals['USD'].net == Decimal('-10')
    assert summarize([]) == {}


def test_dates_fall_in_their_year_or_month():
    from oikos.aggregate import GROUP_MONTH, GROUP_YEAR, date_key
    assert date_key('20240315', GROUP_MONTH) == '2024-03'
    assert date_key('20240315', GROUP_YEAR) == '2024'
    assert date_key('99991231', GROUP_MONTH) is None
    assert date_key('', GROUP_YEAR) is None
    assert date_key('someday', GROUP_YEAR) is None


def test_a_breakdown_by_month_is_chronological_with_unknown_last():
    from oikos.aggregate import GROUP_MONTH, breakdown
    from oikos.ledger import Entry
    pairs = [
        ('2024-03', '2024-03', Entry('income', '5', 'EUR')),
        (None, None, Entry('expense', '1', 'EUR')),
        ('2024-01', '2024-01', Entry('expense', '7', 'EUR')),
        ('2024-03', '2024-03', Entry('expense', '2', 'EUR')),
    ]
    rows = breakdown(pairs, GROUP_MONTH, unknown_label='Unknown')['EUR']
    assert [row.label for row in rows] == ['2024-01', '2024-03', 'Unknown']
    assert rows[1].totals.income == Decimal('5')
    assert rows[1].totals.expense == Decimal('2')


def test_a_breakdown_by_field_puts_the_largest_first():
    from oikos.aggregate import GROUP_SENTBY, breakdown
    from oikos.ledger import Entry
    pairs = [
        ('SHOP', 'The Shop', Entry('expense', '10', 'EUR')),
        ('BANK', 'The Bank', Entry('income', '900', 'EUR')),
        ('SHOP', 'The Shop', Entry('expense', '15', 'EUR')),
        ('BANK', 'The Bank', Entry('expense', '3', 'USD')),
    ]
    result = breakdown(pairs, GROUP_SENTBY)
    assert [row.label for row in result['EUR']] == ['The Bank', 'The Shop']
    assert result['EUR'][1].totals.expense == Decimal('25')
    assert [row.key for row in result['USD']] == ['BANK']
