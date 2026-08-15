#!/usr/bin/python3

"""The two guards that stop the projects file being wiped.

On 14 August the project assignments of a real repository were emptied: every
document ended up in the default bucket and the fifteen projects were left with
nothing. The service that owns projects.json holds the path to one repository
and was outliving repository switches, so it compared one repository's
assignments against another repository's directory, found every document
missing, and deleted the lot.

The lifecycle bug is fixed elsewhere (the service is disposed and removed when
the plugin is unloaded). These are the guards that make the damage impossible
even when something else goes wrong: no cause of a mismatch, present or future,
can empty the file.

The plugin module imports gi but needs no display, so it is tested here rather
than in the UI suite.
"""

import json
import os
import sys

import pytest

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Peas', '2')

from MiAZ.backend.util import MiAZUtil

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZProjectMgt')
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from projmgt import (  # noqa: E402
    MiAZProject, is_total_wipe, writes_to_the_active_repository)


# ---------------------------------------------------------------------------
# is_total_wipe: would this consistency check delete everything?
# ---------------------------------------------------------------------------

def test_removing_every_assignment_from_a_full_repository_is_a_wipe():
    """The exact shape of the incident: 1235 assignments, all 'missing',
    while the repository is full of documents."""
    assert is_total_wipe(to_delete=1235, assigned=1235, documents_in_repo=1235) is True


def test_removing_some_assignments_is_ordinary_housekeeping():
    """Documents really do leave a repository. That is what check() is for."""
    assert is_total_wipe(to_delete=3, assigned=1235, documents_in_repo=1232) is False


def test_removing_every_assignment_from_an_empty_repository_is_fine():
    """A repository whose documents were all deleted really has nothing left,
    so clearing the assignments is correct rather than suspicious."""
    assert is_total_wipe(to_delete=40, assigned=40, documents_in_repo=0) is False


def test_nothing_to_delete_is_never_a_wipe():
    assert is_total_wipe(to_delete=0, assigned=1235, documents_in_repo=1235) is False


def test_no_assignments_at_all_is_never_a_wipe():
    assert is_total_wipe(to_delete=0, assigned=0, documents_in_repo=10) is False


def test_the_last_assignment_of_a_full_repository_still_counts():
    """One project, one document, and it 'vanished' while the repository is
    full. Small numbers are the same mistake as large ones."""
    assert is_total_wipe(to_delete=1, assigned=1, documents_in_repo=800) is True


# ---------------------------------------------------------------------------
# writes_to_the_active_repository: is this still my repository?
# ---------------------------------------------------------------------------

def test_the_same_repository_may_be_written():
    assert writes_to_the_active_repository('/repo/a/.conf', '/repo/a/.conf') is True


def test_another_repository_may_not_be_written():
    """The cross-repository write, refused at the point of the write."""
    assert writes_to_the_active_repository('/repo/a/.conf', '/repo/b/.conf') is False


def test_a_trailing_slash_is_the_same_repository():
    assert writes_to_the_active_repository('/repo/a/.conf/', '/repo/a/.conf') is True


def test_an_unknown_active_repository_does_not_block_the_write():
    """During shutdown the repository can no longer resolve. Refusing then
    would lose a legitimate save; the mismatch is what matters."""
    assert writes_to_the_active_repository('/repo/a/.conf', None) is True
    assert writes_to_the_active_repository('/repo/a/.conf', '') is True


# ---------------------------------------------------------------------------
# The guards where they matter: inside the service that owns the file
# ---------------------------------------------------------------------------


class FakeRepository:
    """Points at a documents directory and a configuration directory."""

    def __init__(self, docs, conf):
        self.docs = docs
        self.conf = conf

    def get(self, key):
        return {'dir_docs': self.docs, 'dir_conf': self.conf}[key]


class FakeDialogs:
    def __init__(self):
        self.toasts = []

    def show_toast(self, message):
        self.toasts.append(message)


class FakeApp:
    def __init__(self, repository):
        self.repository = repository
        self.dialogs = FakeDialogs()
        self.util = MiAZUtil(self)

    def get_service(self, name):
        return {'repo': self.repository, 'util': self.util,
                'dialogs': self.dialogs}.get(name)

    def get_config(self, name):
        return None


@pytest.fixture
def repository(tmp_path):
    """A repository with three documents and all three assigned to a project."""
    docs = tmp_path / 'repo'
    conf = docs / '.conf'
    conf.mkdir(parents=True)
    names = ['20260101-ES-FIN-BANK-INV-one-JOHNDOE.pdf',
             '20260102-ES-FIN-BANK-INV-two-JOHNDOE.pdf',
             '20260103-ES-FIN-BANK-INV-three-JOHNDOE.pdf']
    for name in names:
        (docs / name).write_text('document')
    with open(conf / 'projects.json', 'w', encoding='utf-8') as handler:
        json.dump({'AOK': names}, handler)
    return docs, conf, names


def read_projects(conf):
    with open(conf / 'projects.json', encoding='utf-8') as handler:
        return json.load(handler)


def test_a_mismatched_repository_does_not_empty_the_projects(repository, tmp_path):
    """The incident, reproduced: the assignments belong to one repository and
    the documents directory is another one, which is full of other files."""
    docs, conf, names = repository
    other = tmp_path / 'other'
    other.mkdir()
    for index in range(5):
        (other / f'20260201-DE-HOU-ACME-INV-other{index}-JOHNDOE.pdf').write_text('x')

    # Built against the real repository, then pointed at the other one, which
    # is what a service outliving a repository switch ends up looking at.
    app = FakeApp(FakeRepository(str(docs), str(conf)))
    service = MiAZProject(app)
    service.app.repository.docs = str(other)
    service.check()

    assert read_projects(conf)['AOK'] == names, 'the assignments were deleted'


def test_a_genuinely_empty_repository_still_gets_cleaned(repository):
    """The case check() is for: the documents really are gone."""
    docs, conf, names = repository
    for name in names:
        os.unlink(docs / name)

    app = FakeApp(FakeRepository(str(docs), str(conf)))
    service = MiAZProject(app)
    service.check()

    assert read_projects(conf)['AOK'] == []


def test_one_missing_document_is_still_removed(repository):
    """Ordinary housekeeping must keep working."""
    docs, conf, names = repository
    os.unlink(docs / names[0])

    app = FakeApp(FakeRepository(str(docs), str(conf)))
    service = MiAZProject(app)
    service.check()

    assert read_projects(conf)['AOK'] == names[1:]


def test_saving_into_a_repository_that_is_no_longer_open_is_refused(repository, tmp_path):
    """The cross-repository write: refused at the write itself."""
    docs, conf, names = repository
    app = FakeApp(FakeRepository(str(docs), str(conf)))
    service = MiAZProject(app)

    other_conf = tmp_path / 'other' / '.conf'
    other_conf.mkdir(parents=True)
    app.repository.conf = str(other_conf)

    service.projects = {'AOK': []}
    service.save()

    assert read_projects(conf)['AOK'] == names, 'it wrote to the wrong repository'
