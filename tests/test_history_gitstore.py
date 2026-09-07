#!/usr/bin/python3

"""The git repository behind MiAZHistory.

Every test runs against a real git repository in a temporary directory. Faking
git would test the fake: what matters here is what git actually does with
read-tree, renames and an empty working tree.
"""

import os
import sys
import json
import shutil
import subprocess

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZHistory')

pytestmark = pytest.mark.skipif(shutil.which('git') is None,
                                reason='git is not installed')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


@pytest.fixture
def repository(tmp_path):
    """A repository shaped like a MiAZ one: documents in the root, config in
    .conf."""
    conf = tmp_path / '.conf'
    conf.mkdir()
    (conf / 'repo.json').write_text('{"dir_docs": "."}', encoding='utf-8')
    (conf / 'plugins-used.json').write_text(
        json.dumps({'MiAZHistory': 'Undo and redo changes in this repository'}),
        encoding='utf-8')
    (tmp_path / '20260101-ES-FIN-BANKX-INV-rent-JOHNDOE.pdf').write_bytes(b'first')
    return tmp_path


def test_a_directory_with_no_git_has_no_history(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    assert store.exists() is False
    assert store.is_ours() is False
    assert store.is_foreign() is False


def test_the_first_snapshot_records_one_state(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    first = store.init('Everything as it was')
    assert store.exists() is True
    assert store.is_ours() is True
    assert store.states() == [first]
    assert store.index() == 0
    assert store.count() == 1


def test_the_first_snapshot_holds_the_documents_and_the_configuration(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    listed = subprocess.run(['git', '-C', str(repository), 'ls-files'],
                            capture_output=True, text=True, check=True).stdout
    assert '20260101-ES-FIN-BANKX-INV-rent-JOHNDOE.pdf' in listed
    assert '.conf/repo.json' in listed
    assert '.conf/plugins-used.json' in listed


def test_the_identity_belongs_to_miaz_and_not_to_the_user(repository):
    """A user with no git identity configured must still be able to use this,
    and a user who has one must not find it on these commits."""
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    author = subprocess.run(
        ['git', '-C', str(repository), 'show', '-s', '--format=%an <%ae>'],
        capture_output=True, text=True, check=True).stdout.strip()
    assert author == 'MiAZ <miaz@localhost>'


def test_the_state_file_is_inside_git_and_not_inside_conf(repository):
    """Anywhere under .conf it would be a tracked file that changes on every
    step, and every step would trigger the next one."""
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    assert os.path.exists(repository / '.git' / 'miaz-history.json')
    assert not os.path.exists(repository / '.conf' / 'miaz-history.json')
    assert store.is_dirty() is False


def test_a_git_repository_made_by_somebody_else_is_foreign(repository):
    from history.gitstore import GitStore
    subprocess.run(['git', '-C', str(repository), 'init', '-q'], check=True)
    store = GitStore(str(repository))
    assert store.exists() is True
    assert store.is_ours() is False
    assert store.is_foreign() is True


def test_the_history_reports_the_disk_it_uses(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    assert store.size() > 0


def test_a_failing_command_raises(repository):
    from history.gitstore import GitStore, GitError
    store = GitStore(str(repository))
    with pytest.raises(GitError):
        store.subject_of('no-such-state')


def test_a_change_becomes_a_state(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    first = store.init('Everything as it was')
    (repository / '20260202-ES-FIN-BANKX-INV-water-JOHNDOE.pdf').write_bytes(b'second')
    second = store.record('Added 1 document')
    assert second is not None
    assert store.states() == [first, second]
    assert store.index() == 1


def test_everything_in_one_window_is_one_state(repository):
    """A mass rename is one action, so it is one step, however many files it
    touched."""
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    for number in range(5):
        (repository / f'2026030{number}-ES-FIN-BANKX-INV-fee-JOHNDOE.pdf').write_bytes(b'x')
    store.record('Added 5 documents')
    assert store.count() == 2


def test_a_change_to_the_configuration_is_a_state(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    (repository / '.conf' / 'senders-used.json').write_text('{"BANKX": "Bank X"}',
                                                           encoding='utf-8')
    assert store.record('Added 1 sender') is not None
    assert store.count() == 2


def test_installing_a_plugin_is_a_state(repository):
    """Enabling a plugin writes plugins-used.json, which is tracked like
    anything else under .conf."""
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    used = repository / '.conf' / 'plugins-used.json'
    used.write_text(json.dumps({'MiAZHistory': 'Undo and redo changes in this repository',
                                'MiAZDoctor': 'Health check'}), encoding='utf-8')
    assert store.record('Changed settings') is not None
    assert store.count() == 2


def test_a_plugin_setting_is_a_state(repository):
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    conf = repository / '.conf' / 'plugins' / 'MiAZDoctor' / 'conf'
    conf.mkdir(parents=True)
    (conf / 'Plugin-MiAZDoctor.json').write_text('{"autorun": true}', encoding='utf-8')
    assert store.record('Changed settings') is not None
    assert store.count() == 2


def test_nothing_changed_is_not_a_state(repository):
    """The settle timer fires on signals, and a signal that changed no file
    must not leave an empty step behind."""
    from history.gitstore import GitStore
    store = GitStore(str(repository))
    store.init('Everything as it was')
    assert store.record('Nothing at all') is None
    assert store.count() == 1
