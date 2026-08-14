#!/usr/bin/python3

"""
Tests for the command line: argument parsing and query building.

The point of these is that the CLI writes no filter conditions of its own. A
flag either sets a DocumentQuery field or it is a mistake.
"""

import io
import json as jsonlib

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

import pytest

from MiAZ.backend.models import MiAZItem
from MiAZ.backend.query import ANY, DATE_RANGE, DocumentQuery
from MiAZ.backend.util import MiAZUtil
from MiAZ.frontend.console.app import MiAZConsoleApp
from MiAZ.frontend.console.cli import (COMMANDS, UsageError, as_record,
                                       build_parser, build_query, cmd_repos,
                                       cmd_search, main, render)


class NoServices:
    def get_service(self, name):
        return None


def util():
    """MiAZUtil owns the date helpers resolve_preset needs."""
    return MiAZUtil(NoServices())


def parse(argv):
    return build_parser().parse_args(argv)


def test_defaults_match_an_empty_query():
    assert build_query(parse(['search']), util()) == DocumentQuery()


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
    by_hand = DocumentQuery(search='x', country='ES', only_pending=True)
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
    assert COMMANDS == {'search', 'repos'}


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
