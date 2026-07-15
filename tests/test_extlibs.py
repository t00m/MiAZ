#!/usr/bin/python3

"""
Tests for MiAZ.frontend.desktop.services.extlibs.MiAZExtLibs, focused on the
library-to-plugin mapping. The plugin system and app are stubbed so no GTK
display or real plugins are needed; only the pure inversion logic is exercised.
"""

from MiAZ.backend.venv import MiAZVenv
from MiAZ.frontend.desktop.services.extlibs import MiAZExtLibs


class StubPlugin:
    def __init__(self, module_dir, name, loaded=True):
        self._dir, self._name, self._loaded = module_dir, name, loaded

    def is_loaded(self):
        return self._loaded

    def get_module_dir(self):
        return self._dir

    def get_name(self):
        return self._name

    def get_module_name(self):
        return self._name


class StubPluginSystem:
    def __init__(self, plugins):
        self.plugins = plugins


class StubApp:
    def __init__(self, venv_path, plugins):
        self._env = {'LPATH': {'VENV': venv_path}}
        self._services = {'venv': MiAZVenv(self),
                          'plugin-system': StubPluginSystem(plugins)}

    def get_env(self):
        return self._env

    def get_service(self, name):
        return self._services.get(name)


def _plugin(tmp_path, name, reqs, loaded=True):
    pdir = tmp_path / name
    pdir.mkdir()
    if reqs is not None:
        (pdir / 'requirements.txt').write_text('\n'.join(reqs) + '\n')
    return StubPlugin(str(pdir), name, loaded=loaded)


def test_plugins_by_library(tmp_path):
    plugins = [
        _plugin(tmp_path, 'AI Assistant', ['anthropic', 'openai>=1.0']),
        _plugin(tmp_path, 'AI Chat', ['anthropic']),
        _plugin(tmp_path, 'Notes', None),          # no requirements
        _plugin(tmp_path, 'Disabled', ['ollama'], loaded=False),
    ]
    ext = MiAZExtLibs(StubApp(str(tmp_path / 'venv'), plugins))
    mapping = ext.plugins_by_library()

    # A shared library lists both requiring plugins, sorted.
    assert mapping['anthropic'] == ['AI Assistant', 'AI Chat']
    # Version specifiers are stripped to the distribution name.
    assert mapping['openai'] == ['AI Assistant']
    # A disabled plugin does not contribute its requirements.
    assert 'ollama' not in mapping
