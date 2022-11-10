#!/usr/bin/env python

from gi.repository import GObject


class MiAZModel(GObject.Object):
    """Custom data model for MiAZ use cases"""
    __gtype_name__ = 'MiAZModel'

    def __init__(self, id: str, title: str = '', subtitle:str = '', active: bool = False, icon: str = ''):
        super().__init__()

        self._id = id
        self._title = title
        self._subtitle = subtitle
        self._active = active
        self._icon = icon

    @GObject.Property
    def id(self):
        return self._id

    @GObject.Property
    def title(self):
        return self._title

    @GObject.Property
    def subtitle(self):
        return self._subtitle

    @GObject.Property(type=bool, default=False)
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        self._active = active

    @GObject.Property
    def icon(self):
        return self._icon


class File(MiAZModel):
    __gtype_name__ = 'File'

class Collection(MiAZModel):
    __gtype_name__ = 'Date'

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

class Repository(MiAZModel):
    __gtype_name__ = 'Repository'