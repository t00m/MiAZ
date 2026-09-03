# File: iban.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: IBAN checksum and display, no GTK and no MiAZ imports

import re

# Length per country, from the IBAN registry. A country that is not here is
# still checked for shape and checksum, which catches most typing mistakes.
LENGTHS = {
    'AD': 24, 'AE': 23, 'AL': 28, 'AT': 20, 'AZ': 28, 'BA': 20, 'BE': 16,
    'BG': 22, 'BH': 22, 'BR': 29, 'BY': 28, 'CH': 21, 'CR': 22, 'CY': 28,
    'CZ': 24, 'DE': 22, 'DK': 18, 'DO': 28, 'EE': 20, 'EG': 29, 'ES': 24,
    'FI': 18, 'FO': 18, 'FR': 27, 'GB': 22, 'GE': 22, 'GI': 23, 'GL': 18,
    'GR': 27, 'GT': 28, 'HR': 21, 'HU': 28, 'IE': 22, 'IL': 23, 'IS': 26,
    'IT': 27, 'JO': 30, 'KW': 30, 'KZ': 20, 'LB': 28, 'LC': 32, 'LI': 21,
    'LT': 20, 'LU': 20, 'LV': 21, 'LY': 25, 'MC': 27, 'MD': 24, 'ME': 22,
    'MK': 19, 'MR': 27, 'MT': 31, 'MU': 30, 'NL': 18, 'NO': 15, 'PK': 24,
    'PL': 28, 'PS': 29, 'PT': 25, 'QA': 29, 'RO': 24, 'RS': 22, 'SA': 24,
    'SC': 31, 'SE': 24, 'SI': 19, 'SK': 24, 'SM': 27, 'ST': 25, 'SV': 28,
    'TL': 23, 'TN': 24, 'TR': 26, 'UA': 29, 'VA': 22, 'VG': 24, 'XK': 20,
}

# What an IBAN may be made of, and the two letters plus two digits it opens with.
SHAPE = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]+$')


def normalise(value):
    """The IBAN as it is compared: no spaces, no dashes, upper case."""
    return re.sub(r'[\s-]', '', str(value or '')).upper()


def is_valid(value):
    """True when the shape, the length and the mod 97 checksum all hold."""
    account = normalise(value)
    if not 15 <= len(account) <= 34 or not SHAPE.match(account):
        return False
    expected = LENGTHS.get(account[:2])
    if expected is not None and len(account) != expected:
        return False
    rotated = account[4:] + account[:4]
    digits = ''.join(str(int(char, 36)) for char in rotated)
    return int(digits) % 97 == 1


def display(value):
    """The IBAN in groups of four, the way it is printed on a statement."""
    account = normalise(value)
    return ' '.join(account[index:index + 4] for index in range(0, len(account), 4))
