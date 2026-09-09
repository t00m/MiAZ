"""
# File: cli.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Command line interface: argument parsing, commands, output
"""

import argparse
import json
import logging
import os
from datetime import datetime
from gettext import gettext as _

from MiAZ.backend.log import set_console_level
from MiAZ.backend.query import (ANY, DATE_PRESET_ALL, DATE_PRESETS, DATE_RANGE,
                                DocumentQuery, resolve_preset)
from MiAZ.frontend.console.app import MiAZConsoleApp

# Everything query.py knows about, minus the token that means "no filter":
# --since with no range would be a flag that does nothing.
PRESETS = tuple(token for token in DATE_PRESETS if token != DATE_PRESET_ALL)

# The five filename fields chosen from a controlled vocabulary. Their flags and
# their DocumentQuery attributes carry the same name on purpose.
FIELDS = ('country', 'group', 'sentby', 'purpose', 'sentto')


class UsageError(Exception):
    """The arguments do not make sense. Reported on stderr, exit code 2."""


def _parse_date(text):
    # A date, not a datetime. The bounds are compared against parse_date(),
    # which returns date objects, and the two types do not compare.
    try:
        return datetime.strptime(text, '%Y%m%d').date()
    except ValueError:
        raise UsageError(
            _("dates are written as YYYYMMDD, not '{value}'").format(value=text))


def build_query(args, util):
    """Turn parsed arguments into a DocumentQuery.

    No condition lives here. Every flag sets a field the workspace filter
    already understands, which is what keeps the two from drifting apart.
    `util` is needed only to resolve a --since preset.
    """
    if args.since and (args.date_from or args.date_to):
        raise UsageError(_('use --since or --from and --to, not both'))
    if args.since and args.since not in PRESETS:
        raise UsageError(
            _("unknown period '{value}'. Try one of: {valid}").format(
                value=args.since, valid=', '.join(PRESETS)))

    values = {field: (getattr(args, field) or '').upper() or ANY for field in FIELDS}
    query = DocumentQuery(
        search=args.text or '',
        concept=args.concept or '',
        only_pending=args.pending,
        ignore_active=args.all,
        **values)

    if args.since:
        query.date_preset = args.since
        query.date_mode = DATE_RANGE
        query.date_since, query.date_until = resolve_preset(
            args.since, datetime.now(), util)
    elif args.date_from or args.date_to:
        query.date_mode = DATE_RANGE
        query.date_since = _parse_date(args.date_from) if args.date_from else None
        query.date_until = _parse_date(args.date_to) if args.date_to else None
        if (query.date_since is not None and query.date_until is not None
                and query.date_since > query.date_until):
            raise UsageError(_('--from is later than --to'))
    return query


COLUMNS = (
    ('DATE', 'date_dsc'),
    ('COUNTRY', 'country_dsc'),
    ('GROUP', 'group_dsc'),
    ('SENT BY', 'sentby_dsc'),
    ('PURPOSE', 'purpose_dsc'),
    ('CONCEPT', 'subtitle'),
    ('SENT TO', 'sentto_dsc'),
)


def as_record(item):
    """The JSON shape. Flat on purpose, so jq needs no digging."""
    return {
        'id': item.id,
        'path': item.title,
        'date': item.date,
        'date_label': item.date_dsc,
        'country': item.country,
        'country_label': item.country_dsc,
        'group': item.group,
        'group_label': item.group_dsc,
        'sentby': item.sentby_id,
        'sentby_label': item.sentby_dsc,
        'purpose': item.purpose,
        'purpose_label': item.purpose_dsc,
        'concept': item.subtitle,
        'sentto': item.sentto_id,
        'sentto_label': item.sentto_dsc,
        'extension': item.extension,
        'valid': item.valid,
        'active': item.active,
    }


def render(items, args, stream):
    """Write the results. Filenames by default, a table or JSON on request."""
    if getattr(args, 'json', False):
        json.dump([as_record(item) for item in items], stream, indent=2)
        stream.write('\n')
        return

    if not getattr(args, 'long', False):
        for item in items:
            stream.write(f'{item.id}\n')
        return

    rows = [[title for title, _attr in COLUMNS]]
    rows += [[str(getattr(item, attr) or '') for _title, attr in COLUMNS]
             for item in items]
    widths = [max(len(row[column]) for row in rows) for column in range(len(COLUMNS))]
    for row in rows:
        line = '  '.join(value.ljust(widths[column])
                         for column, value in enumerate(row))
        stream.write(f'{line.rstrip()}\n')


def cmd_search(app, args, stdout, stderr):
    """Find documents. 0 with results, 1 without, 2 when the flags are wrong."""
    util = app.get_service('util')
    try:
        query = build_query(args, util)
    except UsageError as error:
        stderr.write(f'{error}\n')
        return 2

    index = app.get_service('index')
    items = [item for item in index.documents() if query.matches(item)]
    items.sort(key=lambda item: (item.date, item.id), reverse=True)
    if args.limit:
        items = items[:args.limit]

    if not items:
        # Search hides documents whose values the configuration does not know,
        # exactly as the workspace does. On a repository where nothing
        # validates, silence reads as a broken command, so say what is there.
        # pending() is the one that means "fails validation against the enabled
        # configuration", which is what the workspace Review button counts.
        # invalid() is a different thing: filenames that do not split into
        # seven fields at all.
        needing_review = len(index.pending())
        if needing_review and not args.all:
            stderr.write(_('no matches; {count} documents in this repository '
                           'need review (try --all)\n').format(count=needing_review))
        return 1

    render(items, args, stdout)
    return 0


def cmd_repos(app, args, stdout, stderr):
    """List the registered repositories. Opens none of them."""
    repos = app.get_config('Repository').load_used()
    if not repos:
        stderr.write(_('no repositories configured\n'))
        return 1

    current = app.get_config('App').get('current')

    def path_of(entry):
        return entry.get('path', '') if isinstance(entry, dict) else entry

    if args.json:
        json.dump([{'name': name,
                    'path': path_of(entry),
                    'description': entry.get('description', '') if isinstance(entry, dict) else '',
                    'current': name == current}
                   for name, entry in sorted(repos.items())], stdout, indent=2)
        stdout.write('\n')
        return 0

    width = max(len(name) for name in repos)
    for name, entry in sorted(repos.items()):
        marker = '*' if name == current else ' '
        stdout.write(f'{name.ljust(width)} {marker} {path_of(entry)}\n')
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog='miaz', description=_('Personal Document Organizer'))
    commands = parser.add_subparsers(dest='command')

    search = commands.add_parser('search', help=_('Find documents'))
    search.add_argument('text', nargs='?', help=_('Free text to look for'))
    search.add_argument('--concept', help=_('Substring of the concept field'))
    for field in FIELDS:
        search.add_argument(f'--{field}', metavar='CODE',
                            help=_('Filter by {field}').format(field=field))
    search.add_argument('--since', metavar='PERIOD',
                        help=_('One of: {valid}').format(valid=', '.join(PRESETS)))
    search.add_argument('--from', dest='date_from', metavar='YYYYMMDD',
                        help=_('Documents dated on or after this day'))
    search.add_argument('--to', dest='date_to', metavar='YYYYMMDD',
                        help=_('Documents dated on or before this day'))
    search.add_argument('--pending', action='store_true',
                        help=_('Only documents that need review'))
    search.add_argument('--all', action='store_true',
                        help=_('Include documents whose values are not in the configuration'))
    search.add_argument('--limit', type=int, metavar='N',
                        help=_('Show at most N documents'))
    search.add_argument('--repo', metavar='NAME_OR_PATH',
                        help=_('Which repository to search'))
    search.add_argument('--long', action='store_true',
                        help=_('Table with expanded labels'))
    search.add_argument('--json', action='store_true', help=_('JSON records'))

    repos = commands.add_parser('repos', help=_('List repositories'))
    repos.add_argument('--json', action='store_true', help=_('JSON records'))
    return parser


# What miaz.py checks the first argument against before choosing the command
# line over the window.
HANDLERS = {'search': cmd_search, 'repos': cmd_repos}
COMMANDS = frozenset(HANDLERS)


def main(argv, stdout, stderr, env=None):
    """Run a command. Returns the process exit code.

    0 results, 1 nothing found, 2 the arguments are wrong, 3 the repository
    cannot be used.
    """
    args = build_parser().parse_args(argv)
    if not args.command:
        stderr.write(_('usage: miaz [search|repos] ...\n'))
        return 2

    # A command prints results, not a startup narration. MIAZ_DEBUG=1 brings
    # the usual logging back when something needs looking at.
    if not os.environ.get('MIAZ_DEBUG'):
        set_console_level(logging.WARNING)

    if env is None:
        from MiAZ.env import ENV
        env = ENV

    app = MiAZConsoleApp(env)
    # 'repos' reads the application configuration only, so it works even when
    # no repository can be opened, which is exactly when it is most useful.
    if args.command == 'repos':
        return cmd_repos(app, args, stdout, stderr)

    code, message = app.open_repository(getattr(args, 'repo', None))
    if code:
        stderr.write(f'{message}\n')
        return code
    return HANDLERS[args.command](app, args, stdout, stderr)
