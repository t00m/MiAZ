#!/usr/bin/python3

"""UI: the MiAZHistory plugin, through the real application.

The sandbox repository gets its history prepared before the plugin loads, so
activation finds a history that is already ours and no dialog opens.
"""

import os
import sys
import shutil

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')

import pytest

PLUGIN_DIR = os.path.join('data', 'resources', 'plugins', 'MiAZHistory')

pytestmark = pytest.mark.skipif(shutil.which('git') is None,
                                reason='git is not installed')


@pytest.fixture
def history(miaz):
    """The MiAZHistory plugin, loaded against a prepared sandbox repository."""
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)
    from history.gitstore import GitStore

    repository = miaz.service('repo').docs
    store = GitStore(repository)
    if not store.exists():
        store.init('Everything as it was')

    system = miaz.service('plugin-system')
    info = system.get_plugin_info('miazhistory')
    assert info is not None, 'the MiAZHistory plugin is not in the index'
    was_loaded = system.is_plugin_loaded(info)
    if not was_loaded:
        assert system.load_plugin(info), 'the MiAZHistory plugin did not load'
    miaz.pump(0.5)
    instance = system.get_extension('miazhistory')
    assert instance is not None, 'the MiAZHistory plugin has no extension instance'
    yield instance
    if not was_loaded:
        system.unload_plugin(info)
        miaz.pump(0.3)


def test_the_plugin_finds_a_history_that_is_already_prepared(history):
    assert history.is_ready() is True


def test_a_new_document_is_recorded_as_one_step(miaz, history):
    """The settle timer is fired by hand: the test is what a settled window
    records, not how long the timer waits."""
    repository = miaz.service('repo').docs
    before = history.store.count()
    with open(os.path.join(repository, '20261212-ES-FIN-BANKX-INV-x-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history.settle()
    miaz.pump(0.5)
    assert history.store.count() == before + 1


def test_a_step_is_named_after_what_the_user_did(miaz, history):
    repository = miaz.service('repo').docs
    with open(os.path.join(repository, '20261213-ES-FIN-BANKX-INV-y-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history.settle()
    miaz.pump(0.5)
    newest = history.store.states()[-1]
    assert history.store.subject_of(newest) == 'Added 1 document'
