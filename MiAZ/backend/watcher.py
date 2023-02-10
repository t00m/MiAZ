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
    __gtype_name__ = 'MiAZWatcher'
    before = {}
    active = False

    def __init__(self, name: str, dirpath: str):
        super(MiAZWatcher, self).__init__()
        self.log = get_logger('MiAZWatcher')
        self.name = name.lower()
        self.dirpath = dirpath
        sid = GObject.signal_lookup('repository-updated', MiAZWatcher)
        self.log.debug("Watcher SID: %d", sid)
        if sid == 0:
            GObject.GObject.__init__(self)
            GObject.signal_new('repository-updated', MiAZWatcher, GObject.SignalFlags.RUN_LAST, None, () )
            self.set_path(dirpath)
            GLib.timeout_add_seconds(2, self.watch)

    # PLAIN
    def __files_with_timestamp(self, rootdir):
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
        self.log.debug("Watcher[%s] installed. Monitoring '%s'", self.name, self.dirpath)

    def set_active(self, active: bool = True) -> None:
        self.log.debug("%s = %s", self.name, self.dirpath)
        self.log.debug("Current watcher status? %s", self.active)
        self.active = active
        self.log.debug("New watcher status? %s", self.active)

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
            # ~ self.log.debug("Watcher[%s] > %d files added", self.name, len(added))
            updated |= True
        if removed:
            # ~ self.log.debug("Watcher[%s] > %d files removed", self.name, len(removed))
            updated |= True
        if modified:
            # ~ self.log.debug("Watcher[%s] > %d files modified", self.name, len(modified))
            updated |= True

        if updated:
            self.emit('repository-updated')
            # ~ self.log.debug("Signal 'repository-updated'  emitted", self.name)

        self.before = after
        return True
