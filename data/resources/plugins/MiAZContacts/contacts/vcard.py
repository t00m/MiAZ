# File: vcard.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: vCard reader and writer, no GTK and no MiAZ imports

import quopri

# Longest line a written card may have, in octets, before it is folded.
FOLD_LIMIT = 75

# Properties the writer emits itself, so a parsed card does not repeat them.
STRUCTURAL = ('BEGIN', 'END', 'VERSION')


def unfold(text):
    """The physical lines of a card joined into logical ones."""
    normalised = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = []
    for raw in normalised.split('\n'):
        if lines and raw[:1] in (' ', '\t'):
            lines[-1] += raw[1:]
        elif lines and lines[-1].endswith('=') and 'QUOTED-PRINTABLE' in lines[-1].upper():
            # A vCard 2.1 soft line break: the continuation has no leading space.
            lines[-1] = lines[-1][:-1] + raw
        else:
            lines.append(raw)
    return [line for line in lines if line.strip()]


def escape(text):
    """Text as a vCard value: backslash, newline, comma and semicolon."""
    return (str(text).replace('\\', '\\\\').replace('\n', '\\n')
            .replace(',', '\\,').replace(';', '\\;'))


def unescape(text):
    """The inverse of escape, tolerant of a trailing lone backslash."""
    out = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\' and index + 1 < len(text):
            following = text[index + 1]
            out.append('\n' if following in ('n', 'N') else following)
            index += 2
            continue
        out.append(char)
        index += 1
    return ''.join(out)


def _split_escaped(text, separator):
    """Split on a separator that a backslash can hide."""
    parts = []
    current = ''
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\' and index + 1 < len(text):
            current += text[index:index + 2]
            index += 2
            continue
        if char == separator:
            parts.append(current)
            current = ''
        else:
            current += char
        index += 1
    parts.append(current)
    return parts


def _split_quoted(text, separator):
    """Split on a separator that double quotes can hide."""
    parts = []
    current = ''
    in_quotes = False
    for char in text:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == separator and not in_quotes:
            parts.append(current)
            current = ''
        else:
            current += char
    parts.append(current)
    return parts


def _unquote(text):
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


class Property:
    """One line of a card: an optional group, a name, parameters, a value.

    The value is kept as it was written, still escaped, because a structured
    value like ADR only means something once it is split.
    """

    def __init__(self, name, value, params=None, group=None):
        self.name = name.upper()
        self.value = value
        self.params = params or {}
        self.group = group

    def __repr__(self):
        return f"<Property {self.name} {self.value[:20]!r}>"

    def text(self):
        return unescape(self.value)

    def components(self):
        return [[unescape(value) for value in _split_escaped(part, ',')]
                for part in _split_escaped(self.value, ';')]

    def component(self, position):
        """One component as text, empty when the value has no such part."""
        parts = self.components()
        if position >= len(parts):
            return ''
        return ', '.join(value for value in parts[position] if value)

    def types(self):
        return [value.lower() for value in self.params.get('TYPE', [])]

    def is_preferred(self):
        return 'pref' in self.types() or self.params.get('PREF', [''])[0] == '1'

    @classmethod
    def from_text(cls, name, text, params=None, group=None):
        return cls(name, escape(text), params, group)

    @classmethod
    def from_components(cls, name, parts, params=None, group=None):
        pieces = []
        for part in parts:
            if isinstance(part, (list, tuple)):
                pieces.append(','.join(escape(value) for value in part))
            else:
                pieces.append(escape(part))
        return cls(name, ';'.join(pieces), params, group)


class Card:
    """One vCard: its properties, in the order they were read."""

    def __init__(self, properties=None):
        self.properties = list(properties or [])

    def get(self, name):
        for prop in self.properties:
            if prop.name == name.upper():
                return prop
        return None

    def all(self, name):
        return [prop for prop in self.properties if prop.name == name.upper()]

    def groups(self):
        found = {}
        for prop in self.properties:
            if prop.group:
                found.setdefault(prop.group, []).append(prop)
        return found

    def version(self):
        prop = self.get('VERSION')
        return prop.text() if prop is not None else '4.0'


def _parse_params(parts):
    """The parameters of a line, with vCard 2.1 bare values read as types."""
    params = {}
    for part in parts:
        if not part:
            continue
        key, sign, value = part.partition('=')
        if not sign:
            key, value = 'TYPE', part
        key = key.upper()
        values = [_unquote(one) for one in _split_quoted(value, ',')]
        params.setdefault(key, []).extend(values)
    return params


def _decode(value, params):
    """Undo the transfer encoding of a vCard 2.1 line."""
    encoding = params.get('ENCODING', [''])[0].upper()
    if encoding not in ('QUOTED-PRINTABLE', 'Q'):
        return value
    charset = params.get('CHARSET', ['utf-8'])[0]
    try:
        return quopri.decodestring(value.encode('ascii')).decode(charset, 'replace')
    except (UnicodeError, ValueError):
        return value


def parse_line(line):
    """One logical line as a Property, or None when it is not one."""
    head = ''
    value = ''
    in_quotes = False
    for index, char in enumerate(line):
        if char == '"':
            in_quotes = not in_quotes
        elif char == ':' and not in_quotes:
            head, value = line[:index], line[index + 1:]
            break
    else:
        return None
    parts = _split_quoted(head, ';')
    name = parts[0]
    group = None
    if '.' in name:
        group, _, name = name.partition('.')
    if not name.strip():
        return None
    params = _parse_params(parts[1:])
    decoded = _decode(value, params)
    if 'ENCODING' in params:
        # The encoding described the file, not the value that is now decoded.
        del params['ENCODING']
        decoded = escape(decoded)
    return Property(name.strip(), decoded, params, group)


def parse(text):
    """Every card in a piece of text. Text that holds none yields none."""
    cards = []
    current = None
    for line in unfold(text):
        upper = line.upper()
        if upper.startswith('BEGIN:VCARD'):
            current = Card()
            continue
        if upper.startswith('END:VCARD'):
            if current is not None:
                cards.append(current)
            current = None
            continue
        if current is None:
            continue
        prop = parse_line(line)
        if prop is not None:
            current.properties.append(prop)
    return cards


def fold(line, limit=FOLD_LIMIT):
    """A line cut to the octet limit, continuations marked with a space.

    The cut falls between characters, never inside one, so a folded card is
    still valid UTF-8. A continuation carries a leading space, so it has one
    octet less to work with.
    """
    pieces = []
    current = ''
    size = 0
    for char in line:
        width = len(char.encode('utf-8'))
        ceiling = limit if not pieces else limit - 1
        if size + width > ceiling:
            pieces.append(current)
            current = ''
            size = 0
        current += char
        size += width
    pieces.append(current)
    return '\r\n '.join(pieces)


def _write_param(value):
    return f'"{value}"' if any(char in value for char in ',;:') else value


def format_line(prop):
    """One property as the line that says it."""
    head = prop.name if not prop.group else f'{prop.group}.{prop.name}'
    for key in sorted(prop.params):
        values = ','.join(_write_param(value) for value in prop.params[key])
        head += f';{key}={values}'
    return fold(f'{head}:{prop.value}')


def serialize(cards):
    """Cards as vCard 4.0 text, whatever version they were read from."""
    lines = []
    for card in cards:
        lines.append('BEGIN:VCARD')
        lines.append('VERSION:4.0')
        for prop in card.properties:
            if prop.name in STRUCTURAL:
                continue
            lines.append(format_line(prop))
        lines.append('END:VCARD')
    return '\r\n'.join(lines) + '\r\n'
