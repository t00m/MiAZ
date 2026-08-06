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

from MiAZ.backend.config import MiAZConfig
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
