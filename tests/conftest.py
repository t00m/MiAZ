#!/usr/bin/python3

"""
Shared fixtures for the headless console tests.

The console app and the command line both need a repository on disk and an
environment pointing at it. The config layer reads exactly three environment
keys, so these fixtures are complete: nothing here touches the real ~/.MiAZ.
"""

import json
import os

import pytest

# The defaults each config copies into a fresh repository.
DEFAULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data', 'resources', 'conf')


@pytest.fixture
def miaz_env(tmp_path):
    """The ENV keys the config layer reads, pointed at a temp directory."""
    etc = tmp_path / 'etc'
    etc.mkdir(parents=True, exist_ok=True)
    return {
        'APP': {'ID': 'io.github.t00m.MiAZ', 'name': 'MiAZ', 'VERSION': '0.0.0'},
        'FILE': {'CONF': str(etc / 'MiAZ-application.json')},
        'LPATH': {'ETC': str(etc)},
        'GPATH': {'CONF': DEFAULTS},
    }


@pytest.fixture
def make_repo(tmp_path):
    """Build a repository directory holding the given documents."""
    def build(name, filenames=()):
        root = tmp_path / name
        conf = root / '.conf'
        conf.mkdir(parents=True, exist_ok=True)
        (conf / 'repo.json').write_text(json.dumps({'FORMAT': 1}))
        for filename in filenames:
            (root / filename).write_text('x')
        return str(root)
    return build


@pytest.fixture
def register_repo():
    """Write a repository into repos-used.json, the way the app does."""
    def register(env, name, path, current=False):
        used = os.path.join(env['LPATH']['ETC'], 'repos-used.json')
        repos = {}
        if os.path.exists(used):
            with open(used, encoding='utf-8') as handler:
                repos = json.load(handler)
        repos[name] = {'description': name, 'path': path}
        with open(used, 'w', encoding='utf-8') as handler:
            json.dump(repos, handler)
        if current:
            with open(env['FILE']['CONF'], 'w', encoding='utf-8') as handler:
                json.dump({'current': name, 'source': path}, handler)
    return register
