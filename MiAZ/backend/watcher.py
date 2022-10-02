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
        GObject.signal_new('directory-updated', MiAZBackend, GObject.SignalFlags.RUN_LAST, None, () )
        self.dirpath = dirpath
        self.name = name
        self.log = get_logger('MiAZWatcher')
        self.log.debug("Watching %s[%s]", name, self.dirpath)
        GLib.idle_add(self.watch)

    def __files_with_timestamp(self, rootdir):
        """Add data files from a given directory."""
        filelist = []
        resdirs = set()
        for root, dirs, files in os.walk(rootdir):
            resdirs.add(os.path.realpath(root))
        filelist = []
        for directory in resdirs:
            files = glob.glob(os.path.join(directory, '*'))

            for thisfile in files:
                if not os.path.isdir(thisfile):
                    filelist.append(os.path.abspath(os.path.relpath(thisfile)))
        return dict([(f, os.path.getmtime(f)) for f in filelist])

    def set_path(dirpath: str):
        self.dirpath = dirpath

    def set_active(self, active: bool) -> None:
        self.active = active

    def get_active(self):
        return self.active

    def watch(self):
        updated = False
        if not self.active:
            self.log.debug("Watcher [%s] not active", self.name)
            return

        if self.dirpath is None:
            self.log.debug("Watcher [%s] directory not set", self.name)
            return

        after = self.__files_with_timestamp(self.dirpath)

        added = [f for f in after.keys() if not f in self.before.keys()]
        removed = [f for f in self.before.keys() if not f in after.keys()]
        modified = []

        for f in self.before.keys():
            if not f in removed:
                if os.path.getmtime(f) != before.get(f):
                    modified.append(f)

        if added:
            updated |= True
        if removed:
            updated |= True
        if modified:
            updated |= True

        if updated:
            self.emit('directory-updated')
            self.log.debug("Signal 'directory-updated' emitted")

        self.before = after
