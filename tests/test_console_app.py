#!/usr/bin/python3

"""
Tests for the console application shell.

Runs without a display: GObject and Gio only, no GTK. That is the whole point
of the shell, so a failure here means the command line has grown a dependency
it cannot have.
"""

import json

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from MiAZ.frontend.console.app import MiAZConsoleApp

DOCS = ['20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf',
        '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf']


def test_services_are_registered(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)

    app = MiAZConsoleApp(miaz_env)
    code, message = app.open_repository(None)

    assert (code, message) == (0, '')
    assert app.get_service('util') is not None
    assert app.get_service('repo') is not None
    assert len(app.get_service('index').documents()) == 2


def test_named_repository_wins_over_current(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)
    register_repo(miaz_env, 'Home', make_repo('Home', DOCS[:1]))

    app = MiAZConsoleApp(miaz_env)

    assert app.open_repository('Home') == (0, '')
    assert len(app.get_service('index').documents()) == 1


def test_opening_a_repository_leaves_the_default_alone(miaz_env, make_repo, register_repo):
    """Searching another repository must not move the one the app opens."""
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)
    register_repo(miaz_env, 'Home', make_repo('Home', DOCS[:1]))

    MiAZConsoleApp(miaz_env).open_repository('Home')

    with open(miaz_env['FILE']['CONF'], encoding='utf-8') as handler:
        assert json.load(handler)['current'] == 'Work'


def test_repository_by_path(miaz_env, make_repo):
    path = make_repo('Loose', DOCS)
    app = MiAZConsoleApp(miaz_env)

    assert app.open_repository(path) == (0, '')
    assert len(app.get_service('index').documents()) == 2


def test_unknown_name_is_a_usage_error(miaz_env, make_repo, register_repo):
    register_repo(miaz_env, 'Work', make_repo('Work', DOCS), current=True)

    code, message = MiAZConsoleApp(miaz_env).open_repository('Nope')

    assert code == 2
    assert 'Work' in message


def test_directory_without_repo_json(miaz_env, tmp_path):
    plain = tmp_path / 'plain'
    plain.mkdir()

    code, message = MiAZConsoleApp(miaz_env).open_repository(str(plain))

    assert code == 3
    assert str(plain) in message


def test_no_repository_configured(miaz_env):
    code, _message = MiAZConsoleApp(miaz_env).open_repository(None)
    assert code == 3
