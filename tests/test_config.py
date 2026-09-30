#!/usr/bin/python3

"""
Tests for MiAZ.backend.config.MiAZConfig — using tmp_path.
Runs without a display (GObject only, no GTK/Adw).

MockApp supplies a real MiAZUtil instance because MiAZConfig delegates
json_load/json_save to util.  MiAZUtil.__init__ only stores self.app, so any
object is acceptable as its app argument.
"""

import os

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from MiAZ.backend.config import MiAZConfig, changed_keys
from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.log import MiAZLog


class _UtilApp:
    """Minimal app for MiAZUtil (none of the tested methods call self.app)."""
    pass


class MockApp:
    """App stub that returns a live MiAZUtil from get_service('util')."""

    def __init__(self):
        self._util = MiAZUtil(_UtilApp())

    def get_service(self, name):
        if name == 'util':
            return self._util
        raise KeyError(f"Unknown service: {name}")


def make_config(tmp_path, *, subdir='cfg', cache=None):
    """Return a MiAZConfig wired to files inside tmp_path.

    `cache` is the dict the config reads and writes its in-memory copies
    through. Passing the same one to two configs makes them share, which is what
    the repository store does for the configs that read one file.
    """
    cfg_dir = tmp_path / subdir
    cfg_dir.mkdir(exist_ok=True)
    available_file = str(cfg_dir / 'fake-available.json')
    used_file = str(cfg_dir / 'fake-used.json')
    app = MockApp()
    log = MiAZLog('test.config')
    cfg = MiAZConfig(
        app=app,
        log=log,
        config_for='FakeConfig',
        available=available_file,
        used=used_file,
        default=None,
        must_copy=False,
        cache=cache,
    )
    return cfg


# ---------------------------------------------------------------------------
# setup() creates both files via __init__
# ---------------------------------------------------------------------------

def test_setup_creates_available_file(tmp_path):
    cfg = make_config(tmp_path)
    assert os.path.exists(cfg.available)


def test_setup_creates_used_file(tmp_path):
    cfg = make_config(tmp_path)
    assert os.path.exists(cfg.used)


# ---------------------------------------------------------------------------
# load_used returns a dict
# ---------------------------------------------------------------------------

def test_load_used_returns_dict(tmp_path):
    cfg = make_config(tmp_path)
    result = cfg.load_used()
    assert isinstance(result, dict)


def test_load_available_returns_dict(tmp_path):
    cfg = make_config(tmp_path)
    result = cfg.load_available()
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# add_used / exists_used / remove_used round-trip
# ---------------------------------------------------------------------------

def test_add_used_then_exists(tmp_path):
    # Keys with hyphens are sanitised by valid_key (hyphens become underscores),
    # so use an already-sanitised key to avoid the mismatch.
    cfg = make_config(tmp_path)
    cfg.add_used('fakekeyalpha', 'fake value alpha')
    assert cfg.exists_used('fakekeyalpha') is True


def test_add_used_value_stored(tmp_path):
    cfg = make_config(tmp_path)
    cfg.add_used('fakekeybeta', 'stored-value')
    data = cfg.load_used()
    assert data.get('fakekeybeta') == 'stored-value'


def test_remove_used_then_not_exists(tmp_path):
    cfg = make_config(tmp_path)
    cfg.add_used('fakekeygamma', 'to be deleted')
    assert cfg.exists_used('fakekeygamma') is True
    cfg.remove_used('fakekeygamma')
    assert cfg.exists_used('fakekeygamma') is False


def test_remove_used_absent_key_returns_false(tmp_path):
    cfg = make_config(tmp_path)
    result = cfg.remove_used('nonexistent-key-xyz')
    assert result is False


def test_add_used_empty_key_returns_false(tmp_path):
    cfg = make_config(tmp_path)
    result = cfg.add_used('', 'some value')
    assert result is False


# ---------------------------------------------------------------------------
# add_available / exists_available round-trip
# ---------------------------------------------------------------------------

def test_add_available_then_exists(tmp_path):
    # Use a sanitised key (no hyphens) so valid_key does not transform it.
    cfg = make_config(tmp_path)
    cfg.add_available('availkeyalpha', 'available value')
    assert cfg.exists_available('availkeyalpha') is True


# ---------------------------------------------------------------------------
# get / set round-trip (operates on the used file)
# ---------------------------------------------------------------------------

def test_set_then_get(tmp_path):
    cfg = make_config(tmp_path)
    cfg.set('fake-setting', 'fake-value-xyz')
    assert cfg.get('fake-setting') == 'fake-value-xyz'


def test_get_missing_key_returns_none(tmp_path):
    cfg = make_config(tmp_path)
    assert cfg.get('does-not-exist-key') is None


# ---------------------------------------------------------------------------
# Multiple independent config instances share no state
# ---------------------------------------------------------------------------

def test_two_configs_independent(tmp_path):
    cfg_a = make_config(tmp_path, subdir='cfg_a')
    cfg_b = make_config(tmp_path, subdir='cfg_b')
    cfg_a.add_used('shared-name', 'value-a')
    assert cfg_b.exists_used('shared-name') is False


# ---------------------------------------------------------------------------
# set() must behave like every other writer
# ---------------------------------------------------------------------------

def test_set_writes_the_value_to_the_used_file(tmp_path):
    cfg = make_config(tmp_path)
    cfg.set('fakesetting', 'fake-value-xyz')
    util = cfg.app.get_service('util')
    assert util.json_load(cfg.used).get('fakesetting') == 'fake-value-xyz'


def test_set_does_not_create_a_bogus_cache_entry(tmp_path):
    """set() used to call save() with no filepath, so the cache bookkeeping
    keyed itself on the empty string and the real file was never marked dirty.
    It only worked because load() hands back the cached dict by reference and
    set() mutates that same object.
    """
    cfg = make_config(tmp_path)
    cfg.set('fakesetting', 'fake-value-xyz')
    assert '' not in cfg.cache


def test_set_marks_the_used_file_as_changed(tmp_path):
    cfg = make_config(tmp_path)
    cfg.load_used()
    cfg.set('fakesetting', 'fake-value-xyz')
    assert cfg.cache[cfg.used]['changed'] is True


def test_set_emits_used_updated(tmp_path):
    cfg = make_config(tmp_path)
    seen = []
    cfg.connect('used-updated', lambda *a: seen.append(True))
    cfg.set('fakesetting', 'fake-value-xyz')
    assert seen == [True]


def test_set_survives_a_writer_that_replaces_the_dict(tmp_path):
    """The reference-mutation accident is not something to rely on: a caller
    that saves a fresh dict must still invalidate the cache.
    """
    cfg = make_config(tmp_path)
    cfg.load_used()
    cfg.save(cfg.used, {'brandnew': 'value'})
    assert cfg.load_used() == {'brandnew': 'value'}


# ---------------------------------------------------------------------------
# The cache belongs to whoever owns the config, not to the class
# ---------------------------------------------------------------------------

def test_config_cache_is_not_shared_through_the_class(tmp_path):
    """A class attribute outlives every repository switch. Two configs given
    separate caches must not see each other's entries.
    """
    cfg_a = make_config(tmp_path, subdir='cache_a')
    cfg_b = make_config(tmp_path, subdir='cache_b')
    cfg_a.load_used()
    assert cfg_a.used not in cfg_b.cache


def test_configs_can_share_one_cache_on_purpose(tmp_path):
    """SentBy, SentTo and Person all read people-available.json, so they must
    share, which is why the cache was made a class attribute in the first place.
    Sharing is now something the owner asks for.
    """
    shared = {}
    cfg_a = make_config(tmp_path, subdir='shared_cfg', cache=shared)
    cfg_b = make_config(tmp_path, subdir='shared_cfg', cache=shared)
    cfg_a.add_used('sharedkey', 'value-a')
    assert cfg_b.exists_used('sharedkey') is True


# ---------------------------------------------------------------------------
# The update signals say which keys changed
# ---------------------------------------------------------------------------

def test_changed_keys_reports_additions_removals_and_edits():
    old = {'A': 'one', 'B': 'two', 'C': 'three'}
    new = {'A': 'one', 'B': 'CHANGED', 'D': 'four'}
    assert changed_keys(old, new) == {'B', 'C', 'D'}


def test_changed_keys_of_identical_dicts_is_empty():
    items = {'A': 'one', 'B': 'two'}
    assert changed_keys(items, dict(items)) == set()


def test_used_updated_carries_only_the_edited_key(tmp_path):
    """The point of the payload: renaming one country must not tell every
    listener to throw away everything it derived from the other countries.
    """
    cfg = make_config(tmp_path)
    cfg.save_used({'ES': 'Spain', 'FR': 'France'})
    seen = []
    cfg.connect('used-updated', lambda _c, changed: seen.append(changed))
    cfg.save_used({'ES': 'Kingdom of Spain', 'FR': 'France'})
    assert seen == [{'ES'}]


def test_used_updated_reports_an_added_key(tmp_path):
    cfg = make_config(tmp_path)
    cfg.save_used({'ES': 'Spain'})
    seen = []
    cfg.connect('used-updated', lambda _c, changed: seen.append(changed))
    cfg.add_used('FR', 'France')
    assert seen == [{'FR'}]


def test_used_updated_reports_a_removed_key(tmp_path):
    cfg = make_config(tmp_path)
    cfg.save_used({'ES': 'Spain', 'FR': 'France'})
    seen = []
    cfg.connect('used-updated', lambda _c, changed: seen.append(changed))
    cfg.remove_used('FR')
    assert seen == [{'FR'}]


def test_a_first_save_reports_every_key_as_changed(tmp_path):
    """There is no previous file, so nothing about the new one can be assumed
    to be already known.
    """
    cfg = make_config(tmp_path)
    seen = []
    cfg.connect('used-updated', lambda _c, changed: seen.append(changed))
    cfg.save_used({'ES': 'Spain', 'FR': 'France'})
    assert seen == [{'ES', 'FR'}]


def test_the_diff_is_taken_against_disk_not_the_cache(tmp_path):
    """load() hands out the cached dict itself and set() mutates it in place, so
    a diff against the cache would always come back empty.
    """
    cfg = make_config(tmp_path)
    cfg.save_used({'ES': 'Spain'})
    cfg.load_used()
    seen = []
    cfg.connect('used-updated', lambda _c, changed: seen.append(changed))
    cfg.set('ES', 'Kingdom of Spain')
    assert seen == [{'ES'}]


def test_an_unreadable_previous_file_reports_unknown(tmp_path):
    """None means "assume everything changed". Silently reporting an empty set
    would leave stale entries in every listener's cache.
    """
    cfg = make_config(tmp_path)
    cfg.save_used({'ES': 'Spain'})
    with open(cfg.used, 'w', encoding='utf-8') as fout:
        fout.write('{ not json')
    seen = []
    cfg.connect('used-updated', lambda _c, changed: seen.append(changed))
    cfg.save_used({'ES': 'Spain', 'FR': 'France'})
    assert seen == [None]


def test_available_updated_carries_its_own_diff(tmp_path):
    cfg = make_config(tmp_path)
    cfg.save_available({'ES': 'Spain'})
    seen = []
    cfg.connect('available-updated', lambda _c, changed: seen.append(changed))
    cfg.save_available({'ES': 'Spain', 'FR': 'France'})
    assert seen == [{'FR'}]


# MiAZConfigRepositories: the per-repository entries, and the remote flag.
#
# Two things rebuild an entry from scratch and drop any key they do not know:
# _normalize_items on every load, and set_repo on every rename. A per
# repository setting has to survive both.

import json

from MiAZ.frontend.console.app import MiAZConsoleApp


def _repos_file(miaz_env):
    return os.path.join(miaz_env['LPATH']['ETC'], 'repos-used.json')


def _repos_config(miaz_env):
    return MiAZConsoleApp(miaz_env).get_config('Repository')


def test_normalize_keeps_the_remote_flag(miaz_env):
    """A flag written to disk survives the next load."""
    with open(_repos_file(miaz_env), 'w', encoding='utf-8') as handler:
        json.dump({'Work': {'path': '/tmp/work', 'description': 'Work',
                            'remote': True}}, handler)

    assert _repos_config(miaz_env).get_remote('Work') is True


def test_normalize_defaults_remote_to_false(miaz_env):
    """An entry written before the flag existed reads as local."""
    with open(_repos_file(miaz_env), 'w', encoding='utf-8') as handler:
        json.dump({'Work': {'path': '/tmp/work', 'description': 'Work'}}, handler)

    assert _repos_config(miaz_env).get_remote('Work') is False


def test_a_legacy_string_entry_reads_as_local(miaz_env):
    """The oldest shape is {key: path}, with no dict to carry a flag."""
    with open(_repos_file(miaz_env), 'w', encoding='utf-8') as handler:
        json.dump({'Work': '/tmp/work'}, handler)
    config = _repos_config(miaz_env)

    assert config.get_remote('Work') is False
    assert config.get_path('Work') == '/tmp/work'


def test_an_old_entry_is_migrated_once(miaz_env):
    """The first load writes the missing key, the second writes nothing.

    Counted rather than timed: two writes inside one filesystem timestamp tick
    would make an mtime comparison pass for the wrong reason.
    """
    with open(_repos_file(miaz_env), 'w', encoding='utf-8') as handler:
        json.dump({'Work': {'path': '/tmp/work', 'description': 'Work'}}, handler)
    config = _repos_config(miaz_env)
    config.load(config.used)

    util = config.app.get_service('util')
    real_save = util.json_save
    writes = []
    util.json_save = lambda path, items: (writes.append(path), real_save(path, items))[1]
    config._invalidate(config.used)
    config.load(config.used)

    assert writes == [], 'a migrated file was rewritten on every load'


def test_renaming_a_repository_keeps_the_remote_flag(miaz_env):
    """set_repo rebuilds the entry, and dropped everything it did not know."""
    config = _repos_config(miaz_env)
    config.set_repo('Work', '/tmp/work', 'Work')
    config.set_remote('Work', True)

    config.set_repo('Work', '/tmp/work', 'Renamed')

    assert config.get_description('Work') == 'Renamed'
    assert config.get_remote('Work') is True


def test_set_remote_persists_to_disk(miaz_env):
    config = _repos_config(miaz_env)
    config.set_repo('Work', '/tmp/work', 'Work')

    config.set_remote('Work', True)

    with open(_repos_file(miaz_env), encoding='utf-8') as handler:
        assert json.load(handler)['Work']['remote'] is True


def test_the_flag_is_per_repository(miaz_env):
    config = _repos_config(miaz_env)
    config.set_repo('Work', '/tmp/work', 'Work')
    config.set_repo('Home', '/tmp/home', 'Home')

    config.set_remote('Work', True)

    assert config.get_remote('Work') is True
    assert config.get_remote('Home') is False


def test_disabling_and_re_enabling_keeps_the_remote_flag(miaz_env):
    """The entry is rebuilt on both moves, so the flag has to be carried.

    MiAZRepositories moves a repository between the available and used pools
    by rebuilding the entry from the selected row, which carries only the id,
    path and description. Without help the flag is lost, and a hard disabled
    repository would quietly come back enabled.
    """
    config = _repos_config(miaz_env)
    config.set_repo_used('Work', '/tmp/work', 'Work')
    config.set_remote('Work', True, used=True)

    # Disable: used entry moves to available.
    remembered = config.get_remote('Work', used=True)
    config.set_repo_available('Work', '/tmp/work', 'Work')
    config.set_remote('Work', remembered, used=False)

    assert config.get_remote('Work', used=False) is True

    # Enable again: available entry moves back to used.
    remembered = config.get_remote('Work', used=False)
    config.set_repo_used('Work', '/tmp/work', 'Work')
    config.set_remote('Work', remembered, used=True)

    assert config.get_remote('Work', used=True) is True


# ---------------------------------------------------------------------------
# _add_batch writes only when the batch changes something
# ---------------------------------------------------------------------------

def test_adding_a_batch_that_changes_nothing_writes_nothing(tmp_path):
    """The plugin list is handed to add_available_batch on every startup.

    saved counted the keys written into the dictionary, not the keys that
    differed, so with 20 plugins it was 20 every time and the file was rewritten
    at every launch. The write cost a read of the previous contents for the diff
    and invalidated the cache, so one logical read of plugins-available.json
    became three accesses and a write. On a remote repository that is three
    round trips instead of one.
    """
    cfg = make_config(tmp_path)
    batch = [('one', 'One'), ('two', 'Two')]
    cfg.add_available_batch(batch)

    written = []
    original = cfg.save

    def counting_save(*args, **kwargs):
        written.append(True)
        return original(*args, **kwargs)

    cfg.save = counting_save
    try:
        cfg.add_available_batch(batch)
    finally:
        cfg.save = original
    assert written == [], 'the same batch was written again'


def test_adding_a_batch_that_changes_something_still_writes(tmp_path):
    """The guard must not stop a real change from reaching the disk."""
    cfg = make_config(tmp_path)
    cfg.add_available_batch([('one', 'One')])

    written = []
    original = cfg.save

    def counting_save(*args, **kwargs):
        written.append(True)
        return original(*args, **kwargs)

    cfg.save = counting_save
    try:
        cfg.add_available_batch([('one', 'One'), ('two', 'Two')])
    finally:
        cfg.save = original
    assert written == [True], 'a new key was not written'
    assert 'two' in cfg.load_available()


def test_a_batch_that_changes_a_description_is_written(tmp_path):
    """Same keys, different values: still a change."""
    cfg = make_config(tmp_path)
    cfg.add_available_batch([('one', 'One')])

    written = []
    original = cfg.save
    cfg.save = lambda *a, **k: (written.append(True), original(*a, **k))[1]
    try:
        cfg.add_available_batch([('one', 'Uno')])
    finally:
        cfg.save = original
    assert written == [True], 'a changed description was not written'
    assert cfg.load_available()['one'] == 'Uno'
