#!/usr/bin/env python

from gi.repository import GObject

class MiAZModel(GObject.Object):
    """Custom MiAZ data model to be subclassed"""
    __gtype_name__ = 'MiAZModel'

    def __init__(self, id: str, title: str):
        super().__init__()
        self._id = id
        self._title = title

    @GObject.Property
    def id(self):
        return self._id

    @GObject.Property
    def title(self):
        return self._title

class MiAZItem(MiAZModel):
    """Custom data model for MiAZ use cases
    {timestamp}-{country}-{group}-{subgroup}-{from}-{purpose}-{concept}-{to}.{extension}
    """
    __gtype_name__ = 'MiAZItem'

    def __init__(self,  id: str,
                        date: str = '',
                        date_dsc: str = '',
                        group: str = '',
                        subgroup: str = '',
                        country: str = '',
                        purpose: str = '',
                        sentby_id: str = '',
                        sentby_dsc: str = '',
                        title: str = '',
                        subtitle:str = '',
                        sentto_id: str = '',
                        sentto_dsc: str = '',
                        active: bool = False,
                        valid: bool = False,
                        icon: str = ''):
        super().__init__(id)

        # ~ self._id = id
        self._date = date
        self._date_dsc = date_dsc
        self._group = group
        self._subgroup = subgroup
        self._country = country
        self._purpose = purpose
        self._sentby_id = sentby_id
        self._sentby_dsc = sentby_dsc
        self._title = title
        self._subtitle = subtitle
        self._sentto_id = sentto_id
        self._sentto_dsc = sentto_dsc
        self._active = active
        self._valid = valid
        self._icon = icon

    # ~ @GObject.Property
    # ~ def id(self):
        # ~ return self._id

    @GObject.Property
    def date(self):
        return self._date

    @GObject.Property
    def date_dsc(self):
        return self._date_dsc

    @GObject.Property
    def group(self):
        return self._group

    @GObject.Property
    def subgroup(self):
        return self._subgroup

    @GObject.Property
    def country(self):
        return self._country

    @GObject.Property
    def purpose(self):
        return self._purpose

    @GObject.Property
    def sentby_id(self):
        return self._sentby_id

    @GObject.Property
    def sentto_id(self):
        return self._sentto_id

    @GObject.Property
    def sentby_dsc(self):
        return self._sentby_dsc

    @GObject.Property
    def sentto_dsc(self):
        return self._sentto_dsc

    # ~ @GObject.Property
    # ~ def title(self):
        # ~ return self._title

    @GObject.Property
    def subtitle(self):
        return self._subtitle

    @GObject.Property(type=bool, default=False)
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        self._active = active

    @GObject.Property(type=bool, default=False)
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, valid):
        self._valid = valid

    @GObject.Property
    def icon(self):
        return self._icon

class File(MiAZModel):
    __gtype_name__ = 'File'

class Date(MiAZModel):
    __gtype_name__ = 'Date'

class Group(MiAZModel):
    __gtype_name__ = 'Group'

class Subgroup(MiAZModel):
    __gtype_name__ = 'Subgroup'

class Concept(MiAZModel):
    __gtype_name__ = 'Concept'

class Country(MiAZModel):
    __gtype_name__ = 'Country'

    def __init__(self,  id: str, title: str = '', icon: str = ''):
        super().__init__(id, title)
        self._icon = icon

    @GObject.Property
    def icon(self):
        return self._icon

class Person(MiAZModel):
    __gtype_name__ = 'Person'

class SentBy(Person):
    __gtype_name__ = 'SentBy'

class SentTo(Person):
    __gtype_name__ = 'SentTo'

class Purpose(MiAZModel):
    __gtype_name__ = 'Purpose'

class Repository(MiAZModel):
    __gtype_name__ = 'Repository'
