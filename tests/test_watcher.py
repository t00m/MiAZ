#!/usr/bin/python3

"""
Tests for MiAZWatcher's burst-to-signal logic: a single-file change emits a
per-file 'repository-changed' plus the full-refresh 'repository-updated'; a
bulk change emits only 'repository-updated'; events coalesce per path.

The watcher is built with dirpath=None so no real Gio.FileMonitor is created;
the tests drive _pending and _flush_changes directly.
"""

import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gio

from MiAZ.backend.watcher import MiAZWatcher


def _watcher():
    w = MiAZWatcher(dirpath=None)
    w.set_active(True)
    emissions = []
    w.connect('repository-changed', lambda wt, p, o, e: emissions.append(('changed', p, o, e)))
    w.connect('repository-updated', lambda wt: emissions.append(('updated',)))
    return w, emissions


def test_single_change_emits_per_file_then_full():
    w, emissions = _watcher()
    w._pending = {'/repo/doc.pdf': ('', 'created')}
    w._flush_changes()
    assert emissions == [
        ('changed', '/repo/doc.pdf', '', 'created'),
        ('updated',),
    ]


def test_rename_carries_other_path():
    w, emissions = _watcher()
    w._pending = {'/repo/old.pdf': ('/repo/new.pdf', 'renamed')}
    w._flush_changes()
    assert ('changed', '/repo/old.pdf', '/repo/new.pdf', 'renamed') in emissions


def test_bulk_change_emits_only_full():
    w, emissions = _watcher()
    w._pending = {f'/repo/d{i}.pdf': ('', 'created') for i in range(MiAZWatcher._BULK_THRESHOLD + 1)}
    w._flush_changes()
    assert emissions == [('updated',)]


def test_multiple_but_under_threshold_emit_each():
    w, emissions = _watcher()
    w._pending = {'/repo/a.pdf': ('', 'created'), '/repo/b.pdf': ('', 'deleted')}
    w._flush_changes()
    changed = [e for e in emissions if e[0] == 'changed']
    assert len(changed) == 2
    assert emissions[-1] == ('updated',)


def test_inactive_watcher_emits_nothing():
    w, emissions = _watcher()
    w.set_active(False)
    w._pending = {'/repo/doc.pdf': ('', 'created')}
    w._flush_changes()
    assert emissions == []


def test_event_nick_mapping():
    w, _ = _watcher()
    assert w._event_nick(Gio.FileMonitorEvent.CREATED) == 'created'
    assert w._event_nick(Gio.FileMonitorEvent.DELETED) == 'deleted'
    assert w._event_nick(Gio.FileMonitorEvent.RENAMED) == 'renamed'
    assert w._event_nick(Gio.FileMonitorEvent.CHANGES_DONE_HINT) == 'changes-done-hint'


def test_pending_cleared_after_flush():
    w, _ = _watcher()
    w._pending = {'/repo/doc.pdf': ('', 'created')}
    w._flush_changes()
    assert w._pending == {}
