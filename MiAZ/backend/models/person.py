#!/usr/bin/env python

from gi.repository import GObject

class Person(GObject.Object):
    __gtype_name__ = 'Person'

    def __init__(self, name, fullname):
        super().__init__()

        self._name = name
        self._fullname = fullname

    @GObject.Property
    def name(self):
        return self._name

    @GObject.Property
    def fullname(self):
        return self._fullname
