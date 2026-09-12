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
import sys
from datetime import datetime
from gettext import gettext as _, ngettext

from MiAZ.backend import importer, rename
from MiAZ.backend.log import MiAZLog, debug_requested, set_console_level
from MiAZ.backend.notes import NotesStore, notes_dir
from MiAZ.backend.plugins import (MiAZPluginCore, discover_commands,
                                  parse_operations)
from MiAZ.backend.models import Country, Group, Purpose, SentBy, SentTo
from MiAZ.backend.query import (ANY, DATE_PRESET_ALL, DATE_PRESETS, DATE_RANGE,
                                NONE, DocumentQuery, resolve_preset)
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


def _field_value(raw):
    """One --field argument, as the query model spells it.

    'Any' and 'None' are the two sentinels _matches_value understands, and
    upper-casing turned both into ordinary codes that match no document:
    'ANY' is not 'Any'. Omitting the flag has always meant Any. Spelling it
    out now means the same, and 'none' asks for the documents whose field was
    never filled in, which is the shape filename_normalize leaves behind for
    anything dropped into the repository under a name MiAZ did not write.

    The cost is that a real code spelled ANY or NONE cannot be searched for.
    No controlled vocabulary in this project uses either.
    """
    text = (raw or '').strip()
    if not text or text.lower() == ANY.lower():
        return ANY
    if text.lower() == NONE.lower():
        return NONE
    return text.upper()


def validate_search_args(args):
    """The flags build_query never sees, because they are not query fields.

    --limit is the only one, and `miaz notes` takes it too, so both commands
    check it here. Left unchecked, --limit -1 sliced items[:-1] and quietly
    dropped the newest document, which reads as a search that lies rather
    than as a typo.
    """
    if args.limit is not None and args.limit < 1:
        raise UsageError(
            _('--limit counts documents, so it starts at 1, not {value}')
            .format(value=args.limit))


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

    values = {field: _field_value(getattr(args, field)) for field in FIELDS}
    query = DocumentQuery(
        search=args.text or '',
        concept=args.concept or '',
        only_pending=args.pending,
        ignore_active=args.all,
        # A code typed at a terminal is remembered as a word, not as the code
        # the filename carries: `--sentby vatt` is how somebody looks for
        # VATTENFALL. The window means the dropdown entry it was given.
        partial_fields=True,
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


def write_table(columns, rows, stream):
    """An aligned table: the column titles, then the rows, padded to fit.

    Shared by the two commands that print one, so a column is added by naming
    it rather than by writing the padding again.
    """
    lines = [[title for title, _attr in columns]] + rows
    widths = [max(len(line[column]) for line in lines)
              for column in range(len(columns))]
    for line in lines:
        text = '  '.join(value.ljust(widths[column])
                         for column, value in enumerate(line))
        stream.write(f'{text.rstrip()}\n')


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

    rows = [[str(getattr(item, attr) or '') for _title, attr in COLUMNS]
            for item in items]
    write_table(COLUMNS, rows, stream)


def cmd_search(app, args, stdout, stderr):
    """Find documents. 0 with results, 1 without, 2 when the flags are wrong."""
    util = app.get_service('util')
    try:
        validate_search_args(args)
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


# A document whose fields are still empty is named `-----CONCEPT-.pdf`: five
# separators and nothing in front of them. No option starts like that.
EMPTY_FIELDS_PREFIX = '-----'

# Which positional each command means when it is handed one of those names,
# and whether that positional takes a list or a single document.
DOCUMENT_ARGUMENTS = {'add': ('paths', True), 'delete': ('documents', True),
                      'rename': ('document', False)}


def parse_arguments(parser, argv):
    """Parse, letting a document name that starts with a dash be one.

    argparse reads a leading dash as an option, and the documents somebody
    deletes from a terminal are exactly the ones named `-----SCAN-.pdf`:
    `miaz search --pending` prints nothing else, and piping that into `miaz
    delete` handed argparse a list of what looked like unknown flags.

    Such a name goes back into the positional it was meant for. Anything else
    unrecognised is still an error, so a mistyped flag is still a mistyped
    flag. A name given this way is read after the ones argparse accepted
    normally, which changes the order of a mixed list and nothing else.
    """
    args, extras = parser.parse_known_args(argv)
    names = [extra for extra in extras
             if extra.startswith(EMPTY_FIELDS_PREFIX)]
    rest = [extra for extra in extras
            if not extra.startswith(EMPTY_FIELDS_PREFIX)]
    target, many = DOCUMENT_ARGUMENTS.get(getattr(args, 'command', None),
                                          (None, False))
    unrecognised = list(rest)
    if names and target is None:
        unrecognised += names
    elif names and not many:
        # One document, so a second name is not a document, it is a mistake.
        if getattr(args, target, None) or len(names) > 1:
            unrecognised += names
        else:
            setattr(args, target, names[0])
    elif names:
        setattr(args, target, list(getattr(args, target) or []) + names)
    if unrecognised:
        parser.error(_('unrecognized arguments: {arguments}').format(
            arguments=' '.join(unrecognised)))
    return args


def cmd_add(app, args, stdout, stderr):
    """Copy files and directories into the repository.

    Prints the repository name each file arrived under, one per line, so the
    output feeds a script. 0 when everything asked for arrived, 1 when
    anything did not, and what did not is named on stderr.
    """
    repository = app.get_service('repo')
    util = app.get_service('util')

    if not args.paths:
        stderr.write(_('name a file or a directory to add\n'))
        return 2

    paths = importer.expand_paths(args.paths, recursive=args.recursive)
    if not paths:
        # An empty directory, or one whose files are all in subdirectories
        # while --recursive was not given.
        stderr.write(_('nothing to add\n'))
        return 1

    imported, failed = importer.import_paths(util, repository.docs, paths)
    for name in imported:
        stdout.write(f'{name}\n')
    for name in failed:
        stderr.write(_("could not add '{name}'\n").format(name=name))
    return 1 if failed else 0


def repository_document(docs_dir, given):
    """The path of a named document inside the repository, or None.

    A pipeline gives a name and tab completion gives a path, so both are taken.
    A path somewhere else is not: it names a different file that happens to
    share a name, and deleting the repository's copy of it would be a guess.
    """
    if os.sep in given:
        directory = os.path.dirname(os.path.abspath(given))
        if directory != os.path.normpath(docs_dir):
            return None
    path = os.path.join(docs_dir, os.path.basename(given))
    return path if os.path.isfile(path) else None


def ask_to_confirm(question, stream):
    """Ask on the terminal. None when there is no terminal to ask on."""
    if not sys.stdin.isatty():
        return None
    stream.write(question)
    answer = sys.stdin.readline().strip().lower()
    return answer in ('y', 'yes')


def cmd_delete(app, args, stdout, stderr):
    """Delete documents from the repository.

    0 when they were deleted, 1 when the user said no, 2 when a name is not
    one the repository holds or there is nobody to ask and no --yes. Nothing
    is deleted unless every name given is a document: a typo in a list must
    not take the documents that were spelled right.
    """
    repository = app.get_service('repo')
    util = app.get_service('util')

    if not args.documents:
        stderr.write(_('name a document to delete\n'))
        return 2

    paths = []
    unknown = []
    for given in args.documents:
        path = repository_document(repository.docs, given)
        if path is None:
            unknown.append(given)
        else:
            paths.append(path)

    if unknown:
        for name in unknown:
            stderr.write(_("'{name}' is not a document in this repository\n")
                         .format(name=name))
        stderr.write(_('nothing was deleted\n'))
        return 2

    if not args.yes:
        for path in paths:
            stderr.write(f'{os.path.basename(path)}\n')
        answer = ask_to_confirm(
            _('Delete {count} documents? [y/N] ').format(count=len(paths)),
            stderr)
        if answer is None:
            stderr.write(_('nothing was deleted: pass --yes to delete without '
                           'being asked\n'))
            return 2
        if not answer:
            stderr.write(_('nothing was deleted\n'))
            return 1

    util.filename_delete(set(paths))
    for path in paths:
        stdout.write(f'{os.path.basename(path)}\n')
    return 0


# The models the index counts documents by, one per field with a vocabulary.
MODEL_OF = {'country': Country, 'group': Group, 'sentby': SentBy,
            'purpose': Purpose, 'sentto': SentTo}

# How each problem with a field reads. The backend returns the reason; the
# wording, and its translation, belong here.
PROBLEM_TEXT = {
    rename.UNKNOWN: _("{field}: '{value}' is not a {field} this repository "
                      "has. Add it with: miaz fields {field} --add {value} "
                      "<description>"),
    rename.NOT_A_DATE: _("date: '{value}' is not a date (YYYYMMDD)"),
    rename.EMPTY: _('{field}: not set'),
}


def cmd_rename(app, args, stdout, stderr):
    """Change the fields of a document name.

    0 when the document was renamed, 1 never (a rename that changes nothing is
    not a failure), 2 when a field cannot be what it was asked to be. Nothing
    is renamed unless every field is good: a name half applied is a document
    filed under something nobody chose.
    """
    repository = app.get_service('repo')
    util = app.get_service('util')

    if not args.document:
        stderr.write(_('name a document to rename\n'))
        return 2

    path = repository_document(repository.docs, args.document)
    if path is None:
        stderr.write(_("'{name}' is not a document in this repository\n")
                     .format(name=args.document))
        return 2

    basename = os.path.basename(path)
    fields, extension = rename.split(util, basename)
    changes = {field: getattr(args, field, None) for field in rename.FIELDS}
    fields.update(rename.normalize(util, changes))

    found = rename.problems(app, fields)
    if found:
        for field, value, reason in found:
            stderr.write(PROBLEM_TEXT[reason].format(field=field, value=value)
                         + '\n')
        stderr.write(_('nothing was renamed\n'))
        return 2

    # Uppercased here rather than left to filename_rename: the checks below
    # are about the name the file will really get, and comparing against the
    # composed one made a document collide with itself.
    target = os.path.join(repository.docs,
                          util.filename_upper(rename.compose(fields, extension)))
    if not util.filename_rename_needed(path, target):
        stderr.write(_('nothing to change\n'))
        return 0
    if os.path.exists(target):
        stderr.write(_("this repository already holds '{name}'\n").format(
            name=os.path.basename(target)))
        stderr.write(_('nothing was renamed\n'))
        return 2

    if not util.filename_rename(path, target):
        stderr.write(_("could not rename '{name}'\n").format(name=basename))
        return 3

    stdout.write(f'{basename} -> {os.path.basename(target)}\n')
    return 0


def cmd_fields(app, args, stdout, stderr):
    """Read and change the values a field may take.

    With no field, the fields that have a vocabulary. With one, its keys and
    their descriptions, or the addition or removal asked for.
    """
    util = app.get_service('util')

    if not args.field:
        for field in rename.CONFIG_OF:
            stdout.write(f'{field}\n')
        return 0

    field = args.field.lower()
    if field not in rename.CONFIG_OF:
        stderr.write(_("'{field}' has no values to manage. Fields with a "
                       "vocabulary: {fields}\n").format(
                           field=args.field,
                           fields=', '.join(rename.CONFIG_OF)))
        return 2
    config = app.get_config(rename.CONFIG_OF[field])

    if args.add:
        key, description = args.add
        key = util.valid_key(key).upper()
        if not key:
            stderr.write(_('a key cannot be empty\n'))
            return 2
        # Available as well as used, which is what the rename dialog's inline
        # Add does: a value added from a terminal is the value the window
        # offers, in the same two places.
        config.add_available(key, description)
        config.add_used(key, description)
        # add() leaves a key that is already there alone, so this is what
        # corrects a description: `--add INV Bill` on a key that exists.
        config.set_description(key, description)
        stdout.write(f'{key}  {description}\n')
        return 0

    if args.remove:
        key = args.remove.upper()
        if not config.exists_used(key):
            stderr.write(_("'{key}' is not a {field} this repository has\n")
                         .format(key=key, field=field))
            return 2
        index = app.get_service('index')
        used, documents = index.field_used(MODEL_OF[field], key)
        if used:
            stderr.write(ngettext(
                "'{key}' is still on {count} document. Rename it first\n",
                "'{key}' is still on {count} documents. Rename them first\n",
                len(documents)).format(key=key, count=len(documents)))
            return 2
        # Disabled for this repository, not thrown away: it stays in the
        # available pool, which is what the window's own remove does.
        config.add_available(key, config.get(key) or '')
        config.remove_used(key)
        return 0

    values = config.load_used()
    if args.json:
        json.dump([{'key': key, 'description': description}
                   for key, description in sorted(values.items())],
                  stdout, indent=2)
        stdout.write('\n')
        return 0
    for key, description in sorted(values.items()):
        stdout.write(f'{key}  {description}\n')
    return 0


NOTE_COLUMNS = (
    ('DATE', 'date'),
    ('DOCUMENT', 'document_id'),
    ('CATEGORY', 'category'),
    ('PRIORITY', 'priority'),
    ('STATUS', 'status'),
    ('SUMMARY', 'summary'),
)


def as_note_record(note):
    """The JSON shape of a note. The body is in it: a note is its text."""
    return {
        'path': note.path,
        'document': note.document_id,
        'date': note.date,
        'author': note.author,
        'category': note.category,
        'priority': note.priority,
        'status': note.status,
        'summary': note.summary,
        'body': note.body,
    }


def render_notes(notes, store, args, stream):
    """Write the notes found. One line each, or the whole of them on request."""
    if getattr(args, 'json', False):
        json.dump([as_note_record(note) for note in notes], stream, indent=2)
        stream.write('\n')
        return

    if getattr(args, 'full', False):
        for note in notes:
            # The note as the file holds it: the header, a blank line, the
            # body. serialize_header and this blank line are what _write puts
            # in the file, so what is printed is what is stored.
            stream.write(f'{note.path}\n\n')
            stream.write(store.serialize_header(note.header))
            stream.write(f'\n{note.body.rstrip()}\n\n')
        return

    if getattr(args, 'long', False):
        rows = [[str(getattr(note, attr) or '') for _title, attr in NOTE_COLUMNS]
                for note in notes]
        write_table(NOTE_COLUMNS, rows, stream)
        return

    for note in notes:
        stream.write(f'{note.date}  {note.document_id}  {note.summary}\n')


def cmd_notes(app, args, stdout, stderr):
    """Read the notes filed against the documents.

    0 with results, 1 without, 2 when the flags are wrong. It reads and does
    not write: creating and deleting notes is the window's, and MiAZOCR files
    its own through the same store.
    """
    try:
        validate_search_args(args)
    except UsageError as error:
        stderr.write(f'{error}\n')
        return 2

    repository = app.get_service('repo')
    store = NotesStore(notes_dir(repository.docs), MiAZLog('MiAZ.CLI.Notes'))
    notes = store.search(text=args.text or '',
                         document=args.document or '',
                         category=args.category or '',
                         status=args.status or '',
                         priority=args.priority or '')
    if args.limit:
        notes = notes[:args.limit]

    if not notes:
        # A repository with no notes at all and a filter that matched none are
        # different answers, and silence reads as a broken command.
        if not store.list_all():
            stderr.write(_('this repository has no notes\n'))
        return 1

    render_notes(notes, store, args, stdout)
    return 0


def repo_from(argv):
    """The repository named in these arguments, without parsing them.

    Which commands the help lists depends on which repository is meant, and
    the parser cannot say which one that is before it has been built. Read by
    hand rather than in two passes: it is one flag, in either of its spellings.
    """
    for index, token in enumerate(argv):
        if token == '--repo' and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith('--repo='):
            return token.split('=', 1)[1]
    return None


def enabled_plugins(docs_dir):
    """The plugins a repository enables, or None when it does not say.

    Read straight from the repository configuration, the same file the window
    reads when it decides which plugins to load. None means there is nothing
    to go by: no repository, or one the window has never opened, which has no
    list at all. Hiding every plugin command there would read as commands that
    do not exist, so nothing is hidden.
    """
    if not docs_dir:
        return None
    path = os.path.join(docs_dir, '.conf', 'plugins-used.json')
    try:
        with open(path, encoding='utf-8') as handler:
            return frozenset(json.load(handler))
    except (OSError, ValueError):
        return None


def repository_docs(env, selector=None):
    """Where the repository lives, without opening it.

    The parser is built before anything is loaded, so this resolves a name or
    a path to a directory and stops there: no index, no documents read, no
    plugin imported.
    """
    if env is None:
        return None
    try:
        app = MiAZConsoleApp(env)
        repository = app.get_service('repo')
        repository.reset()
        if selector:
            if os.sep in selector or os.path.isdir(selector):
                resolved = repository.use(path=selector)
            else:
                resolved = repository.use(selector)
            if not resolved:
                return None
        return repository.docs
    except Exception:
        # Building the parser must not be the thing that fails. A repository
        # that cannot be resolved simply filters nothing.
        return None


def plugin_search_paths(env=None):
    """Where to look for plugins, or nothing when the environment is unknown.

    Taken from ENV rather than hardcoded so a test can point the command line
    at a temporary directory instead of the installed plugins.
    """
    if env is None:
        return []
    return [env.get('GPATH', {}).get('PLUGINS'),
            env.get('LPATH', {}).get('PLUGINS')]


def known_commands(search_paths=None) -> frozenset:
    """Every command name this build answers to, built-in and contributed.

    miaz.py tests the first argument against this before it decides between
    the window and the command line, so a plugin command missing from here
    would open the window instead of running.
    """
    return frozenset(HANDLERS) | frozenset(discover_commands(search_paths))


def _add_plugin_command(commands, name, declared, search_paths, listed=True):
    """Give one plugin command its subparser, with the flags it declares.

    The module is imported here because this is the point where the schema is
    needed, and only this one module is: `miaz search` never reaches it.
    """
    core = MiAZPluginCore(search_paths=search_paths, log_name='MiAZ.CLI.Plugins')
    module = core.import_module(declared['module'])
    if module is None:
        return None

    operation = None
    for candidate in parse_operations(getattr(module, 'plugin_info', {}) or {},
                                      owner=declared['module']):
        if candidate.name == name:
            operation = candidate
            break
    if operation is None:
        return None

    # A command whose plugin the repository does not enable is added without
    # a help string. argparse builds the line in the command list out of that
    # string, so leaving it out is what keeps the command runnable and unlisted.
    if listed:
        parser = commands.add_parser(name, help=declared['help'] or operation.help)
    else:
        parser = commands.add_parser(name)
    operation.add_arguments(parser)
    parser.add_argument('--repo', metavar='NAME_OR_PATH',
                        default=argparse.SUPPRESS,
                        help=_('Which repository to work on'))
    parser.set_defaults(_operation=operation, _module=module,
                        _plugin=declared['plugin_name'])
    return operation


class MiAZParser(argparse.ArgumentParser):
    """A parser whose help holds each command's options, not only its name.

    argparse prints a subcommand as a name and one line of help, and keeps its
    flags behind `miaz search --help`. Somebody reading `miaz --help` is asking
    what MiAZ takes, so all of it is printed: the list of commands first, then
    the help of each command under it.

    Subparsers inherit this class, since add_subparsers defaults parser_class
    to the type of the parser it is called on. That costs nothing: a command
    has no commands of its own, so its help is the one argparse writes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Commands that are in the parser but not in the help: a plugin
        # command the repository does not enable. Runnable, so the refusal can
        # say why, and unlisted, because it cannot be run against this one.
        self.hidden_commands = set()

    def format_help(self):
        text = super().format_help()
        blocks = [subparser.format_help().rstrip()
                  for _name, subparser in self.command_parsers()]
        if not blocks:
            return text
        return '{text}\n{header}\n\n{blocks}\n'.format(
            text=text.rstrip('\n') + '\n',
            header=_('each command in detail:'),
            blocks='\n\n'.join(blocks))

    def command_parsers(self):
        """(name, parser) for every subcommand, in the order they were added.

        Read off the actions rather than kept in a second list, so a command
        added anywhere is described here without being registered twice.
        """
        hidden = self.hidden_commands or frozenset()
        for action in self._actions:
            choices = getattr(action, 'choices', None)
            if not isinstance(choices, dict):
                continue
            for name, subparser in choices.items():
                if name in hidden:
                    continue
                if isinstance(subparser, argparse.ArgumentParser):
                    yield name, subparser


def build_parser(search_paths=None, env=None, repo=None):
    """The parser, listing the commands this repository can run.

    `env` and `repo` say which repository that is: the one named, or the
    current one. Without an env there is no repository to ask about and every
    command is listed, which is what a test and a bare import get.
    """
    parser = MiAZParser(
        prog='miaz', description=_('Personal Document Organizer'))
    parser.add_argument('--repo', metavar='NAME_OR_PATH',
                        help=_('Which repository to work on'))
    commands = parser.add_subparsers(dest='command')

    search = commands.add_parser('search', help=_('Find documents'))
    search.add_argument('text', nargs='?', help=_('Free text to look for'))
    search.add_argument('--concept', help=_('Substring of the concept field'))
    for field in FIELDS:
        search.add_argument(f'--{field}', metavar='TEXT',
                            help=_('Filter by {field}. Any part of the code or '
                                   'its description, or none for the documents '
                                   'with no {field}').format(field=field))
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
                        help=_('Show at most N documents, N being 1 or more'))
    search.add_argument('--repo', metavar='NAME_OR_PATH',
                        default=argparse.SUPPRESS,
                        help=_('Which repository to search'))
    search.add_argument('--long', action='store_true',
                        help=_('Table with expanded labels'))
    search.add_argument('--json', action='store_true', help=_('JSON records'))

    repos = commands.add_parser('repos', help=_('List repositories'))
    repos.add_argument('--json', action='store_true', help=_('JSON records'))

    add = commands.add_parser('add', help=_('Add documents to the repository'))
    add.add_argument('paths', nargs='*', metavar='PATH',
                     help=_('Files or directories to add'))
    add.add_argument('--recursive', '-r', action='store_true',
                     help=_('Take the whole tree of a directory, not only the '
                            'files directly in it'))
    add.add_argument('--repo', metavar='NAME_OR_PATH',
                     default=argparse.SUPPRESS,
                     help=_('Which repository to add to'))

    delete = commands.add_parser('delete',
                                 help=_('Delete documents from the repository'))
    delete.add_argument('documents', nargs='*', metavar='DOCUMENT',
                        help=_('Document names, as `miaz search` prints them'))
    delete.add_argument('--yes', '-y', action='store_true',
                        help=_('Do not ask first. Needed when there is no '
                               'terminal to ask on'))
    delete.add_argument('--repo', metavar='NAME_OR_PATH',
                        default=argparse.SUPPRESS,
                        help=_('Which repository to delete from'))

    renamer = commands.add_parser(
        'rename', help=_('Change the fields of a document name'))
    renamer.add_argument('document', nargs='?', metavar='DOCUMENT',
                         help=_('The document to rename, as `miaz search` '
                                'prints it'))
    renamer.add_argument('--date', metavar='YYYYMMDD', help=_('Document date'))
    for field in ('country', 'group', 'sentby', 'purpose', 'sentto'):
        renamer.add_argument(f'--{field}', metavar='CODE',
                             help=_('A {field} this repository has. See: miaz '
                                    'fields {field}').format(field=field))
    renamer.add_argument('--concept', metavar='TEXT',
                         help=_('What the document is about'))
    renamer.add_argument('--repo', metavar='NAME_OR_PATH',
                         default=argparse.SUPPRESS,
                         help=_('Which repository the document is in'))

    fields = commands.add_parser(
        'fields', help=_('The values a document field may take'))
    fields.add_argument('field', nargs='?', metavar='FIELD',
                        help=_('country, group, sentby, purpose or sentto'))
    fields.add_argument('--list', action='store_true',
                        help=_('List the keys and their descriptions, which is '
                               'also what naming a field on its own does'))
    fields.add_argument('--add', nargs=2, metavar=('KEY', 'DESCRIPTION'),
                        help=_('Add a key, or describe one that is there'))
    fields.add_argument('--remove', metavar='KEY',
                        help=_('Remove a key, unless documents still carry it'))
    fields.add_argument('--json', action='store_true', help=_('JSON records'))
    fields.add_argument('--repo', metavar='NAME_OR_PATH',
                        default=argparse.SUPPRESS,
                        help=_('Which repository to work on'))

    notes = commands.add_parser('notes', help=_('Read the notes on documents'))
    notes.add_argument('text', nargs='?',
                       help=_('Free text to look for in the note, its header '
                              'or the document it is filed against'))
    notes.add_argument('--document', metavar='TEXT',
                       help=_('Only notes on documents whose name holds this'))
    notes.add_argument('--category', metavar='TEXT',
                       help=_('Only notes whose category holds this'))
    notes.add_argument('--status', metavar='TEXT',
                       help=_('Only notes whose status holds this'))
    notes.add_argument('--priority', metavar='TEXT',
                       help=_('Only notes whose priority holds this'))
    notes.add_argument('--full', action='store_true',
                       help=_('Print each note in full, header and body'))
    notes.add_argument('--limit', type=int, metavar='N',
                       help=_('Show at most N notes, N being 1 or more'))
    notes.add_argument('--repo', metavar='NAME_OR_PATH',
                       default=argparse.SUPPRESS,
                       help=_('Which repository to read'))
    notes.add_argument('--long', action='store_true',
                       help=_('Table with the header fields'))
    notes.add_argument('--json', action='store_true', help=_('JSON records'))

    listed = list(commands.choices)
    enabled = enabled_plugins(repository_docs(env, repo))
    for name, declared in sorted(discover_commands(search_paths).items()):
        if name in HANDLERS:
            # A plugin does not get to shadow `search` or `repos`. Refusing it
            # here beats letting the last plugin scanned decide what `search`
            # means.
            continue
        visible = enabled is None or declared['plugin_name'] in enabled
        if _add_plugin_command(commands, name, declared, search_paths,
                               listed=visible) is None:
            continue
        if visible:
            listed.append(name)
        else:
            parser.hidden_commands.add(name)
    if parser.hidden_commands:
        # The usage line lists the choices out of the parser, hidden ones and
        # all, unless it is told what to say instead.
        commands.metavar = '{%s}' % ','.join(listed)
    return parser


# What miaz.py checks the first argument against before choosing the command
# line over the window.
HANDLERS = {'search': cmd_search, 'repos': cmd_repos, 'notes': cmd_notes,
            'add': cmd_add, 'delete': cmd_delete, 'rename': cmd_rename,
            'fields': cmd_fields}
COMMANDS = frozenset(HANDLERS)


def main(argv, stdout, stderr, env=None):
    """Run a command. Returns the process exit code.

    0 results, 1 nothing found, 2 the arguments are wrong, 3 the repository
    cannot be used.
    """
    if env is None:
        from MiAZ.env import ENV
        env = ENV

    # Built before parsing, because a plugin command's flags are part of the
    # parser. Discovery reads the .plugin files and imports nothing until a
    # plugin command is actually named.
    search_paths = plugin_search_paths(env)
    # The repository is read out of the arguments before they are parsed: it
    # decides which plugin commands this parser lists.
    parser = build_parser(search_paths, env=env, repo=repo_from(argv))
    args = parse_arguments(parser, argv)
    if not args.command:
        stderr.write(_('usage: miaz [search|repos] ...\n'))
        return 2

    # A command prints results, not a startup narration. MIAZ_DEBUG=1 brings
    # the usual logging back when something needs looking at.
    if not debug_requested():
        set_console_level(logging.WARNING)

    app = MiAZConsoleApp(env)
    # 'repos' reads the application configuration only, so it works even when
    # no repository can be opened, which is exactly when it is most useful.
    if args.command == 'repos':
        return cmd_repos(app, args, stdout, stderr)

    code, message = app.open_repository(getattr(args, 'repo', None))
    if code:
        stderr.write(f'{message}\n')
        return code

    if args.command in HANDLERS:
        return HANDLERS[args.command](app, args, stdout, stderr)
    return run_plugin_command(app, args, stdout, stderr)


def run_plugin_command(app, args, stdout, stderr):
    """Call the module-level function the operation names.

    A plugin naming a handler it does not define is the plugin's bug, so say
    which plugin and which name rather than dying with an AttributeError from
    inside here.
    """
    operation = getattr(args, '_operation', None)
    module = getattr(args, '_module', None)
    if operation is None or module is None:
        stderr.write(_("'{command}' is not a command\n").format(
            command=args.command))
        return 2

    # A plugin is enabled per repository, and the window honours that. A
    # command from a plugin this repository does not enable is refused here
    # rather than run: the two frontends answer the same question the same way.
    repository = app.get_service('repo')
    plugin = getattr(args, '_plugin', None)
    enabled = enabled_plugins(repository.docs)
    if plugin is not None and enabled is not None and plugin not in enabled:
        stderr.write(_("'{command}' comes from {plugin}, which is not enabled "
                       "for repository '{repository}'\n").format(
                           command=args.command, plugin=plugin,
                           repository=repository.get_active_id() or repository.docs))
        stderr.write(_('Enable it in the repository settings, Plugins tab\n'))
        return 3

    handler = operation.resolve(module)
    if handler is None:
        stderr.write(_("plugin '{plugin}' declares command '{command}' but "
                       "defines no '{handler}'\n").format(
                           plugin=operation.owner, command=operation.name,
                           handler=operation.run))
        return 2
    return handler(app, args, stdout, stderr)
