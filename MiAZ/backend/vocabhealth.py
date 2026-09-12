# File: vocabhealth.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: What is wrong with a repository's vocabulary. No GTK imports.
#              Not to be confused with vocabulary.py, which holds the
#              translatable labels for the shipped vocabularies.

"""Three questions about one filename field.

Which codes are used by no document, which codes documents use that the
vocabulary has never heard of, and which codes are described by nothing more
than themselves. No GTK and no services here, so it can be tested headless.
"""

# Where each vocabulary field sits in
# {date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
FIELD_POSITION = {
    'Country': 1,
    'Group': 2,
    'SentBy': 3,
    'Purpose': 4,
    'SentTo': 6,
}


def fields(filename):
    """The seven filename fields, following MiAZUtil.get_fields."""
    name = filename
    dot = name.rfind('.')
    if dot > 0:
        name = name[:dot]
    parts = name.split('-')
    if len(parts) > 7:
        parts[6] = '-'.join(parts[6:])
        parts = parts[:7]
    return parts


def count_codes(filenames, position):
    """How many documents use each code at that field position."""
    counts = {}
    for filename in filenames:
        parts = fields(filename)
        if len(parts) != 7:
            continue
        code = parts[position].strip()
        if code:
            counts[code] = counts.get(code, 0) + 1
    return counts


def _bare(text):
    """The text with the separators taken out, case kept."""
    return text.replace('_', '').replace('-', '').replace(' ', '').strip()


def is_unnamed(code, description):
    """True when the description tells the user nothing the code did not.

    An empty description, or one that is the code written out again, is the
    state a repository drifts into: values get added during a rename, when
    naming them properly is not what the user is doing.

    Case counts as a difference, and that is the whole subtlety. Codes are
    upper case by convention, so a description of "Health" for HEALTH is
    somebody typing a word, while "GENERALI" for GENERALI is not. Comparing
    case-insensitively flagged 234 documents worth of HEALTH as a problem and
    pushed the values that really say nothing down the list. Separators are
    ignored, so "TRV INS" describes TRV_INS no better than the code does.
    """
    text = (description or '').strip()
    if not text:
        return True
    return _bare(text) == _bare(code)


def analyse_field(filenames, used, position):
    """What is wrong with one field's vocabulary.

    `used` is the code to description mapping the repository holds. Returns
    unnamed, unused and unknown, each a list of (code, description, count)
    sorted by how many documents are affected, most first.
    """
    counts = count_codes(filenames, position)
    unnamed, unused = [], []
    for code, description in used.items():
        count = counts.get(code, 0)
        if count == 0:
            unused.append((code, description, 0))
        elif is_unnamed(code, description):
            unnamed.append((code, description, count))
    unknown = [(code, '', count) for code, count in counts.items()
               if code not in used]

    def by_count(entry):
        return (-entry[2], entry[0])

    return {
        'unnamed': sorted(unnamed, key=by_count),
        'unused': sorted(unused, key=by_count),
        'unknown': sorted(unknown, key=by_count),
    }


def analyse(filenames, vocabularies):
    """Every field at once. `vocabularies` maps field name to its used dict."""
    report = {}
    for name, position in FIELD_POSITION.items():
        if name in vocabularies:
            report[name] = analyse_field(filenames, vocabularies[name], position)
    return report


def totals(report):
    """How many entries each problem has, across every field."""
    counted = {'unnamed': 0, 'unused': 0, 'unknown': 0}
    for field in report.values():
        for problem, entries in field.items():
            counted[problem] += len(entries)
    return counted


def documents_using(filenames, position, codes):
    """The documents whose field at `position` holds one of `codes`."""
    wanted = set(codes)
    found = []
    for filename in filenames:
        parts = fields(filename)
        if len(parts) == 7 and parts[position].strip() in wanted:
            found.append(filename)
    return sorted(found)
