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


def test_a_remote_watcher_schedules_exactly_one_poll(monkeypatch):
    """A remote repository has no Gio.FileMonitor, so it is polled instead.

    __init__ used to call set_path(), which schedules the poll, and then
    schedule a second one itself, overwriting _timeout_id with the new source.
    The first source kept running with its id lost, so nothing could ever stop
    it: the repository was polled at twice the intended rate and every watcher
    built leaked one source.
    """
    import MiAZ.backend.watcher as watcher_module

    scheduled = []
    real_add = watcher_module.GLib.timeout_add_seconds

    def spy_add(seconds, callback, *args):
        source_id = real_add(seconds, callback, *args)
        scheduled.append(source_id)
        return source_id

    removed = []
    real_remove = watcher_module.GLib.source_remove

    def spy_remove(source_id):
        removed.append(source_id)
        return real_remove(source_id)

    monkeypatch.setattr(watcher_module.GLib, 'timeout_add_seconds', spy_add)
    monkeypatch.setattr(watcher_module.GLib, 'source_remove', spy_remove)

    w = MiAZWatcher(dirpath='/tmp', remote=True)
    try:
        assert len(scheduled) == 1, f'{len(scheduled)} polls scheduled, expected 1'
        # Whatever is running has to be the source the watcher can still name.
        orphans = [s for s in scheduled if s not in removed and s != w._timeout_id]
        assert orphans == [], f'poll sources running with their id lost: {orphans}'
    finally:
        if w._timeout_id > 0:
            real_remove(w._timeout_id)


def test_setting_a_new_path_replaces_the_remote_poll(monkeypatch):
    """Pointing a remote watcher somewhere else must not leave the old poll
    running alongside the new one."""
    import MiAZ.backend.watcher as watcher_module

    scheduled = []
    real_add = watcher_module.GLib.timeout_add_seconds
    monkeypatch.setattr(
        watcher_module.GLib, 'timeout_add_seconds',
        lambda s, cb, *a: scheduled.append(real_add(s, cb, *a)) or scheduled[-1])

    w = MiAZWatcher(dirpath='/tmp', remote=True)
    try:
        w.set_path('/var/tmp')
        assert len(scheduled) == 2
        # The first source must be gone, only the second still armed.
        assert w._timeout_id == scheduled[-1]
        assert watcher_module.GLib.main_context_default().find_source_by_id(scheduled[0]) is None
    finally:
        if w._timeout_id > 0:
            watcher_module.GLib.source_remove(w._timeout_id)


def test_a_local_watcher_schedules_no_poll(monkeypatch):
    """A local repository uses a Gio.FileMonitor and must never poll."""
    import MiAZ.backend.watcher as watcher_module

    scheduled = []
    real_add = watcher_module.GLib.timeout_add_seconds
    monkeypatch.setattr(
        watcher_module.GLib, 'timeout_add_seconds',
        lambda s, cb, *a: scheduled.append(real_add(s, cb, *a)) or scheduled[-1])

    MiAZWatcher(dirpath='/tmp', remote=False)
    assert scheduled == []
