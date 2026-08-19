#!/usr/bin/python3

"""
Tests for MiAZ.backend.repository — validate() and init() — using tmp_path.
Runs without a display (GObject only, no GTK/Adw).
"""

import json
import os
import shutil

import gi
gi.require_version('GLib', '2.0')

from MiAZ.backend.repository import MiAZRepository
from MiAZ.backend.util import MiAZUtil

DEFAULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data', 'resources', 'conf')


class MockAppConfig:
    """Minimal stand-in for a MiAZConfig entry that only needs .set()."""
    def __init__(self):
        self._data = {}

    def set(self, key, value):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)


class MockApp:
    """Stand-in for the real app object used by MiAZRepository."""

    def __init__(self):
        self._config = {
            'App': MockAppConfig(),
        }

    def get_config_dict(self):
        return self._config


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------

def test_validate_empty_directory(tmp_path):
    repo = MiAZRepository(MockApp())
    assert repo.validate(str(tmp_path)) is False


def test_validate_conf_dir_only_no_json(tmp_path):
    conf_dir = tmp_path / '.conf'
    conf_dir.mkdir()
    repo = MiAZRepository(MockApp())
    assert repo.validate(str(tmp_path)) is False


def test_validate_empty_path_string(tmp_path):
    repo = MiAZRepository(MockApp())
    assert repo.validate('') is False


def test_validate_invalid_json(tmp_path):
    conf_dir = tmp_path / '.conf'
    conf_dir.mkdir()
    repo_json = conf_dir / 'repo.json'
    repo_json.write_text('NOT VALID JSON }{')
    repo = MiAZRepository(MockApp())
    assert repo.validate(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# init() + validate()
# ---------------------------------------------------------------------------

def test_init_creates_valid_repository(tmp_path):
    repo = MiAZRepository(MockApp())
    repo.init(str(tmp_path))
    assert repo.validate(str(tmp_path)) is True


def test_init_creates_conf_directory(tmp_path):
    repo = MiAZRepository(MockApp())
    repo.init(str(tmp_path))
    assert (tmp_path / '.conf').is_dir()


def test_init_creates_repo_json(tmp_path):
    repo = MiAZRepository(MockApp())
    repo.init(str(tmp_path))
    repo_json = tmp_path / '.conf' / 'repo.json'
    assert repo_json.exists()
    with open(repo_json) as fh:
        data = json.load(fh)
    assert data.get('FORMAT') == 1


def test_init_creates_default_plugins_file(tmp_path):
    repo = MiAZRepository(MockApp())
    repo.init(str(tmp_path))
    plugins_file = tmp_path / '.conf' / 'plugins-used.json'
    assert plugins_file.exists()
    with open(plugins_file) as fh:
        data = json.load(fh)
    assert isinstance(data, dict)
    assert len(data) > 0


def test_init_records_source_path(tmp_path):
    app = MockApp()
    repo = MiAZRepository(app)
    repo.init(str(tmp_path))
    assert app.get_config_dict()['App'].get('source') == str(tmp_path)


def test_validate_after_init_on_separate_instance(tmp_path):
    """validate() must work on a freshly constructed repository object."""
    repo_a = MiAZRepository(MockApp())
    repo_a.init(str(tmp_path))

    repo_b = MiAZRepository(MockApp())
    assert repo_b.validate(str(tmp_path)) is True


# ---------------------------------------------------------------------------
# load() and the per-repository config store
# ---------------------------------------------------------------------------

class MockRepoConfig:
    """Stand-in for MiAZConfigRepositories: id -> filesystem path."""

    def __init__(self):
        self._repos = {}

    def add(self, key, path):
        self._repos[key] = path

    def load_used(self):
        return dict(self._repos)

    def get_path(self, key, used=True):
        return self._repos.get(key, '')


class StoreApp(MockApp):
    """MockApp plus what setup() and MiAZConfigStore need."""

    def __init__(self):
        super().__init__()
        self._config['Repository'] = MockRepoConfig()
        self._util = MiAZUtil(self)

    def get_service(self, name):
        if name == 'util':
            return self._util
        return None

    def get_env(self):
        return {'GPATH': {'CONF': DEFAULTS}}


def make_repository(tmp_path, *names):
    """A repository knowing about one or more repos, switched to the first."""
    app = StoreApp()
    confs = {}
    for name in names:
        docs = tmp_path / name
        conf = docs / '.conf'
        conf.mkdir(parents=True, exist_ok=True)
        app.get_config_dict()['Repository'].add(name, str(docs))
        confs[name] = str(conf)
    app.get_config_dict()['App'].set('current', names[0])
    return MiAZRepository(app), confs


def switch_to(repo, name):
    """Point the repository at another configured repo and load it."""
    repo.app.get_config_dict()['App'].set('current', name)
    repo.reset()
    repo.load()


def write_used(dir_conf, filename, items):
    with open(os.path.join(dir_conf, filename), 'w', encoding='utf-8') as handler:
        json.dump(items, handler)


def test_load_publishes_the_configs_into_the_app_registry(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo')
    repo.load()
    config = repo.app.get_config_dict()
    for name in ('Country', 'Group', 'Purpose', 'Concept',
                 'SentBy', 'SentTo', 'Person', 'Plugin'):
        assert config.get(name) is not None, name


def test_load_keeps_the_app_scoped_configs(tmp_path):
    """The store publishes into the same dict that holds App and Repository."""
    repo, _confs = make_repository(tmp_path, 'repo')
    before = repo.app.get_config_dict()['App']
    repo.load()
    assert repo.app.get_config_dict()['App'] is before


def test_switching_repositories_reads_the_new_one_from_disk(tmp_path):
    """The bug this store exists for: the cache used to be a class attribute,
    so entries written before a switch were still there after it.
    """
    repo, confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    write_used(confs['repo_a'], 'countries-used.json', {'ES': 'Spain'})
    write_used(confs['repo_b'], 'countries-used.json', {'FR': 'France'})

    repo.load()
    assert repo.get_config_store().get('Country').load_used() == {'ES': 'Spain'}

    switch_to(repo, 'repo_b')
    assert repo.get_config_store().get('Country').load_used() == {'FR': 'France'}


def test_switching_back_re_reads_a_repository_changed_meanwhile(tmp_path):
    """Switch away, the repository changes on disk, switch back."""
    repo, confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    write_used(confs['repo_a'], 'countries-used.json', {'ES': 'Spain'})
    repo.load()
    repo.get_config_store().get('Country').load_used()

    switch_to(repo, 'repo_b')
    write_used(confs['repo_a'], 'countries-used.json', {'PT': 'Portugal'})

    switch_to(repo, 'repo_a')
    assert repo.get_config_store().get('Country').load_used() == {'PT': 'Portugal'}


def test_load_disposes_the_previous_store(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    repo.load()
    first = repo.get_config_store()
    first.get('Country').load_used()

    switch_to(repo, 'repo_b')

    assert first.cache == {}
    assert repo.get_config_store() is not first


def test_get_config_store_is_none_before_any_load(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo')
    assert repo.get_config_store() is None


# ---------------------------------------------------------------------------
# use()
# ---------------------------------------------------------------------------

def test_use_named_repository(tmp_path):
    repo, confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    assert repo.use('repo_b') is True
    assert repo.docs == str(tmp_path / 'repo_b')
    assert repo.conf == confs['repo_b']


def test_use_does_not_change_the_current_repository(tmp_path):
    """Reading another repository must not move the one the app opens."""
    repo, _confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    repo.use('repo_b')
    assert repo.app.get_config_dict()['App'].get('current') == 'repo_a'


def test_use_unknown_name(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a')
    assert repo.use('nope') is False


def test_use_unknown_name_creates_nothing(tmp_path, monkeypatch):
    """An unresolved name must not reach init(), which would makedirs('.conf')."""
    monkeypatch.chdir(tmp_path)
    repo, _confs = make_repository(tmp_path, 'repo_a')
    repo.use('nope')
    assert not (tmp_path / '.conf').exists()


def test_use_path(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a')
    somewhere = tmp_path / 'usb'
    (somewhere / '.conf').mkdir(parents=True)
    assert repo.use(path=str(somewhere)) is True
    assert repo.docs == str(somewhere)
    assert repo.conf == str(somewhere / '.conf')


def test_use_nothing(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a')
    assert repo.use() is False


def test_use_survives_load(tmp_path):
    """load() must not re-resolve the repository the caller chose.

    It used to clear the conf cache on entry, so the next lookup fell back to
    'current' and loaded a different repository than the one requested.
    """
    repo, confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    repo.use('repo_b')
    repo.load(repo.docs)
    assert repo.docs == str(tmp_path / 'repo_b')
    assert repo.conf == confs['repo_b']


# ---------------------------------------------------------------------------
# get_active_id(): which repository is being shown right now
#
# It is not always the default one. Switching without setting the default
# points the repository elsewhere while 'current' still names what MiAZ opens
# on the next start, and the window title, the sidebar and the settings all
# have to name the one on screen.
# ---------------------------------------------------------------------------

def test_active_id_is_the_default_when_nothing_else_was_chosen(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    assert repo.get_active_id() == 'repo_a'


def test_active_id_follows_use(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    repo.use('repo_b')
    assert repo.get_active_id() == 'repo_b'
    assert repo.app.get_config_dict()['App'].get('current') == 'repo_a'


def test_active_id_survives_load(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    repo.use('repo_b')
    repo.load(repo.docs)
    assert repo.get_active_id() == 'repo_b'


def test_active_id_falls_back_to_the_default_after_reset(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a', 'repo_b')
    repo.use('repo_b')
    repo.reset()
    assert repo.get_active_id() == 'repo_a'


def test_active_id_of_a_path_without_a_name(tmp_path):
    """use(path=...) has no registered name, so the default one is not claimed."""
    repo, _confs = make_repository(tmp_path, 'repo_a')
    somewhere = tmp_path / 'usb'
    (somewhere / '.conf').mkdir(parents=True)
    repo.use(path=str(somewhere))
    assert repo.get_active_id() is None


def test_active_id_when_no_repository_is_configured(tmp_path):
    app = StoreApp()
    repo = MiAZRepository(app)
    assert repo.get_active_id() is None


# ---------------------------------------------------------------------------
# setup(): a repository whose directory is gone
#
# Renaming or unmounting a repository directory used to be silent: setup()
# initialised whatever path was configured, and os.makedirs recreated the
# directory itself, so MiAZ opened an empty repository with empty
# configuration where the documents used to be.
# ---------------------------------------------------------------------------

def test_setup_does_not_recreate_a_missing_repository_directory(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a')
    gone = tmp_path / 'repo_a'
    shutil.rmtree(gone)

    repo.reset()
    repo.setup()

    assert not gone.exists(), 'the repository directory was recreated'


def test_setup_reports_a_missing_repository_directory(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a')
    shutil.rmtree(tmp_path / 'repo_a')

    repo.reset()
    repo.setup()

    error = repo.get_error()
    assert error is not None
    assert 'repo_a' in str(error) or str(tmp_path / 'repo_a') in str(error)


def test_a_missing_repository_does_not_validate(tmp_path):
    repo, _confs = make_repository(tmp_path, 'repo_a')
    shutil.rmtree(tmp_path / 'repo_a')

    repo.reset()
    assert repo.validate(repo.docs) is False


def test_setup_still_initialises_an_existing_directory(tmp_path):
    """A repository added through the assistant points at a folder that
    exists and has no .conf yet. That one is still set up here."""
    app = StoreApp()
    docs = tmp_path / 'brand_new'
    docs.mkdir()
    app.get_config_dict()['Repository'].add('brand_new', str(docs))
    app.get_config_dict()['App'].set('current', 'brand_new')

    repo = MiAZRepository(app)
    assert repo.validate(repo.docs) is True
    assert (docs / '.conf' / 'repo.json').exists()
