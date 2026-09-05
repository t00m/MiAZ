#!/usr/bin/python3

"""
Tests for MiAZ.backend.config.MiAZConfigStore — the per-repository config owner.

The cache used to be a class attribute on MiAZConfig, shared by every instance in
the process and keyed by absolute filepath. That made the configs of a repository
agree with each other, which was the point, but it also outlived the repository:
switching away and back read entries written before the switch.
"""

import json
import os

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

import pytest

from MiAZ.backend.config import MiAZConfig, MiAZConfigStore
from MiAZ.backend.util import MiAZUtil

# The defaults each config copies into a fresh repository.
DEFAULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data', 'resources', 'conf')


class MockApp:
    def __init__(self):
        self._util = MiAZUtil(self)

    def get_service(self, name):
        if name == 'util':
            return self._util
        return None

    def get_env(self):
        return {'GPATH': {'CONF': DEFAULTS}}


@pytest.fixture
def app():
    return MockApp()


def conf_dir(tmp_path, name='repo'):
    path = tmp_path / name / '.conf'
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


# ---------------------------------------------------------------------------
# What the store holds
# ---------------------------------------------------------------------------

def test_the_store_builds_every_repository_config(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    expected = {'Country', 'Group', 'Purpose', 'Concept',
                'SentBy', 'SentTo', 'Person', 'Plugin'}
    assert set(store.names()) == expected


def test_get_returns_a_config(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    assert isinstance(store.get('Country'), MiAZConfig)


def test_get_returns_the_same_instance_every_time(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    assert store.get('Country') is store.get('Country')


def test_get_returns_none_for_an_unknown_name(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    assert store.get('Nonexistent') is None


def test_as_dict_exposes_every_config_by_name(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    as_dict = store.as_dict()
    assert as_dict['Country'] is store.get('Country')


# ---------------------------------------------------------------------------
# One cache per repository
# ---------------------------------------------------------------------------

def test_the_configs_of_one_repository_share_a_cache(app, tmp_path):
    """SentBy, SentTo and Person all read people-available.json. Divergent
    copies are what dropped entries one of them had just added.
    """
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    store.get('SentBy').add_available('personalpha', 'Person Alpha')
    assert store.get('SentTo').exists_available('personalpha') is True


def test_two_repositories_do_not_share_a_cache(app, tmp_path):
    store_a = MiAZConfigStore(app, conf_dir(tmp_path, 'repo_a'))
    store_b = MiAZConfigStore(app, conf_dir(tmp_path, 'repo_b'))
    store_a.get('Country').load_used()
    assert store_a.cache is not store_b.cache


def test_the_cache_is_not_a_class_attribute(app, tmp_path):
    """A class attribute is what tied the cache lifetime to the process."""
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    store.get('Country').load_used()
    assert not hasattr(MiAZConfig, 'cache')


# ---------------------------------------------------------------------------
# The repository switch
# ---------------------------------------------------------------------------

def write_used(dir_conf, filename, items):
    with open(os.path.join(dir_conf, filename), 'w', encoding='utf-8') as handler:
        json.dump(items, handler)


def test_a_new_store_reads_the_repository_from_disk(app, tmp_path):
    """Switch away, the repository changes underneath, switch back. The second
    store must show what is on disk, not what the first one had cached.
    """
    dir_conf = conf_dir(tmp_path)
    write_used(dir_conf, 'countries-used.json', {'ES': 'Spain'})

    store_one = MiAZConfigStore(app, dir_conf)
    assert store_one.get('Country').load_used() == {'ES': 'Spain'}
    store_one.dispose()

    write_used(dir_conf, 'countries-used.json', {'FR': 'France'})

    store_two = MiAZConfigStore(app, dir_conf)
    assert store_two.get('Country').load_used() == {'FR': 'France'}


def test_dispose_empties_the_cache(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    store.get('Country').load_used()
    assert store.cache != {}
    store.dispose()
    assert store.cache == {}


def test_dispose_drops_the_configs(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    store.get('Country')
    store.dispose()
    assert store.names() == []


def test_dispose_is_safe_to_call_twice(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    store.dispose()
    store.dispose()
    assert store.cache == {}


# ---------------------------------------------------------------------------
# The store creates a usable repository configuration
# ---------------------------------------------------------------------------

def test_the_store_seeds_the_available_pools_from_the_defaults(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    assert len(store.get('Country').load_available()) > 0


def test_the_store_creates_the_used_files_empty(app, tmp_path):
    store = MiAZConfigStore(app, conf_dir(tmp_path))
    assert store.get('Country').load_used() == {}


# ---------------------------------------------------------------------------
# One person, four files
# ---------------------------------------------------------------------------

def read_json(dir_conf, filename):
    with open(os.path.join(dir_conf, filename), encoding='utf-8') as handler:
        return json.load(handler)


def seed_person(dir_conf, key='ADAC', description='ADAC'):
    """One person in every file that can hold them, described by their own key,
    which is the state the health check calls undescribed."""
    for filename in ('people-available.json', 'people-used.json',
                     'senders-used.json', 'recipients-used.json'):
        write_used(dir_conf, filename, {key: description})


def test_a_description_set_on_a_sender_reaches_every_people_file(app, tmp_path):
    """A person is the same person whether a document was sent by them or to
    them. The description lives in four files and has to agree in all of them.
    """
    dir_conf = conf_dir(tmp_path)
    seed_person(dir_conf)
    store = MiAZConfigStore(app, dir_conf)

    store.get('SentBy').set_description('ADAC', 'ADAC e.V.')

    for filename in ('people-available.json', 'people-used.json',
                     'senders-used.json', 'recipients-used.json'):
        assert read_json(dir_conf, filename) == {'ADAC': 'ADAC e.V.'}, filename


def test_a_description_set_on_a_person_reaches_the_senders(app, tmp_path):
    """The repository manager edits Person, and the workspace reads senders."""
    dir_conf = conf_dir(tmp_path)
    seed_person(dir_conf)
    store = MiAZConfigStore(app, dir_conf)

    store.get('Person').set_description('ADAC', 'ADAC e.V.')

    assert read_json(dir_conf, 'senders-used.json') == {'ADAC': 'ADAC e.V.'}
    assert read_json(dir_conf, 'recipients-used.json') == {'ADAC': 'ADAC e.V.'}


def test_a_description_is_not_written_where_the_key_is_absent(app, tmp_path):
    """Writing a description says what a key means, never that it is in use:
    a person nothing was sent to does not become a recipient by being named.
    """
    dir_conf = conf_dir(tmp_path)
    write_used(dir_conf, 'people-available.json', {'ADAC': 'ADAC'})
    write_used(dir_conf, 'senders-used.json', {'ADAC': 'ADAC'})
    write_used(dir_conf, 'recipients-used.json', {})
    store = MiAZConfigStore(app, dir_conf)

    store.get('SentBy').set_description('ADAC', 'ADAC e.V.')

    assert read_json(dir_conf, 'recipients-used.json') == {}
    assert read_json(dir_conf, 'senders-used.json') == {'ADAC': 'ADAC e.V.'}


def test_a_country_description_stays_among_the_countries(app, tmp_path):
    """Only the people configurations share a vocabulary."""
    dir_conf = conf_dir(tmp_path)
    write_used(dir_conf, 'countries-used.json', {'ES': 'ES'})
    write_used(dir_conf, 'people-available.json', {'ES': 'ES'})
    store = MiAZConfigStore(app, dir_conf)

    store.get('Country').set_description('ES', 'Spain')

    assert read_json(dir_conf, 'countries-used.json') == {'ES': 'Spain'}
    assert read_json(dir_conf, 'people-available.json') == {'ES': 'ES'}


def test_setting_a_description_says_whether_anything_changed(app, tmp_path):
    dir_conf = conf_dir(tmp_path)
    seed_person(dir_conf)
    store = MiAZConfigStore(app, dir_conf)

    assert store.get('SentBy').set_description('ADAC', 'ADAC e.V.') is True
    assert store.get('SentBy').set_description('ADAC', 'ADAC e.V.') is False
    assert store.get('SentBy').set_description('NOBODY', 'Nobody') is False
