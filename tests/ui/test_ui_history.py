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


def test_a_window_settled_while_recording_is_not_stranded(miaz, history):
    """A recording started by an earlier window can still be in flight when
    the next one settles. That window must be rearmed, not dropped: nothing
    is recorded and its counts wait, rather than sitting with no timer to
    flush them."""
    repository = miaz.service('repo').docs
    before = history.store.count()
    with open(os.path.join(repository, '20261214-ES-FIN-BANKX-INV-z-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history._recording = True
    history.settle()
    assert history._settle_id != 0, 'the window is rearmed rather than dropped'
    assert history._counts == {'added': 1}, 'the count is kept, waiting its turn'
    assert history.store.count() == before, 'nothing is recorded while busy'

    history._recording = False
    history.settle()
    miaz.pump(0.5)
    assert history.store.count() == before + 1


def test_a_failed_recording_keeps_its_counts_for_the_next_step(miaz, history):
    """settle() clears self._counts before the background call is known to
    have succeeded. A recording that fails must not lose that count: it comes
    back and is carried by the step that does succeed."""
    repository = miaz.service('repo').docs
    with open(os.path.join(repository, '20261215-ES-FIN-BANKX-INV-w-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')

    original_record = history.store.record

    def failing_record(subject):
        raise RuntimeError('pretend the disk is full')

    history.store.record = failing_record
    try:
        history._counts = {'added': 1}
        history.settle()
        miaz.pump(0.5)
    finally:
        history.store.record = original_record

    assert history._counts == {'added': 1}, 'the failed count is merged back, not lost'

    with open(os.path.join(repository, '20261216-ES-FIN-BANKX-INV-v-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')
    history._counts['added'] += 1
    history.settle()
    miaz.pump(0.5)
    newest = history.store.states()[-1]
    assert history.store.subject_of(newest) == 'Added 2 documents'


def test_both_buttons_are_in_the_header_bar(miaz, history):
    assert miaz.widget('headerbar-button-history-undo') is not None
    assert miaz.widget('headerbar-button-history-redo') is not None


def test_a_repository_with_one_state_can_step_nowhere(miaz, history):
    """Nothing has happened yet, so neither direction leads anywhere.

    The sandbox repository is session scoped and shared with every other UI
    test file, so walking it back to its oldest state here would strip it of
    documents those files rely on. The steps back are counted and then undone
    with the same number of steps forward, in a finally, so the repository
    ends where it started even if an assertion below fails.
    """
    steps_back = 0
    try:
        while history.store.can_undo():
            history.store.step_back('Stepped back')
            steps_back += 1
        history.refresh_buttons()
        miaz.pump(0.2)
        assert miaz.widget('headerbar-button-history-undo').get_sensitive() is False
    finally:
        for _ in range(steps_back):
            history.store.step_forward('Stepped forward')
        history.refresh_buttons()
        miaz.pump(0.2)


def test_a_recorded_change_makes_the_undo_button_work(miaz, history):
    repository = miaz.service('repo').docs
    with open(os.path.join(repository, '20261214-ES-FIN-BANKX-INV-z-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history.settle()
    miaz.pump(0.5)
    assert miaz.widget('headerbar-button-history-undo').get_sensitive() is True


def test_the_dialog_names_the_files_and_never_says_git(miaz, history):
    repository = miaz.service('repo').docs
    name = '20261215-ES-FIN-BANKX-INV-w-JOHNDOE.pdf'
    with open(os.path.join(repository, name), 'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history.settle()
    miaz.pump(0.5)

    dialog = history.ask_undo()
    miaz.pump(0.2)
    body = dialog.get_body()
    assert name in body
    for word in ('commit', 'git', 'revert', 'checkout'):
        assert word not in body.lower()
    dialog.close()
    miaz.pump(0.2)


def test_stepping_back_takes_the_document_off_the_disk(miaz, history):
    repository = miaz.service('repo').docs
    name = '20261216-ES-FIN-BANKX-INV-v-JOHNDOE.pdf'
    path = os.path.join(repository, name)
    with open(path, 'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history.settle()
    miaz.pump(0.5)

    history.apply_step('back')
    miaz.wait_until(lambda: not os.path.exists(path), message='the document went away')
    assert history.store.can_redo() is True


def test_a_step_already_in_flight_blocks_a_second_one(miaz, history):
    """_suppressed marks a step already running in the background. A second
    apply_step call made while it is set must not start another one against
    the same working tree."""
    before_index = history.store.index()
    before_count = history.store.count()
    history._suppressed = True
    try:
        history.apply_step('back')
        miaz.pump(0.2)
        assert history.store.index() == before_index
        assert history.store.count() == before_count
    finally:
        history._suppressed = False


def test_the_settings_say_what_the_history_costs(history):
    """Nothing is pruned, so the size is the one thing worth showing."""
    group = history.build_settings()
    assert group is not None
    rows = []
    child = group.get_first_child()
    while child is not None:
        rows.append(child)
        child = child.get_next_sibling()
    assert rows, 'the settings group has no rows'


# --- The two paths that exist to refuse a repository gracefully -------------
#
# Both were reached by every user without git, and every user who already
# versions their documents themselves. show_error presents the dialog itself
# and returns nothing, so assigning its result and calling present() on that
# raised AttributeError before disable_self() could run: the plugin failed to
# load, MiAZ put up a plugin-load-failure banner, and because the plugin was
# never removed from plugins-used.json it happened again on every launch.

def _muted_dialogs(history, monkeypatch):
    """Record what would be shown, and return None the way show_error does."""
    shown = []

    def show_error(title='', body='', **kwargs):
        shown.append((title, body))
        return None

    monkeypatch.setattr(history.srvdlg, 'show_error', show_error)
    return shown


def test_a_repository_without_git_is_refused_and_switches_the_plugin_off(
        history, monkeypatch):
    shown = _muted_dialogs(history, monkeypatch)
    switched_off = []
    monkeypatch.setattr(history, 'disable_self',
                        lambda: switched_off.append(True))

    history._offer_to_install('sudo dnf install git')

    assert len(shown) == 1, 'the user was told nothing'
    assert switched_off == [True], 'the plugin stayed half on'


def test_a_repository_without_git_and_an_unknown_distribution_still_refuses(
        history, monkeypatch):
    shown = _muted_dialogs(history, monkeypatch)
    switched_off = []
    monkeypatch.setattr(history, 'disable_self',
                        lambda: switched_off.append(True))

    history._offer_to_install(None)

    assert len(shown) == 1
    assert switched_off == [True]


def test_a_repository_somebody_else_tracks_is_refused_and_switches_off(
        history, monkeypatch):
    shown = _muted_dialogs(history, monkeypatch)
    switched_off = []
    monkeypatch.setattr(history, 'disable_self',
                        lambda: switched_off.append(True))

    history._refuse_foreign()

    assert len(shown) == 1
    assert switched_off == [True]


# --- A step must not start while a recording is in flight ------------------

def test_a_recording_in_flight_blocks_a_step(miaz, history):
    """settle() commits on a worker thread. A step started while that runs
    puts two git processes on one working tree: they fight over
    .git/index.lock, and if read-tree lands between 'add -A' and 'commit' the
    recording commits the stepped-back tree as a state the user never made."""
    before_index = history.store.index()
    before_count = history.store.count()
    history._recording = True
    try:
        history.apply_step('back')
        miaz.pump(0.3)
        assert history.store.index() == before_index
        assert history.store.count() == before_count
    finally:
        history._recording = False


def test_the_buttons_go_dead_while_a_change_is_being_recorded(miaz, history):
    """So the click cannot be made in the first place, rather than being
    swallowed by the guard above with nothing to show for it."""
    repository = miaz.service('repo').docs
    with open(os.path.join(repository, '20261217-ES-FIN-BANKX-INV-u-JOHNDOE.pdf'),
              'wb') as document:
        document.write(b'new')
    history._counts = {'added': 1}
    history.settle()
    assert miaz.widget('headerbar-button-history-undo').get_sensitive() is False
    miaz.pump(0.5)
    assert miaz.widget('headerbar-button-history-undo').get_sensitive() is True


# --- A filename is not markup ----------------------------------------------

def test_the_dialog_escapes_a_name_that_looks_like_markup(miaz, history):
    """show_confirmation renders the body as Pango markup. An unescaped & or <
    in a filename makes it unparseable, and the user then confirms a step that
    rewrites their documents against an empty or broken body."""
    repository = miaz.service('repo').docs
    name = 'Smith & Sons <invoice>.pdf'
    path = os.path.join(repository, name)
    with open(path, 'wb') as document:
        document.write(b'dropped in by the file manager')
    history._counts = {}
    history.settle()
    miaz.pump(0.5)

    dialog = history.ask_undo()
    miaz.pump(0.2)
    try:
        body = dialog.get_body()
        assert 'Smith &amp; Sons &lt;invoice&gt;.pdf' in body
        assert 'Smith & Sons' not in body
    finally:
        dialog.close()
        miaz.pump(0.2)
        # Best effort: MiAZ renames a file that does not match its naming
        # format, so the path this test wrote may not be the one on disk any
        # more. The sandbox repository is thrown away after the run either way.
        try:
            os.unlink(path)
        except OSError:
            pass
        history._counts = {}
        history.settle()
        miaz.pump(0.5)


# --- The button keys go when the plugin does -------------------------------

def test_the_button_keys_are_registered_for_removal(miaz, history):
    """add_widget on its own leaves the key pointing at a detached button after
    a deactivate or a repository switch, and the next activation finds the
    stale key and re-attaches nothing."""
    system = miaz.service('plugin-system')
    assert miaz.widget('headerbar-button-history-undo') is history.button_undo
    assert miaz.widget('headerbar-button-history-redo') is history.button_redo
    # The box, plus one for each button.
    assert system.widgets.count('MiAZHistory') >= 3


# --- The wiring, end to end ------------------------------------------------

def test_deleting_documents_is_recorded_as_one_step_named_for_all_of_them(
        miaz, history):
    """Every other test here sets _counts by hand and calls settle() directly,
    so the signal handlers and the settle timer are never exercised. This one
    deletes through MiAZ and lets the timer fire on its own.

    filename-deleted carries every path removed in one signal, so the count has
    to come from the collection rather than from the number of signals.
    """
    repository = miaz.service('repo').docs
    util = miaz.service('util')
    names = ['20261218-ES-FIN-BANKX-INV-p-JOHNDOE.pdf',
             '20261218-ES-FIN-BANKX-INV-q-JOHNDOE.pdf']
    paths = [os.path.join(repository, name) for name in names]
    for path in paths:
        with open(path, 'wb') as document:
            document.write(b'to be deleted')
    history._counts = {}
    history.settle()
    miaz.pump(0.6)
    before = history.store.count()

    util.filename_delete(set(paths))
    miaz.wait_until(lambda: history.store.count() > before,
                    message='the deletion was recorded')

    newest = history.store.states()[-1]
    assert history.store.subject_of(newest) == 'Deleted 2 documents'
