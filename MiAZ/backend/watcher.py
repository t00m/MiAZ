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

from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class MiAZWatcher(GObject.GObject):
    """
    Observe a given directory for file changes (added/renamed/deleted)
    and emit the signal 'repository-updated' when it happens.
    """
    __gtype_name__ = 'MiAZWatcher'
    before = {}
    active = False

    def __init__(self, dirpath: str = None):
        """
        Initialize MiAZWatcher and signal"
        """
        super().__init__()
        self.log = MiAZLog('MiAZ.Watcher')
        self.dirpath = dirpath
        sid = GObject.signal_lookup('repository-updated', MiAZWatcher)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repository-updated', MiAZWatcher, GObject.SignalFlags.RUN_LAST, None, ())
            self.set_path(dirpath)
            GLib.timeout_add_seconds(1, self.watch)
        self.log.debug("Watcher initialized")

    def __files_with_timestamp(self, rootdir):
        """
        This function generates a dictionary where the keys are the
        absolute paths of files in a specified directory (rootdir), and
        the values are the last modification timestamps of those files.
        """
        # FIXME: FileNotFoundError

        filelist = []
        files = glob.glob(os.path.join(rootdir, '*'))
        for thisfile in files:
            if os.path.exists(thisfile) and not os.path.isdir(thisfile):
                    filelist.append(os.path.abspath(os.path.relpath(thisfile)))
        return dict([(f, os.path.getmtime(f)) for f in filelist])

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

    def watch(self):
        """
        Monitor changes in a directory. It checks for added, removed,
        and modified files and logs these changes. If any changes are
        detected, it emits an event indicating that the repository has
        been updated.
        """
        updated = False
        if not self.active:
            return False

        if self.dirpath is None:
            return False

        after = self.__files_with_timestamp(self.dirpath)

        added = [f for f in after.keys() if f not in self.before.keys()]
        removed = [f for f in self.before.keys() if f not in after.keys()]
        modified = []

        for f in self.before.keys():
            if f not in removed:
                if os.path.getmtime(f) != self.before.get(f):
                    modified.append(f)

        if added:
            self.log.debug(f"Watcher > {len(added)} files added")
            updated |= True
        if removed:
            self.log.debug(f"Watcher > {len(removed)} files removed")
            updated |= True
        if modified:
            self.log.debug(f"Watcher > {len(modified)} files modified")
            updated |= True

        if updated:
            self.emit('repository-updated')

        self.before = after
        return True
