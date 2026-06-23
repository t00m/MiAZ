#!/usr/bin/python3
# File: concept_ops.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Pure, GTK-free transforms for the MiAZMassRename concept tool.


def parse_positions(spec, count):
    """Parse a 1-based position spec into sorted unique 0-based indices within
    range(count). Supports 'N', 'N-M', 'N-' (to end) and comma-separated
    combinations. Invalid or out-of-range parts are dropped."""
    indices = set()
    for part in (spec or '').split(','):
        part = part.strip()
        if not part:
            continue
        try:
            if '-' in part:
                lo, _, hi = part.partition('-')
                start = int(lo) if lo.strip() else 1
                end = int(hi) if hi.strip() else count
            else:
                start = end = int(part)
        except ValueError:
            continue
        for pos in range(start, end + 1):
            if 1 <= pos <= count:
                indices.add(pos - 1)
    return sorted(indices)


def keep_tokens(concept, spec, sep='_'):
    tokens = concept.split(sep)
    keep = parse_positions(spec, len(tokens))
    return sep.join(tokens[i] for i in keep)


def remove_tokens(concept, spec, sep='_'):
    tokens = concept.split(sep)
    drop = set(parse_positions(spec, len(tokens)))
    return sep.join(t for i, t in enumerate(tokens) if i not in drop)


def add_prefix(concept, text, sep='_'):
    if not text:
        return concept
    if not concept:
        return text
    return f"{text}{sep}{concept}"


def add_suffix(concept, text, sep='_'):
    if not text:
        return concept
    if not concept:
        return text
    return f"{concept}{sep}{text}"


def find_replace(concept, find, replace):
    if not find:
        return concept
    return concept.replace(find, replace)


def change_case(concept, mode):
    if mode == 'upper':
        return concept.upper()
    if mode == 'lower':
        return concept.lower()
    if mode == 'title':
        return concept.title()
    return concept


def set_value(concept, value):
    return value


def apply(op, concept, params):
    sep = params.get('sep') or '_'
    if op == 'keep':
        return keep_tokens(concept, params.get('positions', ''), sep)
    if op == 'remove':
        return remove_tokens(concept, params.get('positions', ''), sep)
    if op == 'prefix':
        return add_prefix(concept, params.get('text', ''), sep)
    if op == 'suffix':
        return add_suffix(concept, params.get('text', ''), sep)
    if op == 'replace':
        return find_replace(concept, params.get('find', ''), params.get('replace', ''))
    if op == 'case':
        return change_case(concept, params.get('mode', ''))
    if op == 'set':
        return set_value(concept, params.get('value', ''))
    return concept
