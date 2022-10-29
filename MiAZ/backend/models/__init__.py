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


class Collection(GObject.Object):
    __gtype_name__ = 'Collection'

    def __init__(self, name):
        super().__init__()

        self._name = name

    @GObject.Property
    def name(self):
        return self._name


class Concept(GObject.Object):
    __gtype_name__ = 'Concept'

    def __init__(self, name):
        super().__init__()

        self._name = name

    @GObject.Property
    def name(self):
        return self._name


class Country(GObject.Object):
    __gtype_name__ = 'Country'

    def __init__(self, country_id, country_name):
        super().__init__()

        self._country_id = country_id
        self._country_name = country_name

    @GObject.Property
    def country_id(self):
        return self._country_id

    @GObject.Property
    def country_name(self):
        return self._country_name


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


class Purpose(GObject.Object):
    __gtype_name__ = 'Purpose'

    def __init__(self, name):
        super().__init__()

        self._name = name

    @GObject.Property
    def name(self):
        return self._name
