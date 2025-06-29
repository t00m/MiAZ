#!/usr/bin/python3

"""
# File: watcher.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: It notifies the app when files are added/renamed/deleted
"""

# A modified version found on StackOverflow:
# https://stackoverflow.com/questions/182197/how-do-i-watch-a-file-for-changes

import os
import glob

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
    before = {}
    active = False
    status = MiAZStatus.RUNNING
    updated = False

    def __init__(self, dirpath: str = None, remote=False):
        """
        Initialize MiAZWatcher and signal"
        """
        super().__init__()
        self.log = MiAZLog('MiAZ.Watcher')
        self.dirpath = dirpath
        self.remote = remote
        seconds = 2
        self.log.debug(f"Watching repository: {dirpath}")
        self.log.debug(f"Remote repository? {remote}")
        self.log.debug(f"Timeout set to: {seconds}")
        sid = GObject.signal_lookup('repository-updated', MiAZWatcher)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repository-updated', MiAZWatcher, GObject.SignalFlags.RUN_LAST, None, ())
            self.set_path(dirpath)
            GLib.timeout_add_seconds(seconds, self.monitor, dirpath, self.watch)
            self.log.debug(f"Watcher initialized")

    def files_with_timestamp_async(self, path, callback):
        """
        Asynchronously fetches {file_path: mtime} from a directory.
        'callback' is a function receiving the dictionary once ready.
        """
        if self.status == MiAZStatus.BUSY:
            self.log.warning("Watcher is busy now. Trying later")
            return
        else:
            # ~ self.log.info("Watcher is active")
            pass

        # ~ self.log.debug(f"Checking files for directory: {path}")
        gfile = Gio.File.new_for_path(path)

        def on_query_info(fileobj, res, user_data):
            try:
                info = fileobj.query_info_finish(res)
                if info.get_file_type() != Gio.FileType.DIRECTORY:
                    self.log.warning(f"Not a directory: {path}")
                    callback({})
                    return

                # Proceed with enumeration
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
                callback({})

        def on_enumerate_ready(fileobj, res, user_data):
            timestamps = {}
            try:
                enumerator = fileobj.enumerate_children_finish(res)

                def on_next_file(enum, res2, user_data2):
                    try:
                        infos = enum.next_files_finish(res2)
                        if not infos:
                            callback(timestamps)
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
                        callback(timestamps)

                enumerator.next_files_async(10, GLib.PRIORITY_DEFAULT, None, on_next_file, None)
            except Exception as error:
                self.log.error("Error during enumeration: {error}")
                callback({})  # Return empty dict on failure

        # Set app as busy to block
        self.status = MiAZStatus.BUSY

        # Query info first to ensure it's a directory
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

        # ~ after = self.__files_with_timestamp(self.dirpath)

        added = [f for f in after.keys() if f not in self.before.keys()]
        removed = [f for f in self.before.keys() if f not in after.keys()]
        modified = []

        for f in self.before.keys():
            if f not in removed:
                try:
                    if os.path.getmtime(f) != self.before.get(f):
                        modified.append(f)
                except FileNotFoundError:
                    pass

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
