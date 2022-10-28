#!/usr/bin/env python

from gi.repository import GObject

class Concept(GObject.Object):
    __gtype_name__ = 'Concept'

    def __init__(self, name):
        super().__init__()

        self._name = name

    @GObject.Property
    def name(self):
        return self._name
