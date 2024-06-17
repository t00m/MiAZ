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
    __gtype_name__ = 'MiAZWatcher'
    before = {}
    active = False

    def __init__(self, dirpath: str):
        super().__init__()
        self.log = MiAZLog('MiAZ.Watcher')
        self.dirpath = dirpath
        sid = GObject.signal_lookup('repository-updated', MiAZWatcher)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repository-updated', MiAZWatcher, GObject.SignalFlags.RUN_LAST, None, () )
            self.set_path(dirpath)
            GLib.timeout_add_seconds(1, self.watch)

    # PLAIN
    def __files_with_timestamp(self, rootdir):
        # FIXME: FileNotFoundError
        """Add data files from a given directory."""
        filelist = []
        files = glob.glob(os.path.join(rootdir, '*'))
        for thisfile in files:
            if not os.path.isdir(thisfile):
                if os.path.exists(thisfile):
                    filelist.append(os.path.abspath(os.path.relpath(thisfile)))
        return dict([(f, os.path.getmtime(f)) for f in filelist])

    # RECURSIVE
    # ~ def __files_with_timestamp(self, rootdir):
        # ~ """Add data files from a given directory."""
        # ~ filelist = []
        # ~ resdirs = set()
        # ~ for root, dirs, files in os.walk(rootdir):
            # ~ resdirs.add(os.path.realpath(root))
        # ~ for directory in resdirs:
            # ~ files = glob.glob(os.path.join(directory, '*'))
            # ~ for thisfile in files:
                # ~ if not os.path.isdir(thisfile):
                    # ~ if os.path.exists(thisfile):
                        # ~ filelist.append(os.path.abspath(os.path.relpath(thisfile)))
        # ~ return dict([(f, os.path.getmtime(f)) for f in filelist])

    def set_path(self, dirpath: str):
        self.dirpath = dirpath
        self.log.debug("Watcher monitoring '%s'", self.dirpath)

    def set_active(self, active: bool = True) -> None:
        self.active = active

    def get_active(self):
        return self.active

    def watch(self):
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
            self.log.debug("Watcher > %d files added", len(added))
            updated |= True
        if removed:
            self.log.debug("Watcher > %d files removed", len(removed))
            updated |= True
        if modified:
            self.log.debug("Watcher > %d files modified", len(modified))
            updated |= True

        if updated:
            self.emit('repository-updated')

        self.before = after
        return True
