#!/usr/bin/python3

"""
Tests for the workspace handler that turns a 'used-updated' payload into
targeted cache invalidation.

Importing the workspace module needs the gi versions set (it imports GTK/Adw/
WebKit), but the handler under test touches nothing but the index, so it runs
against a stub self rather than a real widget.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
gi.require_version('WebKit', '6.0')

from MiAZ.backend.index import MiAZDocumentIndex
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace


class _StubConfig:
    """Stands in for a MiAZConfig. Only its model name is read."""

    def __init__(self, gtype_name):
        self.model = type(gtype_name, (), {'__gtype_name__': gtype_name})


class _StubApp:
    def __init__(self, index):
        self._index = index

    def get_service(self, name):
        assert name == 'index'
        return self._index


class _StubWorkspace:
    """Enough of a workspace for the handler: it only reaches for the index."""

    def __init__(self, index):
        self.app = _StubApp(index)


def _handle(index, config, changed):
    MiAZWorkspace._on_config_used_updated(_StubWorkspace(index), config, changed)


def _index_with_cache():
    index = MiAZDocumentIndex(app=None)
    index.cache['Country'] = {'ES': 'Spain', 'FR': 'France'}
    index.cache['Group'] = {'HOU': 'Housing'}
    return index


def test_only_the_changed_key_is_dropped():
    """The whole point: editing one country must not cost every other document
    in the view a full description rebuild.
    """
    index = _index_with_cache()
    _handle(index, _StubConfig('Country'), {'ES'})
    assert index.cache['Country'] == {'FR': 'France'}


def test_other_configs_are_untouched():
    index = _index_with_cache()
    _handle(index, _StubConfig('Country'), {'ES'})
    assert index.cache['Group'] == {'HOU': 'Housing'}


def test_several_changed_keys_are_all_dropped():
    index = _index_with_cache()
    _handle(index, _StubConfig('Country'), {'ES', 'FR'})
    assert index.cache['Country'] == {}


def test_an_empty_change_set_drops_nothing():
    """Saving a file whose contents did not change is not a reason to throw
    away work.
    """
    index = _index_with_cache()
    _handle(index, _StubConfig('Country'), set())
    assert index.cache['Country'] == {'ES': 'Spain', 'FR': 'France'}


def test_a_key_that_was_never_cached_is_harmless():
    index = _index_with_cache()
    _handle(index, _StubConfig('Country'), {'DE'})
    assert index.cache['Country'] == {'ES': 'Spain', 'FR': 'France'}


def test_a_config_with_no_cache_of_its_own_is_ignored():
    """Concept, Person and Plugin all emit the signal but have no description
    cache, so there is nothing to drop and nothing to fail on.
    """
    index = _index_with_cache()
    _handle(index, _StubConfig('Person'), {'JOHNDOE'})
    assert index.cache['Country'] == {'ES': 'Spain', 'FR': 'France'}


def test_an_unknown_change_set_clears_everything():
    """None means the config could not read its previous contents. Keeping any
    entry would risk showing a stale description.
    """
    index = _index_with_cache()
    _handle(index, _StubConfig('Country'), None)
    assert index.cache['Country'] == {}
    assert index.cache['Group'] == {}


def test_a_config_without_a_model_clears_everything():
    """Nothing says which cache to target, so the safe answer is all of them."""
    index = _index_with_cache()

    class _NoModel:
        pass

    _handle(index, _NoModel(), {'ES'})
    assert index.cache['Country'] == {}
    assert index.cache['Group'] == {}
