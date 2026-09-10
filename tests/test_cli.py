#!/usr/bin/python3

"""
Tests for the command line: argument parsing and query building.

The point of these is that the CLI writes no filter conditions of its own. A
flag either sets a DocumentQuery field or it is a mistake.
"""

import io
import json as jsonlib
import os
import subprocess
import sys
from datetime import date as dtdate

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

import pytest

from MiAZ.backend.models import MiAZItem
from MiAZ.backend.query import ANY, DATE_RANGE, NONE, DocumentQuery
from MiAZ.backend.util import MiAZUtil
from MiAZ.frontend.console.app import MiAZConsoleApp
from MiAZ.backend.notes import notes_dir
from MiAZ.frontend.console.cli import (COMMANDS, HANDLERS, UsageError,
                                       as_record, build_parser, build_query,
                                       cmd_notes, cmd_repos, cmd_search, main,
                                       render)


class NoServices:
    def get_service(self, name):
        return None


def util():
    """MiAZUtil owns the date helpers resolve_preset needs."""
    return MiAZUtil(NoServices())


def parse(argv):
    return build_parser().parse_args(argv)


def test_defaults_match_an_empty_query():
    """`miaz search` with no flag filters nothing. partial_fields is the one
    field the command line sets by itself: it says how a typed field value is
    read, not which documents are wanted."""
    assert build_query(parse(['search']), util()) == DocumentQuery(
        partial_fields=True)


def test_text_and_fields():
    query = build_query(parse(['search', 'invoice', '--country', 'es',
                               '--purpose', 'inv', '--concept', 'water']), util())
    assert query.search == 'invoice'
    assert query.country == 'ES'
    assert query.purpose == 'INV'
    assert query.concept == 'water'
    assert query.group == ANY


def test_since_preset():
    query = build_query(parse(['search', '--since', 'last-6-months']), util())
    assert query.date_preset == 'last-6-months'
    assert query.date_mode == DATE_RANGE
    assert query.date_since is not None


def test_explicit_range():
    query = build_query(parse(['search', '--from', '20240101',
                               '--to', '20241231']), util())
    assert query.date_mode == DATE_RANGE
    assert query.date_since is not None
    assert query.date_until is not None
    assert query.date_preset == ''


def test_since_and_from_conflict():
    with pytest.raises(UsageError):
        build_query(parse(['search', '--since', 'this-month',
                           '--from', '20240101']), util())


def test_unknown_preset_lists_the_valid_ones():
    with pytest.raises(UsageError) as caught:
        build_query(parse(['search', '--since', 'last-week']), util())
    assert 'last-6-months' in str(caught.value)


def test_all_documents_is_not_a_period():
    """It means no date filter, so as a --since value it would do nothing."""
    with pytest.raises(UsageError):
        build_query(parse(['search', '--since', 'all-documents']), util())


def test_bad_date_format():
    with pytest.raises(UsageError):
        build_query(parse(['search', '--from', '2024-01-01']), util())


def test_flags_carry_no_logic_of_their_own():
    """The CLI must not filter differently from a query built by hand."""
    from_flags = build_query(parse(['search', 'x', '--country', 'ES',
                                    '--pending']), util())
    by_hand = DocumentQuery(search='x', country='ES', only_pending=True,
                            partial_fields=True)
    assert from_flags == by_hand


def test_all_includes_documents_the_configuration_does_not_know():
    query = build_query(parse(['search', '--all']), util())
    assert query.ignore_active is True


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def an_item():
    return MiAZItem(
        id='20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf',
        title='/repo/20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf',
        date='20260505', date_dsc='2026-05-05',
        country='ES', country_dsc='Spain',
        group='HOU', group_dsc='Housing',
        sentby_id='ACME', sentby_dsc='ACME S.A.',
        purpose='INV', purpose_dsc='Invoice',
        subtitle='electricity',
        sentto_id='JOHNDOE', sentto_dsc='John Doe',
        extension='pdf', active=True, valid=True)


class Args:
    """Only the two attributes render() reads."""
    long = False
    json = False


def test_plain_output_is_one_filename_per_line():
    out = io.StringIO()
    render([an_item()], Args(), out)
    assert out.getvalue() == '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf\n'


def test_long_output_has_a_header_and_labels():
    args = Args()
    args.long = True
    out = io.StringIO()
    render([an_item()], args, out)
    lines = out.getvalue().splitlines()
    assert lines[0].split() == ['DATE', 'COUNTRY', 'GROUP', 'SENT', 'BY',
                                'PURPOSE', 'CONCEPT', 'SENT', 'TO']
    assert 'Spain' in lines[1]
    assert 'Housing' in lines[1]


def test_long_output_columns_line_up():
    args = Args()
    args.long = True
    out = io.StringIO()
    render([an_item(), an_item()], args, out)
    lines = out.getvalue().splitlines()
    assert lines[1].index('Spain') == lines[2].index('Spain')


def test_json_output_is_flat():
    args = Args()
    args.json = True
    out = io.StringIO()
    render([an_item()], args, out)
    records = jsonlib.loads(out.getvalue())
    assert records[0]['concept'] == 'electricity'
    assert records[0]['country'] == 'ES'
    assert records[0]['country_label'] == 'Spain'
    assert records[0]['path'].endswith('.pdf')


def test_json_output_with_no_results_is_an_empty_array():
    args = Args()
    args.json = True
    out = io.StringIO()
    render([], args, out)
    assert jsonlib.loads(out.getvalue()) == []


def test_record_keys_are_stable():
    """Scripts depend on these, so a rename is a breaking change."""
    assert set(as_record(an_item())) == {
        'id', 'path', 'date', 'date_label', 'country', 'country_label',
        'group', 'group_label', 'sentby', 'sentby_label', 'purpose',
        'purpose_label', 'concept', 'sentto', 'sentto_label', 'extension',
        'valid', 'active'}


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

DOCS = ['20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf',
        '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf']


def search(miaz_env, make_repo, register_repo, argv, docs=DOCS):
    """Open a one-repository app and run the search command against it."""
    register_repo(miaz_env, 'Work', make_repo('Work', docs), current=True)
    app = MiAZConsoleApp(miaz_env)
    app.open_repository(None)
    out, err = io.StringIO(), io.StringIO()
    code = cmd_search(app, build_parser().parse_args(argv), out, err)
    return code, out.getvalue(), err.getvalue()


def test_search_finds_by_concept(miaz_env, make_repo, register_repo):
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', 'mortgage', '--all'])
    assert code == 0
    assert out.strip().endswith('mortgage-JOHNDOE.pdf')
    assert len(out.splitlines()) == 1


def test_search_with_no_results_exits_1(miaz_env, make_repo, register_repo):
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', 'nothinghere', '--all'])
    assert code == 1
    assert out == ''


def test_results_are_newest_first(miaz_env, make_repo, register_repo):
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all'])
    assert code == 0
    assert out.splitlines()[0].startswith('20260612')


def test_limit(miaz_env, make_repo, register_repo):
    _code, out, _err = search(miaz_env, make_repo, register_repo,
                              ['search', '--all', '--limit', '1'])
    assert len(out.splitlines()) == 1


def test_usage_error_exits_2(miaz_env, make_repo, register_repo):
    code, _out, err = search(miaz_env, make_repo, register_repo,
                             ['search', '--since', 'last-week'])
    assert code == 2
    assert 'last-6-months' in err


def test_empty_result_hints_at_review(miaz_env, make_repo, register_repo):
    """Values the configuration does not know are hidden, as in the workspace.

    An empty result would otherwise read as a broken command.
    """
    code, out, err = search(miaz_env, make_repo, register_repo, ['search'])
    assert code == 1
    assert out == ''
    assert 'need review' in err


# ---------------------------------------------------------------------------
# repos
# ---------------------------------------------------------------------------

def run_repos(miaz_env, argv):
    app = MiAZConsoleApp(miaz_env)
    out, err = io.StringIO(), io.StringIO()
    code = cmd_repos(app, build_parser().parse_args(argv), out, err)
    return code, out.getvalue(), err.getvalue()


def test_repos_lists_names_and_marks_the_current_one(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)
    register_repo(miaz_env, 'Home', make_repo('Home', DOCS[:1]))

    code, out, _err = run_repos(miaz_env, ['repos'])

    assert code == 0
    lines = out.splitlines()
    assert any(line.startswith('Work') and '*' in line for line in lines)
    assert any(line.startswith('Home') and '*' not in line for line in lines)


def test_repos_shows_the_paths(miaz_env, make_repo, register_repo):
    path = make_repo('Work', DOCS)
    register_repo(miaz_env, 'Work', path, current=True)

    _code, out, _err = run_repos(miaz_env, ['repos'])

    assert path in out


def test_repos_json(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)

    _code, out, _err = run_repos(miaz_env, ['repos', '--json'])

    records = jsonlib.loads(out)
    assert records[0]['name'] == 'Work'
    assert records[0]['current'] is True


def test_repos_with_none_configured(miaz_env):
    code, out, err = run_repos(miaz_env, ['repos'])
    assert code == 1
    assert out == ''
    assert err.strip() != ''


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def test_commands_are_the_ones_the_parser_knows():
    assert COMMANDS == {'search', 'repos', 'notes', 'add', 'delete'}


def test_main_runs_a_search(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)
    out, err = io.StringIO(), io.StringIO()

    code = main(['search', '--all'], out, err, env=miaz_env)

    assert code == 0
    assert len(out.getvalue().splitlines()) == 2


def test_main_searches_a_named_repository(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)
    register_repo(miaz_env, 'Home', make_repo('Home', DOCS[:1]))
    out, err = io.StringIO(), io.StringIO()

    code = main(['search', '--all', '--repo', 'Home'], out, err, env=miaz_env)

    assert code == 0
    assert len(out.getvalue().splitlines()) == 1


def test_main_reports_an_unknown_repository(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)
    out, err = io.StringIO(), io.StringIO()

    code = main(['search', '--repo', 'Nope'], out, err, env=miaz_env)

    assert code == 2
    assert 'Work' in err.getvalue()


def test_main_reports_a_repository_problem(miaz_env, tmp_path):
    plain = tmp_path / 'plain'
    plain.mkdir()
    out, err = io.StringIO(), io.StringIO()

    code = main(['search', '--repo', str(plain)], out, err, env=miaz_env)

    assert code == 3
    assert err.getvalue().strip() != ''


def test_main_lists_repositories_without_opening_one(miaz_env, make_repo, register_repo):
    """repos must work even when no repository can be opened."""
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS))
    out, err = io.StringIO(), io.StringIO()

    assert main(['repos'], out, err, env=miaz_env) == 0
    assert 'Work' in out.getvalue()


def test_main_without_a_command_is_a_usage_error(miaz_env):
    out, err = io.StringIO(), io.StringIO()
    assert main([], out, err, env=miaz_env) == 2
    assert 'usage' in err.getvalue()


def test_since_filters_by_date(miaz_env, make_repo, register_repo):
    """A --since search must run the filter, not just build a query.

    The unit tests asserted the bounds were not None, which said nothing about
    whether comparing them against a document date works at all.
    """
    docs = ['20260612-ES-FIN-BANKX-INV-recent-JOHNDOE.pdf',
            '20180101-ES-FIN-BANKX-INV-ancient-JOHNDOE.pdf']
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--since', '2-years'],
                             docs=docs)
    assert code == 0
    assert '20260612' in out
    assert '20180101' not in out


def test_explicit_range_filters_by_date(miaz_env, make_repo, register_repo):
    """--from and --to must run the filter, not just build a query.

    test_explicit_range above only asserted the bounds were set. That said
    nothing about comparing them against a document date, which is where the
    whole flag pair was broken.
    """
    docs = ['20260612-ES-FIN-BANKX-INV-inside-JOHNDOE.pdf',
            '20180101-ES-FIN-BANKX-INV-before-JOHNDOE.pdf',
            '20270101-ES-FIN-BANKX-INV-after-JOHNDOE.pdf']
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--from', '20260101',
                              '--to', '20261231'], docs=docs)
    assert code == 0
    assert 'inside' in out
    assert 'before' not in out
    assert 'after' not in out


def test_from_alone_reaches_forward_without_end(miaz_env, make_repo, register_repo):
    docs = ['20260612-ES-FIN-BANKX-INV-inside-JOHNDOE.pdf',
            '20180101-ES-FIN-BANKX-INV-before-JOHNDOE.pdf',
            '20270101-ES-FIN-BANKX-INV-after-JOHNDOE.pdf']
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--from', '20260101'], docs=docs)
    assert code == 0
    assert 'inside' in out
    assert 'after' in out
    assert 'before' not in out


def test_to_alone_reaches_back_without_start(miaz_env, make_repo, register_repo):
    docs = ['20260612-ES-FIN-BANKX-INV-inside-JOHNDOE.pdf',
            '20180101-ES-FIN-BANKX-INV-before-JOHNDOE.pdf',
            '20270101-ES-FIN-BANKX-INV-after-JOHNDOE.pdf']
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--to', '20261231'], docs=docs)
    assert code == 0
    assert 'inside' in out
    assert 'before' in out
    assert 'after' not in out


def test_a_bound_is_a_date_not_a_datetime():
    """The query model compares against date objects, so the CLI must hand it
    dates. A datetime here does not compare against a date, it raises."""
    query = build_query(parse(['search', '--from', '20240101',
                               '--to', '20241231']), util())
    assert type(query.date_since) is dtdate
    assert type(query.date_until) is dtdate


def test_reversed_range_is_a_usage_error():
    with pytest.raises(UsageError):
        build_query(parse(['search', '--from', '20241231',
                           '--to', '20240101']), util())


# --- --limit takes a count, and a count starts at one ----------------------

def test_limit_zero_is_a_usage_error(miaz_env, make_repo, register_repo):
    code, _out, err = search(miaz_env, make_repo, register_repo,
                             ['search', '--limit', '0'])
    assert code == 2
    assert 'limit' in err.lower()


def test_negative_limit_is_a_usage_error(miaz_env, make_repo, register_repo):
    """--limit -1 used to slice items[:-1], quietly dropping the newest
    document instead of saying the flag made no sense."""
    code, _out, err = search(miaz_env, make_repo, register_repo,
                             ['search', '--limit', '-1'])
    assert code == 2
    assert 'limit' in err.lower()


def test_a_limit_still_cuts_the_list(miaz_env, make_repo, register_repo):
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--limit', '1'])
    assert code == 0
    assert len(out.splitlines()) == 1


# --- the sentinels the query model already understands ---------------------

# Seven fields, of which the country is blank. filename_normalize builds
# exactly this shape for a document dropped in under a name MiAZ did not
# write, so it is what waits in a repository to be filled in.
BLANK_COUNTRY = '20260101--FIN-BANKX-INV-blank-JOHNDOE.pdf'


def test_none_finds_the_documents_with_that_field_empty(miaz_env, make_repo,
                                                        register_repo):
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--country', 'none'],
                             docs=DOCS + [BLANK_COUNTRY])
    assert code == 0
    assert 'blank' in out
    assert 'mortgage' not in out


def test_any_means_every_value_not_a_code_spelled_any(miaz_env, make_repo,
                                                      register_repo):
    """Omitting the flag has always meant Any. Spelling it out went looking
    for a country coded 'ANY' and found nothing."""
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--country', 'any'])
    assert code == 0
    assert len(out.splitlines()) == len(DOCS)


def test_the_sentinels_are_read_whatever_their_case():
    for text in ('none', 'NONE', 'None'):
        query = build_query(parse(['search', '--country', text]), util())
        assert query.country == NONE, f'{text!r} did not reach the sentinel'
    for text in ('any', 'ANY', 'Any'):
        query = build_query(parse(['search', '--country', text]), util())
        assert query.country == ANY, f'{text!r} did not reach the sentinel'


def test_a_field_flag_matches_part_of_a_code(miaz_env, make_repo, register_repo):
    """`--sentby ban` finds BANKX. A person at a terminal types the start of a
    name, not the code as the filename spells it."""
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--sentby', 'ban'])
    assert code == 0
    assert 'BANKX' in out
    assert 'ACME' not in out


def test_two_field_flags_narrow_each_other(miaz_env, make_repo, register_repo):
    """Parts of two fields, and both have to hold."""
    code, out, _err = search(miaz_env, make_repo, register_repo,
                             ['search', '--all', '--sentby', 'ban',
                              '--purpose', 'in'])
    assert code == 0
    assert len(out.splitlines()) == 1
    assert 'mortgage' in out


def test_the_command_line_matches_fields_by_part():
    """The window passes the id of a dropdown entry and means exactly it. The
    command line takes what somebody typed."""
    assert build_query(parse(['search']), util()).partial_fields is True


def test_an_ordinary_code_is_still_upper_cased():
    query = build_query(parse(['search', '--country', 'es']), util())
    assert query.country == 'ES'


# ---------------------------------------------------------------------------
# miaz --help
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_miaz(args, home):
    """The entry point as a user runs it.

    A subprocess because MiAZ.miaz is the entry point: it reads the toolkit
    versions and the environment while it is imported, and --help has to work
    before any of that matters. HOME is a throwaway, so the per-user plugin
    directory is missing, which is the state of a machine that never installed
    a plugin.
    """
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
           'HOME': str(home), 'PYTHONPATH': ROOT, 'LC_ALL': 'C'}
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR'):
        if name in os.environ:
            env[name] = os.environ[name]
    return subprocess.run([sys.executable, '-m', 'MiAZ.miaz'] + args,
                          cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=120)


def test_the_help_lists_every_command(tmp_path):
    """It listed --version and nothing else, so the commands were readable
    only by somebody who already knew their names."""
    result = run_miaz(['--help'], tmp_path)
    assert result.returncode == 0, result.stderr
    for command in COMMANDS:
        assert command in result.stdout, result.stdout


def test_the_help_lists_a_command_a_plugin_contributes(tmp_path):
    """MiAZOCR declares `ocr`. A plugin command is in the help without the
    entry point holding a list of its own."""
    result = run_miaz(['--help'], tmp_path)
    assert 'ocr' in result.stdout, result.stdout


def test_the_help_expands_the_options_of_every_command(tmp_path):
    """A name and one line is an index, not the options. `miaz --help` prints
    each command's own help under the list, so what MiAZ takes is readable in
    one place."""
    result = run_miaz(['--help'], tmp_path)
    for flag in ('--concept', '--pending', '--since',  # search
                 '--json',                             # repos
                 '--language', '--force'):             # ocr, from a plugin
        assert flag in result.stdout, f'{flag} is not in the help'


def test_the_expanded_help_keeps_each_command_usage_line(tmp_path):
    """Every block says which command it belongs to, which is what the usage
    line of a subparser is."""
    result = run_miaz(['--help'], tmp_path)
    for line in ('usage: miaz search', 'usage: miaz repos', 'usage: miaz ocr'):
        assert line in result.stdout, f'{line!r} is not in the help'


def test_the_help_says_what_no_command_does(tmp_path):
    result = run_miaz(['--help'], tmp_path)
    assert 'opens its window' in result.stdout, result.stdout


def test_the_help_still_offers_the_window_options(tmp_path):
    result = run_miaz(['--help'], tmp_path)
    assert '--version' in result.stdout, result.stdout


def test_the_help_says_nothing_about_a_missing_plugin_directory(tmp_path):
    """A machine with no plugin installed for this user has no per-user plugin
    directory, and that is not something to report over the help."""
    result = run_miaz(['--help'], tmp_path)
    assert 'Plugin directory does not exist' not in result.stderr, result.stderr


def test_the_version_is_still_its_own_option(tmp_path):
    result = run_miaz(['--version'], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), 'no version printed'


def test_an_unknown_option_is_refused_with_the_commands(tmp_path):
    result = run_miaz(['--nonsense'], tmp_path)
    assert result.returncode == 2
    assert 'usage: miaz' in result.stderr, result.stderr


# ---------------------------------------------------------------------------
# miaz notes
# ---------------------------------------------------------------------------

NOTED = '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf'
OTHER = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'


def write_note(repo, document_id, stamp, body, category='General',
               status='Draft', priority='Medium', date='2026-01-01 10:00:00'):
    data = notes_dir(repo)
    os.makedirs(data, exist_ok=True)
    path = os.path.join(data, f'{document_id}_{stamp}.md')
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write(f'---\nAuthor: t00m\nCategory: {category}\n'
                      f'Date: {date}\nPriority: {priority}\n'
                      f'Status: {status}\n---\n\n{body}')
    return path


def run_notes(miaz_env, make_repo, register_repo, argv, notes=()):
    """A one-repository app holding these notes, with `miaz notes` run on it."""
    repo = make_repo('Work', DOCS)
    for note in notes:
        write_note(repo, *note[:3], **(note[3] if len(note) > 3 else {}))
    register_repo(miaz_env, 'Work', repo, current=True)
    app = MiAZConsoleApp(miaz_env)
    app.open_repository(None)
    out, err = io.StringIO(), io.StringIO()
    code = cmd_notes(app, build_parser().parse_args(argv), out, err)
    return code, out.getvalue(), err.getvalue()


BOTH_NOTES = (
    (NOTED, '20260101100000', 'the meter was read', {'category': 'OCR',
                                                     'date': '2026-01-01 10:00:00'}),
    (OTHER, '20260301100000', 'call the bank', {'status': 'Finished',
                                                'date': '2026-03-01 09:00:00'}),
)


def test_notes_lists_every_note_newest_first(miaz_env, make_repo, register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes'], notes=BOTH_NOTES)
    assert code == 0
    lines = out.splitlines()
    assert len(lines) == 2
    assert 'call the bank' in lines[0]
    assert 'the meter was read' in lines[1]


def test_a_listed_note_says_which_document_it_belongs_to(miaz_env, make_repo,
                                                         register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes'], notes=BOTH_NOTES)
    assert code == 0
    assert NOTED in out


def test_notes_narrows_by_text(miaz_env, make_repo, register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', 'meter'], notes=BOTH_NOTES)
    assert code == 0
    assert 'the meter was read' in out
    assert 'call the bank' not in out


def test_notes_narrows_by_document(miaz_env, make_repo, register_repo):
    """Part of the document name, the way the search field flags take one."""
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', '--document', 'bankx'],
                                notes=BOTH_NOTES)
    assert code == 0
    assert 'call the bank' in out
    assert 'the meter was read' not in out


def test_notes_narrows_by_the_header_fields(miaz_env, make_repo, register_repo):
    for flag, value, wanted in (('--category', 'ocr', 'the meter was read'),
                                ('--status', 'finish', 'call the bank'),
                                ('--priority', 'medium', None)):
        code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                    ['notes', flag, value], notes=BOTH_NOTES)
        assert code == 0
        if wanted:
            assert wanted in out
            assert len(out.splitlines()) == 1


def test_notes_full_prints_the_note_as_the_file_holds_it(miaz_env, make_repo,
                                                         register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', 'meter', '--full'], notes=BOTH_NOTES)
    assert code == 0
    path = out.splitlines()[0]
    with open(path, encoding='utf-8') as handler:
        assert handler.read().strip() in out
    assert 'Category: OCR' in out


def test_notes_json_carries_the_body(miaz_env, make_repo, register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', '--json'], notes=BOTH_NOTES)
    assert code == 0
    records = jsonlib.loads(out)
    assert len(records) == 2
    assert records[0]['document'] == OTHER
    assert 'call the bank' in records[0]['body']
    assert records[0]['category'] == 'General'
    assert records[0]['path'].endswith('.md')


def test_notes_long_prints_a_table(miaz_env, make_repo, register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', '--long'], notes=BOTH_NOTES)
    assert code == 0
    assert out.splitlines()[0].split() == ['DATE', 'DOCUMENT', 'CATEGORY',
                                           'PRIORITY', 'STATUS', 'SUMMARY']


def test_notes_limit_cuts_the_list(miaz_env, make_repo, register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', '--limit', '1'], notes=BOTH_NOTES)
    assert code == 0
    assert len(out.splitlines()) == 1


def test_notes_with_nothing_matching_exits_1(miaz_env, make_repo, register_repo):
    code, out, _err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', 'nothinglikeit'], notes=BOTH_NOTES)
    assert code == 1
    assert out == ''


def test_notes_says_when_the_repository_has_none(miaz_env, make_repo,
                                                 register_repo):
    """Silence reads as a broken command. An empty repository is not that."""
    code, out, err = run_notes(miaz_env, make_repo, register_repo, ['notes'])
    assert code == 1
    assert out == ''
    assert 'no notes' in err.lower()


def test_notes_refuses_a_limit_below_one(miaz_env, make_repo, register_repo):
    code, _out, err = run_notes(miaz_env, make_repo, register_repo,
                                ['notes', '--limit', '0'], notes=BOTH_NOTES)
    assert code == 2
    assert '--limit' in err


# ---------------------------------------------------------------------------
# miaz add and miaz delete
# ---------------------------------------------------------------------------

def run_cli(miaz_env, make_repo, register_repo, argv, docs=DOCS):
    """Open a one-repository app and run whichever command argv names.

    Returns the exit code, what was written to each stream, and the repository
    path, since these two commands are judged by what is on disk afterwards.
    """
    repo = make_repo('Work', docs)
    register_repo(miaz_env, 'Work', repo, current=True)
    app = MiAZConsoleApp(miaz_env)
    app.open_repository(None)
    # argv can be a callable, for the tests that need the repository path
    # inside the arguments they pass.
    args = build_parser().parse_args(argv(repo) if callable(argv) else argv)
    out, err = io.StringIO(), io.StringIO()
    code = HANDLERS[args.command](app, args, out, err)
    return code, out.getvalue(), err.getvalue(), repo


class FakeTerminal:
    """A stdin that says it is a terminal and answers what it was given."""

    def __init__(self, answer):
        self.answer = answer

    def isatty(self):
        return True

    def readline(self):
        return f'{self.answer}\n'


def a_file(tmp_path, name, text='document'):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_add_copies_a_file_in_under_a_normalized_name(miaz_env, make_repo,
                                                      register_repo, tmp_path):
    source = a_file(tmp_path, 'bank statement.pdf')
    code, out, _err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['add', source])
    assert code == 0
    assert out.strip() == '-----BANK_STATEMENT-.pdf'
    assert os.path.exists(os.path.join(repo, '-----BANK_STATEMENT-.pdf'))


def test_add_leaves_the_source_where_it_is(miaz_env, make_repo, register_repo,
                                           tmp_path):
    source = a_file(tmp_path, 'invoice.pdf')
    run_cli(miaz_env, make_repo, register_repo, ['add', source])
    assert os.path.exists(source)


def test_add_takes_a_directory(miaz_env, make_repo, register_repo, tmp_path):
    os.makedirs(tmp_path / 'inbox' / 'sub')
    a_file(tmp_path, 'inbox/one.pdf')
    a_file(tmp_path, 'inbox/two.pdf')
    a_file(tmp_path, 'inbox/sub/three.pdf')

    code, out, _err, _repo = run_cli(miaz_env, make_repo, register_repo,
                                     ['add', str(tmp_path / 'inbox')])
    assert code == 0
    assert len(out.splitlines()) == 2


def test_add_recursive_takes_the_whole_tree(miaz_env, make_repo, register_repo,
                                            tmp_path):
    os.makedirs(tmp_path / 'inbox' / 'sub')
    a_file(tmp_path, 'inbox/one.pdf')
    a_file(tmp_path, 'inbox/sub/two.pdf')

    code, out, _err, _repo = run_cli(miaz_env, make_repo, register_repo,
                                     ['add', str(tmp_path / 'inbox'), '--recursive'])
    assert code == 0
    assert len(out.splitlines()) == 2


def test_add_names_what_it_could_not_take(miaz_env, make_repo, register_repo,
                                          tmp_path):
    """A path that is not there is reported, and the rest still arrive."""
    good = a_file(tmp_path, 'invoice.pdf')
    missing = str(tmp_path / 'gone.pdf')
    code, out, err, _repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['add', missing, good])
    assert code == 1
    assert '-----INVOICE-.pdf' in out
    assert 'gone.pdf' in err


def test_add_with_nothing_to_take_says_so(miaz_env, make_repo, register_repo,
                                          tmp_path):
    os.makedirs(tmp_path / 'empty')
    code, out, err, _repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['add', str(tmp_path / 'empty')])
    assert code == 1
    assert out == ''
    assert err.strip() != ''


def test_delete_removes_the_document(miaz_env, make_repo, register_repo):
    code, out, _err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', DOCS[0], '--yes'])
    assert code == 0
    assert DOCS[0] in out
    assert not os.path.exists(os.path.join(repo, DOCS[0]))
    assert os.path.exists(os.path.join(repo, DOCS[1]))


def test_delete_takes_several_documents(miaz_env, make_repo, register_repo):
    code, out, _err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', DOCS[0], DOCS[1], '--yes'])
    assert code == 0
    assert len(out.splitlines()) == 2
    assert os.listdir(repo) == ['.conf']


def test_delete_refuses_a_document_the_repository_does_not_hold(
        miaz_env, make_repo, register_repo):
    """And deletes nothing at all: a typo in a list must not take the
    documents that were spelled right."""
    code, _out, err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', DOCS[0], 'nosuch.pdf', '--yes'])
    assert code == 2
    assert 'nosuch.pdf' in err
    assert os.path.exists(os.path.join(repo, DOCS[0]))


def test_delete_without_a_terminal_needs_yes(miaz_env, make_repo, register_repo):
    """In a pipe there is nobody to ask, so it refuses rather than assuming."""
    code, _out, err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', DOCS[0]])
    assert code == 2
    assert '--yes' in err
    assert os.path.exists(os.path.join(repo, DOCS[0]))


def test_delete_asks_on_a_terminal_and_takes_yes(miaz_env, make_repo,
                                                 register_repo, monkeypatch):
    monkeypatch.setattr(sys, 'stdin', FakeTerminal('y'))
    code, _out, err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', DOCS[0]])
    assert code == 0
    assert DOCS[0] in err, 'the question has to say what it will delete'
    assert not os.path.exists(os.path.join(repo, DOCS[0]))


def test_delete_asks_on_a_terminal_and_takes_no(miaz_env, make_repo,
                                                register_repo, monkeypatch):
    monkeypatch.setattr(sys, 'stdin', FakeTerminal('n'))
    code, out, _err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', DOCS[0]])
    assert code == 1
    assert out == ''
    assert os.path.exists(os.path.join(repo, DOCS[0]))


def test_delete_takes_a_path_inside_the_repository(miaz_env, make_repo,
                                                   register_repo):
    """A pipeline gives a name and tab completion gives a path. Both name the
    same document."""
    code, _out, _err, repo = run_cli(
        miaz_env, make_repo, register_repo,
        lambda repo: ['delete', os.path.join(repo, DOCS[0]), '--yes'])
    assert code == 0
    assert not os.path.exists(os.path.join(repo, DOCS[0]))


def test_delete_refuses_a_path_outside_the_repository(miaz_env, make_repo,
                                                      register_repo, tmp_path):
    """A path somewhere else names a different file that happens to share a
    name. Deleting the repository's copy of it would be a guess."""
    outside = a_file(tmp_path, DOCS[0])
    code, _out, err, repo = run_cli(miaz_env, make_repo, register_repo,
                                    ['delete', outside, '--yes'])
    assert code == 2
    assert os.path.exists(os.path.join(repo, DOCS[0]))
    assert os.path.exists(outside)
    assert DOCS[0] in err


# A document with no fields yet is named -----CONCEPT-.pdf, and argparse reads
# a leading dash as an option. These go through main(), which is where the
# names are folded back in.

PENDING = '-----SCAN-.pdf'


def run_main(miaz_env, make_repo, register_repo, argv, docs=DOCS):
    repo = make_repo('Work', docs)
    register_repo(miaz_env, 'Work', repo, current=True)
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, out, err, env=miaz_env)
    return code, out.getvalue(), err.getvalue(), repo


def test_delete_takes_a_document_whose_name_starts_with_a_dash(
        miaz_env, make_repo, register_repo):
    """`miaz search --pending` prints nothing else, and piping that into
    delete used to fail on every one of them."""
    code, out, _err, repo = run_main(miaz_env, make_repo, register_repo,
                                     ['delete', PENDING, '--yes'],
                                     docs=DOCS + [PENDING])
    assert code == 0
    assert PENDING in out
    assert not os.path.exists(os.path.join(repo, PENDING))


def test_a_flag_after_a_dashed_name_is_still_a_flag(miaz_env, make_repo,
                                                    register_repo):
    """The `--` argparse understands would have swallowed it."""
    code, _out, _err, repo = run_main(miaz_env, make_repo, register_repo,
                                      ['delete', PENDING, '--yes'],
                                      docs=DOCS + [PENDING])
    assert code == 0, 'the --yes after the name was read as a document'


def test_a_mistyped_flag_is_still_an_error(miaz_env, make_repo, register_repo):
    with pytest.raises(SystemExit) as exit_info:
        run_main(miaz_env, make_repo, register_repo,
                 ['delete', PENDING, '--yess'], docs=DOCS + [PENDING])
    assert exit_info.value.code == 2


def test_a_dashed_name_given_to_a_command_that_takes_none_is_an_error(
        miaz_env, make_repo, register_repo):
    with pytest.raises(SystemExit) as exit_info:
        run_main(miaz_env, make_repo, register_repo, ['search', PENDING])
    assert exit_info.value.code == 2


def test_delete_with_no_document_named_says_so(miaz_env, make_repo,
                                               register_repo):
    code, out, err, _repo = run_main(miaz_env, make_repo, register_repo,
                                     ['delete'])
    assert code == 2
    assert out == ''
    assert err.strip() != ''


def test_add_with_no_path_named_says_so(miaz_env, make_repo, register_repo):
    code, out, err, _repo = run_main(miaz_env, make_repo, register_repo,
                                     ['add'])
    assert code == 2
    assert out == ''
    assert err.strip() != ''
