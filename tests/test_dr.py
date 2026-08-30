#!/usr/bin/python3

"""
Tests for the disaster-recovery backend (MiAZ.backend.dr.MiAZDR): backup and
restore of repository files and config, plus the rollback paths.

MiAZDR only needs an app that provides a 'util' service with zip/unzip/timestamp.
FakeUtil implements those with the stdlib (shutil), mirroring MiAZUtil.zip, which
returns the archive path, and MiAZUtil.unzip, which extracts into a directory.
That keeps the tests on dr.py's own orchestration and rollback logic, and lets
them run headless like the rest of the suite.
"""

import os
import shutil
from unittest import mock

import pytest

from MiAZ.backend.dr import MiAZDR


class FakeUtil:
    def timestamp(self):
        return "20260101_000000"

    def zip(self, filename, directory):
        # Mirrors MiAZUtil.zip: archive `directory` into `filename`.zip and
        # return the resulting path.
        return shutil.make_archive(filename, 'zip', directory)

    def unzip(self, target, install_dir):
        shutil.unpack_archive(target, install_dir)


class FakeApp:
    def __init__(self, util):
        self._util = util

    def get_service(self, name):
        assert name == 'util'
        return self._util


@pytest.fixture
def dr():
    return MiAZDR(FakeApp(FakeUtil()))


def _write(path, text):
    with open(path, 'w', encoding='utf-8') as handler:
        handler.write(text)


def _read(path):
    with open(path, encoding='utf-8') as handler:
        return handler.read()


def test_backup_files_copies_only_visible(dr, tmp_path):
    repo = tmp_path / 'repo'
    dest = tmp_path / 'dest'
    repo.mkdir()
    dest.mkdir()
    _write(repo / 'a.txt', 'A')
    _write(repo / 'b.txt', 'B')
    _write(repo / '.hidden', 'H')
    (repo / '.conf').mkdir()

    count = dr.backup_files(str(repo), str(dest))

    assert count == 2
    assert (dest / 'a.txt').exists()
    assert (dest / 'b.txt').exists()
    assert not (dest / '.hidden').exists()


def test_restore_files_roundtrip(dr, tmp_path):
    src = tmp_path / 'backup'
    repo = tmp_path / 'repo'
    src.mkdir()
    repo.mkdir()
    _write(src / 'doc.txt', 'content')

    count = dr.restore_files(str(repo), str(src))

    assert count == 1
    assert _read(repo / 'doc.txt') == 'content'


def test_backup_config_creates_zip(dr, tmp_path):
    conf = tmp_path / '.conf'
    dest = tmp_path / 'dest'
    conf.mkdir()
    dest.mkdir()
    _write(conf / 'repo.json', '{}')

    result = dr.backup_config(str(conf), str(dest), repo_key='myrepo')

    assert result.endswith('.zip')
    assert os.path.exists(result)
    assert 'myrepo' in os.path.basename(result)


def test_restore_config_roundtrip(dr, tmp_path):
    conf = tmp_path / '.conf'
    dest = tmp_path / 'dest'
    conf.mkdir()
    dest.mkdir()
    _write(conf / 'repo.json', '{"FORMAT": 1}')

    zip_path = dr.backup_config(str(conf), str(dest))

    # Corrupt the live config, then restore it from the backup.
    _write(conf / 'repo.json', 'BROKEN')
    dr.restore_config(str(conf), zip_path)

    assert _read(conf / 'repo.json') == '{"FORMAT": 1}'
    assert not os.path.exists(str(conf) + '.old')


def test_restore_config_rolls_back_on_failure(dr, tmp_path):
    conf = tmp_path / '.conf'
    dest = tmp_path / 'dest'
    conf.mkdir()
    dest.mkdir()
    _write(conf / 'repo.json', 'PRE_RESTORE')

    zip_path = dr.backup_config(str(conf), str(dest))

    # Fail while repopulating the fresh .conf. Rollback must restore the
    # pre-restore state and remove the .old sidecar.
    with mock.patch('MiAZ.backend.dr.shutil.copy2', side_effect=OSError('boom')):
        with pytest.raises(OSError, match='boom'):
            dr.restore_config(str(conf), zip_path)

    assert _read(conf / 'repo.json') == 'PRE_RESTORE'
    assert not os.path.exists(str(conf) + '.old')


def test_restore_config_unzip_failure_leaves_original(dr, tmp_path):
    # If unzip fails before anything is moved, the rollback references old_conf,
    # which is why it is defined before the try. The original config survives
    # and the real error (not a NameError) propagates.
    conf = tmp_path / '.conf'
    conf.mkdir()
    _write(conf / 'repo.json', 'ORIGINAL')

    dr.util = FakeUtil()
    with mock.patch.object(dr.util, 'unzip', side_effect=RuntimeError('bad zip')):
        with pytest.raises(RuntimeError, match='bad zip'):
            dr.restore_config(str(conf), '/nonexistent.zip')

    assert _read(conf / 'repo.json') == 'ORIGINAL'


def test_restore_repository_roundtrip(dr, tmp_path):
    repo = tmp_path / 'repo'
    dest = tmp_path / 'dest'
    repo.mkdir()
    dest.mkdir()
    _write(repo / 'doc.txt', 'v1')
    (repo / '.conf').mkdir()
    _write(repo / '.conf' / 'repo.json', '{}')

    zip_path = dr.backup_repository(str(repo), str(dest))

    _write(repo / 'doc.txt', 'v2')
    dr.restore_repository(str(repo), zip_path)

    assert _read(repo / 'doc.txt') == 'v1'
    assert (repo / '.conf' / 'repo.json').exists()
    assert not os.path.exists(str(repo) + '.old')


def test_restore_repository_rolls_back_on_failure(dr, tmp_path):
    repo = tmp_path / 'repo'
    dest = tmp_path / 'dest'
    repo.mkdir()
    dest.mkdir()
    _write(repo / 'doc.txt', 'PRE_RESTORE')

    zip_path = dr.backup_repository(str(repo), str(dest))

    with mock.patch('MiAZ.backend.dr.shutil.copy2', side_effect=OSError('boom')):
        with pytest.raises(OSError, match='boom'):
            dr.restore_repository(str(repo), zip_path)

    assert _read(repo / 'doc.txt') == 'PRE_RESTORE'
    assert not os.path.exists(str(repo) + '.old')


# ---------------------------------------------------------------------------
# Progress reporting
#
# Backup and restore now run in a worker thread behind a modal dialog
# (frontend/desktop/services/progress.py), and the dialog is only as honest as
# what these methods report. The callback is optional everywhere: the tests
# above call them without one.
# ---------------------------------------------------------------------------

class Recorder:
    """Collects (message, fraction) the way the progress dialog receives them."""

    def __init__(self):
        self.updates = []

    def __call__(self, message, fraction=None):
        self.updates.append((message, fraction))

    @property
    def fractions(self):
        return [fraction for _message, fraction in self.updates
                if fraction is not None]


def test_backup_files_reports_one_update_per_file(dr, tmp_path):
    repo = tmp_path / 'repo'
    dest = tmp_path / 'dest'
    repo.mkdir()
    dest.mkdir()
    for name in ('a.txt', 'b.txt', 'c.txt'):
        _write(repo / name, name)
    _write(repo / '.hidden', 'H')
    report = Recorder()

    dr.backup_files(str(repo), str(dest), progress=report)

    assert len(report.updates) == 3
    assert report.fractions == [pytest.approx(1 / 3), pytest.approx(2 / 3), 1.0]
    assert 'a.txt' in report.updates[0][0]


def test_restore_files_reports_one_update_per_file(dr, tmp_path):
    src = tmp_path / 'backup'
    repo = tmp_path / 'repo'
    src.mkdir()
    repo.mkdir()
    _write(src / 'doc.txt', 'content')
    report = Recorder()

    dr.restore_files(str(repo), str(src), progress=report)

    assert report.fractions == [1.0]
    assert 'doc.txt' in report.updates[0][0]


def test_an_empty_backup_reports_nothing_and_does_not_divide_by_zero(dr, tmp_path):
    repo = tmp_path / 'repo'
    dest = tmp_path / 'dest'
    repo.mkdir()
    dest.mkdir()
    report = Recorder()

    assert dr.backup_files(str(repo), str(dest), progress=report) == 0
    assert report.updates == []


def test_zipping_reports_without_a_fraction(dr, tmp_path):
    """shutil and zipfile say nothing while they work, so the bar pulses rather
    than claiming a percentage it cannot know."""
    conf = tmp_path / '.conf'
    dest = tmp_path / 'dest'
    conf.mkdir()
    dest.mkdir()
    _write(conf / 'repo.json', '{}')
    report = Recorder()

    dr.backup_config(str(conf), str(dest), progress=report)

    assert report.updates
    assert report.fractions == []


def test_restore_repository_reports_its_stages(dr, tmp_path):
    repo = tmp_path / 'repo'
    dest = tmp_path / 'dest'
    repo.mkdir()
    dest.mkdir()
    _write(repo / 'doc.txt', 'content')
    archive = dr.backup_repository(str(repo), str(dest))
    report = Recorder()

    dr.restore_repository(str(repo), archive, progress=report)

    # Extract, replace, clean up: three stages, none of them measurable.
    assert len(report.updates) == 3
    assert report.fractions == []
