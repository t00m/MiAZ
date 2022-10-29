#!/usr/bin/env python

from gi.repository import GObject


class MiAZModel(GObject.Object):
    __gtype_name__ = 'MiAZModel'

    def __init__(self, id, name=None, detail=None):
        super().__init__()

        self._id = id
        self._name = name
        self._detail = detail

    @GObject.Property
    def id(self):
        return self._id

    @GObject.Property
    def name(self):
        return self._name

    @GObject.Property
    def detail(self):
        return self._detail


class File(MiAZModel):
    __gtype_name__ = 'File'


class Collection(MiAZModel):
    __gtype_name__ = 'Collection'


class Concept(GObject.Object):
    __gtype_name__ = 'Concept'


class Country(MiAZModel):
    __gtype_name__ = 'Country'


class Person(MiAZModel):
    __gtype_name__ = 'Person'


class Purpose(MiAZModel):
    __gtype_name__ = 'Purpose'

