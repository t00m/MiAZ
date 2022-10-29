#!/usr/bin/env python

from gi.repository import GObject

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
