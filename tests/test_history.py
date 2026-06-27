#!/usr/bin/python3

"""
Tests for MiAZ.backend.history. Runs without a display (GObject/Gio only).

A real MiAZUtil emits the filename-* signals; MiAZHistory listens and writes
the journal. The repository is a stub whose docs dir points at a temp path.
"""

import os
import json
import datetime

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

import pytest

from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.history import MiAZHistory, HISTORY_DIRNAME


class StubRepo:
    def __init__(self, docs):
        self.docs = docs


class MockApp:
    def __init__(self, repo):
        self._repo = repo
        self._util = None

    def get_config(self, name):
        return None

    def get_service(self, name):
        if name == 'util':
            return self._util
        if name == 'repo':
            return self._repo
        return None


@pytest.fixture
def env(tmp_path):
    repo = StubRepo(str(tmp_path))
    app = MockApp(repo)
    util = MiAZUtil(app)
    app._util = util
    history = MiAZHistory(app)
    return util, history, tmp_path


def _read_month(tmp_path):
    month = datetime.datetime.now().strftime('%Y%m')
    fpath = os.path.join(str(tmp_path), HISTORY_DIRNAME, f'{month}.jsonl')
    with open(fpath, encoding='utf-8') as handler:
        return [json.loads(line) for line in handler if line.strip()]


def test_added_record_is_relative(env):
    util, history, tmp_path = env
    target = os.path.join(str(tmp_path), 'doc.pdf')
    util.emit('filename-added', target)

    records = _read_month(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec['event'] == 'added'
    assert rec['origin'] == 'app'
    assert rec['path'] == 'doc.pdf'
    assert 'path_absolute' not in rec
    assert rec['ts']


def test_renamed_record_has_source_and_target(env):
    util, history, tmp_path = env
    source = os.path.join(str(tmp_path), 'old.pdf')
    target = os.path.join(str(tmp_path), 'new.pdf')
    util.emit('filename-renamed', source, target)

    rec = _read_month(tmp_path)[0]
    assert rec['event'] == 'renamed'
    assert rec['source'] == 'old.pdf'
    assert rec['target'] == 'new.pdf'


def test_deleted_set_yields_one_record_per_path(env):
    util, history, tmp_path = env
    paths = {
        os.path.join(str(tmp_path), 'a.pdf'),
        os.path.join(str(tmp_path), 'b.pdf'),
    }
    util.emit('filename-deleted', paths)

    records = _read_month(tmp_path)
    assert len(records) == 2
    assert all(r['event'] == 'deleted' for r in records)
    assert {r['path'] for r in records} == {'a.pdf', 'b.pdf'}


def test_path_outside_repo_stays_absolute(env):
    util, history, tmp_path = env
    outside = '/tmp/elsewhere/doc.pdf'
    util.emit('filename-added', outside)

    rec = _read_month(tmp_path)[0]
    assert rec['path'] == os.path.abspath(outside)
    assert rec['path_absolute'] is True


def test_import_file_provenance(env):
    util, history, tmp_path = env
    # Importing copies the file under a normalized name. The journal should
    # keep the provenance (where it came from) so the rename is traceable.
    origin = {'type': 'file', 'path': '/home/user/Downloads/Original Name-resumen.odt'}
    target = os.path.join(str(tmp_path), '-----original_name_resumen-.odt')
    util.emit('filename-imported', origin, target)
    util.emit('filename-added', target)

    rec = _read_month(tmp_path)[0]
    assert rec['event'] == 'added'
    assert rec['path'] == '-----original_name_resumen-.odt'
    assert rec['source'] == origin


def test_import_zip_provenance(env):
    util, history, tmp_path = env
    origin = {'type': 'zip',
              'archive': '/home/user/courses/book/ai-book-standalone.zip',
              'entry': 'book/ai-book.html'}
    target = os.path.join(str(tmp_path), '-----book-.html')
    util.emit('filename-imported', origin, target)
    util.emit('filename-added', target)

    rec = _read_month(tmp_path)[0]
    assert rec['event'] == 'added'
    assert rec['path'] == '-----book-.html'
    assert rec['source'] == origin


def test_import_scan_provenance(env):
    util, history, tmp_path = env
    target = os.path.join(str(tmp_path), '-----scan-.pdf')
    util.emit('filename-imported', {'type': 'scan'}, target)
    util.emit('filename-added', target)

    rec = _read_month(tmp_path)[0]
    assert rec['event'] == 'added'
    assert rec['source'] == {'type': 'scan'}


def test_plain_add_has_no_source(env):
    util, history, tmp_path = env
    target = os.path.join(str(tmp_path), 'doc.pdf')
    util.emit('filename-added', target)

    rec = _read_month(tmp_path)[0]
    assert rec['event'] == 'added'
    assert 'source' not in rec


def test_iter_records_reads_back_in_order(env):
    util, history, tmp_path = env
    util.emit('filename-added', os.path.join(str(tmp_path), 'one.pdf'))
    util.emit('filename-added', os.path.join(str(tmp_path), 'two.pdf'))

    records = list(history.iter_records())
    assert [r['path'] for r in records] == ['one.pdf', 'two.pdf']


def test_no_journal_without_repository(tmp_path):
    repo = StubRepo(None)
    app = MockApp(repo)
    util = MiAZUtil(app)
    app._util = util
    history = MiAZHistory(app)

    util.emit('filename-added', os.path.join(str(tmp_path), 'doc.pdf'))
    assert not os.path.isdir(os.path.join(str(tmp_path), HISTORY_DIRNAME))
