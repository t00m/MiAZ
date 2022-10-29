#!/usr/bin/env python

from gi.repository import GObject

class Collection(GObject.Object):
    __gtype_name__ = 'Collection'

    def __init__(self, name):
        super().__init__()

        self._name = name

    @GObject.Property
    def name(self):
        return self._name

