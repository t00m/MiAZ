#!/usr/bin/env python

from gi.repository import GObject

class File(GObject.Object):
    __gtype_name__ = 'File'

    def __init__(self, path):
        super().__init__()

        self._path = path

    @GObject.Property
    def path(self):
        return self._path

