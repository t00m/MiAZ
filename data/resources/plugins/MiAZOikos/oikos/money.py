# File: money.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Amounts, kinds and currencies, no GTK and no MiAZ imports

import locale
import re
from decimal import Decimal, InvalidOperation
from gettext import gettext as _

# What a document is to the household. The amount is always positive; the
# kind says which way the money went.
INCOME = 'income'
EXPENSE = 'expense'
KINDS = (INCOME, EXPENSE)

# The currency a repository starts with, and the one used when the user has
# not chosen another.
DEFAULT_CURRENCY = 'EUR'

# Most currencies have two minor digits, a few have three. Four is enough for
# any of them, and more is almost certainly a typing mistake.
MAX_DECIMALS = 4

# Written into the plugin's default data the first time it runs; the user
# enables the ones they use in Repository Settings > Metadata. ISO 4217.
CURRENCIES = {
    'ARS': _('Argentine peso'),
    'AUD': _('Australian dollar'),
    'BGN': _('Bulgarian lev'),
    'BRL': _('Brazilian real'),
    'CAD': _('Canadian dollar'),
    'CHF': _('Swiss franc'),
    'CLP': _('Chilean peso'),
    'CNY': _('Chinese yuan'),
    'COP': _('Colombian peso'),
    'CZK': _('Czech koruna'),
    'DKK': _('Danish krone'),
    'EUR': _('Euro'),
    'GBP': _('Pound sterling'),
    'HKD': _('Hong Kong dollar'),
    'HUF': _('Hungarian forint'),
    'IDR': _('Indonesian rupiah'),
    'ILS': _('Israeli new shekel'),
    'INR': _('Indian rupee'),
    'ISK': _('Icelandic króna'),
    'JPY': _('Japanese yen'),
    'KRW': _('South Korean won'),
    'MAD': _('Moroccan dirham'),
    'MXN': _('Mexican peso'),
    'NOK': _('Norwegian krone'),
    'NZD': _('New Zealand dollar'),
    'PEN': _('Peruvian sol'),
    'PHP': _('Philippine peso'),
    'PLN': _('Polish złoty'),
    'RON': _('Romanian leu'),
    'SEK': _('Swedish krona'),
    'SGD': _('Singapore dollar'),
    'THB': _('Thai baht'),
    'TRY': _('Turkish lira'),
    'UAH': _('Ukrainian hryvnia'),
    'USD': _('US dollar'),
    'UYU': _('Uruguayan peso'),
    'ZAR': _('South African rand'),
}

_PLAIN = re.compile(r'^\d+(\.\d+)?$')
_GROUPED = re.compile(r'^\d{1,3}(,\d{3})+(\.\d+)?$')


def is_currency_code(code) -> bool:
    """Three capital letters, the shape of an ISO 4217 code."""
    return isinstance(code, str) and re.fullmatch(r'[A-Z]{3}', code) is not None


def parse_amount(text) -> Decimal:
    """The amount the user typed, as a Decimal. ValueError when it is not one.

    Both decimal separators are accepted, since the same person types
    1234,50 and 1234.50 depending on where the number came from:

    - one separator is the decimal separator, whichever it is: 1234,5 and
      1234.5 are the same amount;
    - with both, the last one is the decimal separator and the other groups
      thousands: 1.234,50 and 1,234.50 are the same amount;
    - one separator repeated only groups thousands: 1.234.567.

    Spaces, and the apostrophe some write between thousands, are ignored.
    A negative amount is refused: the kind says which way the money went.
    """
    if isinstance(text, Decimal):
        value = text
    else:
        cleaned = str(text).strip()
        for ignored in (' ', ' ', ' ', "'"):
            cleaned = cleaned.replace(ignored, '')
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        if cleaned.startswith('-') or cleaned.startswith('−'):
            raise ValueError('negative amount')
        cleaned = _normalise(cleaned)
        if not _PLAIN.match(cleaned) and not _GROUPED.match(cleaned):
            raise ValueError(f'not an amount: {text!r}')
        cleaned = cleaned.replace(',', '')
        try:
            value = Decimal(cleaned)
        except InvalidOperation as error:
            raise ValueError(f'not an amount: {text!r}') from error
    if not value.is_finite() or value < 0:
        raise ValueError(f'not an amount: {text!r}')
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and -exponent > MAX_DECIMALS:
        raise ValueError(f'more than {MAX_DECIMALS} decimals: {text!r}')
    return value


def _normalise(text: str) -> str:
    """Rewrite the separators so '.' is decimal and ',' groups thousands."""
    dots = text.count('.')
    commas = text.count(',')
    if dots and commas:
        if text.rfind(',') > text.rfind('.'):
            # 1.234,50: swap the two roles.
            return text.replace('.', '\x00').replace(',', '.').replace('\x00', ',')
        return text
    if commas == 1:
        return text.replace(',', '.')
    if dots > 1:
        return text.replace('.', ',')
    return text


def format_amount(value: Decimal, places: int = 2, signed: bool = False,
                  decimal_point: str = None, thousands_sep: str = None) -> str:
    """An amount as a person reads it, in the separators of their locale.

    GTK sets the process locale when it starts, so the numbers follow the
    desktop's regional format. Without it (tests, the command line) the C
    locale gives 1234.50.
    """
    if decimal_point is None or thousands_sep is None:
        conv = locale.localeconv()
        if decimal_point is None:
            decimal_point = conv.get('decimal_point') or '.'
        if thousands_sep is None:
            thousands_sep = conv.get('thousands_sep') or ''
    quantum = Decimal(1).scaleb(-places)
    rounded = abs(value).quantize(quantum)
    whole, _dot, fraction = f'{rounded:f}'.partition('.')
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    text = thousands_sep.join(groups)
    if fraction:
        text = f'{text}{decimal_point}{fraction}'
    if value < 0 and rounded != 0:
        text = f'−{text}'
    elif signed and rounded != 0:
        text = f'+{text}'
    return text


def format_money(value: Decimal, currency: str, signed: bool = False) -> str:
    """An amount with its currency code: 1,234.50 EUR."""
    return f'{format_amount(value, signed=signed)} {currency}'
