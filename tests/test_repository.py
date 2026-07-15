#!/usr/bin/python3

"""
Tests for MiAZ.backend.repository — validate() and init() — using tmp_path.
Runs without a display (GObject only, no GTK/Adw).
"""

import json

import gi
gi.require_version('GLib', '2.0')

from MiAZ.backend.repository import MiAZRepository


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
