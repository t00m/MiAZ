
"""
# File: watcher.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: It notifies the app when files are added/renamed/deleted
"""

# A modified version found on StackOverflow:
# https://stackoverflow.com/questions/182197/how-do-i-watch-a-file-for-changes

import os

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.status import MiAZStatus


class MiAZWatcher(GObject.GObject):
    """
    Observe a given directory for file changes (added/renamed/deleted)
    and emit the signal 'repository-updated' when it happens.
    """
    __gtype_name__ = 'MiAZWatcher'
    __gsignals__ = {
        # Full-refresh notification (unchanged): "something changed, re-scan".
        'repository-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
        # Per-file notification for incremental updates: (path, other_path, event).
        # other_path is only set for renames; event is a FileMonitor nick such
        # as 'created', 'deleted', 'renamed', 'changes-done-hint'.
        'repository-changed': (GObject.SignalFlags.RUN_LAST, None, (str, str, str)),
    }

    # A change touching more files than this in one burst is applied as a full
    # re-scan rather than many per-file updates.
    _BULK_THRESHOLD = 25

    # Gio.FileMonitorEvent to a stable string nick.
    _EVENT_NICKS = None

    def __init__(self, dirpath: str = None, remote=False):
        """
        Initialize MiAZWatcher and signal"
        """
        super().__init__()
        self.log = MiAZLog('MiAZ.Watcher')
        self.dirpath = dirpath
        self.remote = remote
        self.before = {}
        self.active = False
        self.status = MiAZStatus.RUNNING
        self.updated = False
        self._monitor = None
        self._debounce_id = 0
        self._timeout_id = 0
        # Per-path events accumulated during a burst: {path: (other_path, nick)}.
        self._pending = {}
        seconds = 2
        self.log.debug(f"Watching repository: {dirpath}")
        self.log.debug(f"Remote repository? {remote}")
        self.log.debug(f"Timeout set to: {seconds}")
        self.set_path(dirpath)
        
        if self.remote:
            self._timeout_id = GLib.timeout_add_seconds(seconds, self.monitor, dirpath, self.watch)
        
        self.log.debug("Watcher initialized")

    def _setup_file_monitor(self):
        if self._monitor:
            self._monitor.cancel()
            self._monitor = None
        
        if self.dirpath and os.path.exists(self.dirpath):
            gfile = Gio.File.new_for_path(self.dirpath)
            try:
                self._monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
                self._monitor.connect('changed', self._on_monitor_changed)
                self.log.debug(f"FileMonitor started for {self.dirpath}")
            except Exception as e:
                self.log.error(f"Could not setup FileMonitor: {e}")

    def _event_nick(self, event_type):
        """Map a Gio.FileMonitorEvent to a stable string nick."""
        if MiAZWatcher._EVENT_NICKS is None:
            E = Gio.FileMonitorEvent
            MiAZWatcher._EVENT_NICKS = {
                E.CHANGED: 'changed',
                E.CHANGES_DONE_HINT: 'changes-done-hint',
                E.DELETED: 'deleted',
                E.CREATED: 'created',
                E.ATTRIBUTE_CHANGED: 'attribute-changed',
                E.RENAMED: 'renamed',
                E.MOVED_IN: 'moved-in',
                E.MOVED_OUT: 'moved-out',
            }
        return MiAZWatcher._EVENT_NICKS.get(event_type, 'changed')

    def _on_monitor_changed(self, monitor, file, other_file, event_type):
        if not self.active:
            return

        # Accumulate the latest event per path; a burst (temp writes, etc.)
        # collapses to one settled event per file. The 500 ms debounce lets the
        # operation finish before we act on it.
        path = file.get_path() if file is not None else None
        if path is None:
            return
        other = other_file.get_path() if other_file is not None else ''
        self._pending[path] = (other, self._event_nick(event_type))

        if self._debounce_id > 0:
            GLib.source_remove(self._debounce_id)
        self._debounce_id = GLib.timeout_add(500, self._flush_changes)

    def _flush_changes(self):
        self._debounce_id = 0
        if not self.active:
            self._pending = {}
            return False
        pending = self._pending
        self._pending = {}
        if not pending:
            return False

        # Too many files at once: a single full re-scan is cheaper and simpler
        # than many per-file updates.
        if len(pending) > MiAZWatcher._BULK_THRESHOLD:
            self.log.debug(f"Repository updated ({len(pending)} paths, full re-scan)")
            self.emit('repository-updated')
            return False

        # Emit one per-file signal for incremental consumers, then the
        # full-refresh signal for consumers that do not handle paths (they can
        # choose to skip it when the per-file updates already covered the change).
        for path, (other, nick) in pending.items():
            self.emit('repository-changed', path, other, nick)
        self.emit('repository-updated')
        return False

    def files_with_timestamp_async(self, path, callback):
        """
        Asynchronously fetches {file_path: mtime} from a directory.
        'callback' is a function receiving the dictionary once ready.
        """
        if self.status == MiAZStatus.BUSY:
            self.log.warning("Watcher is busy now. Trying later")
            return

        # Guarantee the callback always resets the BUSY status,
        # even if the async chain errors out (GIO cancellation, etc.)
        def _done(result):
            try:
                callback(result)
            finally:
                self.status = MiAZStatus.RUNNING

        gfile = Gio.File.new_for_path(path)

        def on_query_info(fileobj, res, user_data):
            try:
                info = fileobj.query_info_finish(res)
                if info.get_file_type() != Gio.FileType.DIRECTORY:
                    self.log.warning(f"Not a directory: {path}")
                    _done({})
                    return

                fileobj.enumerate_children_async(
                    'standard::name,standard::type,time::modified',
                    Gio.FileQueryInfoFlags.NONE,
                    GLib.PRIORITY_DEFAULT,
                    None,
                    on_enumerate_ready,
                    None
                )
            except Exception as error:
                self.log.error(f"Failed to query info: {error}")
                _done({})

        def on_enumerate_ready(fileobj, res, user_data):
            timestamps = {}
            try:
                enumerator = fileobj.enumerate_children_finish(res)

                def on_next_file(enum, res2, user_data2):
                    try:
                        infos = enum.next_files_finish(res2)
                        if not infos:
                            _done(timestamps)
                            return
                        for i in infos:
                            if i.get_file_type() == Gio.FileType.REGULAR:
                                name = i.get_name()
                                mtime = i.get_modification_time().tv_sec
                                child = fileobj.get_child(name)
                                timestamps[child.get_uri()] = mtime
                        enum.next_files_async(100, GLib.PRIORITY_DEFAULT, None, on_next_file, None)
                    except Exception as error:
                        self.log.error(f"Error during file read: {error}")
                        _done(timestamps)

                enumerator.next_files_async(100, GLib.PRIORITY_DEFAULT, None, on_next_file, None)
            except Exception as error:
                self.log.error(f"Error during enumeration: {error}")
                _done({})

        self.status = MiAZStatus.BUSY

        gfile.query_info_async(
            'standard::*',
            Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_HIGH_IDLE,
            None,
            on_query_info,
            None
        )

    def set_path(self, dirpath: str):
        """Set a directory to watch"""
        if dirpath is not None:
            self.dirpath = dirpath
            self.log.info(f"Watcher monitoring '{self.dirpath}'")
            if self.remote:
                if self._timeout_id > 0:
                    GLib.source_remove(self._timeout_id)
                    self._timeout_id = 0
                seconds = 2
                self._timeout_id = GLib.timeout_add_seconds(seconds, self.monitor, self.dirpath, self.watch)
            else:
                self._setup_file_monitor()

    def set_active(self, active: bool = True) -> None:
        """Set current watcher as active"""
        self.active = active

    def get_active(self):
        """Return if the watcher is active or not"""
        return self.active

    def watch(self, after):
        """
        Monitor changes in a directory. It checks for added, removed,
        and modified files and logs these changes. If any changes are
        detected, it emits an event indicating that the repository has
        been updated.
        """
        self.updated = False
        if not self.active:
            return False

        if self.dirpath is None:
            return False

        if not self.before:
            # First poll
            self.before = after
            self.status = MiAZStatus.RUNNING
            return True

        added = [f for f in after.keys() if f not in self.before.keys()]
        removed = [f for f in self.before.keys() if f not in after.keys()]
        modified = []

        for f in self.before.keys():
            if f not in removed:
                if after.get(f) != self.before.get(f):
                    modified.append(f)

        if added:
            self.log.debug(f"Watcher > {len(added)} files added")
            self.updated |= True
        if removed:
            self.log.debug(f"Watcher > {len(removed)} files removed")
            self.updated |= True
        if modified:
            self.log.debug(f"Watcher > {len(modified)} files modified")
            self.updated |= True

        if self.updated:
            self.log.debug("Repository updated")
            self.emit('repository-updated')

        self.before = after
        self.status = MiAZStatus.RUNNING
        return True

    def monitor(self, path, callback):
        # ~ self.log.debug(f"Watcher active? {self.active}")
        if self.active:
            self.files_with_timestamp_async(path, callback)
        return True
