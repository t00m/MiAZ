#!/usr/bin/env python

# A modified version found on StackOverflow:
# https://stackoverflow.com/questions/182197/how-do-i-watch-a-file-for-changes

import os
import sys
import glob
import time

from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import get_logger

class MiAZWatcher(GObject.GObject):
    before = {}
    active = True

    def __init__(self, name: str, dirpath: str):
        GObject.GObject.__init__(self)
        self.dirpath = dirpath
        self.name = name.lower()
        GObject.signal_new('%s-directory-updated' % self.name, MiAZWatcher, GObject.SignalFlags.RUN_LAST, None, () )
        self.log = get_logger('MiAZWatcher')
        self.log.debug("Watcher[%s] installed. Monitoring '%s'", self.name, self.dirpath)
        GLib.timeout_add_seconds(2, self.watch)

    def __files_with_timestamp(self, rootdir):
        """Add data files from a given directory."""
        filelist = []
        resdirs = set()
        for root, dirs, files in os.walk(rootdir):
            resdirs.add(os.path.realpath(root))
        for directory in resdirs:
            files = glob.glob(os.path.join(directory, '*'))
            for thisfile in files:
                if not os.path.isdir(thisfile):
                    filelist.append(os.path.abspath(os.path.relpath(thisfile)))
        return dict([(f, os.path.getmtime(f)) for f in filelist])

    def set_path(self, dirpath: str):
        self.dirpath = dirpath

    def set_active(self, active: bool) -> None:
        self.active = active

    def get_active(self):
        return self.active

    def watch(self):
        # ~ self.log.debug("Watcher[%s] active? %s", self.name, self.active)
        updated = False
        if not self.active:
            self.log.debug("Watcher[%s] not active", self.name)
            return False

        if self.dirpath is None:
            self.log.debug("Watcher[%s] directory not set", self.name)
            return False

        after = self.__files_with_timestamp(self.dirpath)

        added = [f for f in after.keys() if not f in self.before.keys()]
        removed = [f for f in self.before.keys() if not f in after.keys()]
        modified = []

        for f in self.before.keys():
            if not f in removed:
                if os.path.getmtime(f) != self.before.get(f):
                    modified.append(f)

        if added:
            self.log.debug("Watcher[%s] > %d files added", self.name, len(added))
            updated |= True
        if removed:
            self.log.debug("Watcher[%s] > %d files removed", self.name, len(removed))
            updated |= True
        if modified:
            self.log.debug("Watcher[%s] > %d files modified", self.name, len(modified))
            updated |= True

        if updated:
            self.emit('%s-directory-updated' % self.name)
            # ~ self.log.debug("Signal 'directory-%s-updated'  emitted", self.name)

        self.before = after
        return True
