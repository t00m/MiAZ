#!/usr/bin/python3

"""
# File: watcher.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom models for working with Columnviews
"""

from gettext import gettext as _

from gi.repository import GObject


class MiAZModel(GObject.Object):
    """Custom MiAZ data model to be subclassed"""
    __gtype_name__ = 'MiAZModel'
    __title__ = 'MiAZModel'

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
    {timestamp}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}
    """
    __gtype_name__ = 'MiAZItem'
    __title__ = 'MiAZItem'

    def __init__(self, id: str,
                        date: str = '',
                        date_dsc: str = '',
                        group: str = '',
                        group_dsc: str = '',
                        country: str = '',
                        country_dsc: str = '',
                        purpose: str = '',
                        purpose_dsc: str = '',
                        sentby_id: str = '',
                        sentby_dsc: str = '',
                        title: str = '',
                        subtitle: str = '',
                        sentto_id: str = '',
                        sentto_dsc: str = '',
                        active: bool = False,
                        valid: bool = False,
                        icon: str = '',
                        extension: str = '',
                        ):
        super().__init__(id, title)

        self._date = date
        self._date_dsc = date_dsc
        self._country = country
        self._country_dsc = country_dsc
        self._group = group
        self._group_dsc = group_dsc
        self._purpose = purpose
        self._purpose_dsc = purpose_dsc
        self._sentby_id = sentby_id
        self._sentby_dsc = sentby_dsc
        self._subtitle = subtitle
        self._sentto_id = sentto_id
        self._sentto_dsc = sentto_dsc
        self._active = active
        self._valid = valid
        self._icon = icon
        self._extension = extension
        self.search_text =  self.id + ' ' + date + ' ' + date_dsc + ' ' + group + ' ' + group_dsc + ' ' + \
                            country + ' ' + country_dsc + ' ' + purpose + ' ' + purpose_dsc + ' ' + \
                            sentby_id + ' ' + sentby_dsc + ' ' + title + ' ' + subtitle + ' ' + \
                            sentto_id + ' ' + sentto_dsc + ' ' + extension

    @GObject.Property
    def date(self):
        return self._date

    @GObject.Property
    def date_dsc(self):
        return self._date_dsc

    @GObject.Property
    def country(self):
        return self._country

    @GObject.Property
    def extension(self):
        return self._extension

    @GObject.Property
    def country_dsc(self):
        return self._country_dsc

    @GObject.Property
    def group(self):
        return self._group

    @GObject.Property
    def group_dsc(self):
        return self._group_dsc

    @GObject.Property
    def purpose(self):
        return self._purpose

    @GObject.Property
    def purpose_dsc(self):
        return self._purpose_dsc

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


class Concept(MiAZModel):
    __gtype_name__ = 'Concept'
    __title__ = _('Concept')
    __title_plural__ = _('Concepts')
    __config_name__ = 'concepts'
    __config_name_available__ = 'concepts'
    __config_name_used__ = 'concepts'


class Country(MiAZModel):
    __gtype_name__ = 'Country'
    __title__ = _('Country')
    __title_plural__ = _('Countries')
    __config_name__ = 'countries'
    __config_name_available__ = 'countries'
    __config_name_used__ = 'countries'

    def __init__(self, id: str, title: str = '', icon: str = ''):
        super().__init__(id, title)
        self._icon = icon

    @GObject.Property
    def icon(self):
        return self._icon


class Date(MiAZModel):
    __gtype_name__ = 'Date'
    __title__ = _('Date')
    __title_plural__ = _('Dates')
    __config_name__ = 'dates'
    __config_name_available__ = 'dates'
    __config_name_used__ = 'dates'


class Document(MiAZModel):
    __gtype_name__ = 'Document'
    __title__ = _('Document')
    __title_plural__ = _('Documents')
    __config_name__ = 'documents'
    __config_name_available__ = 'documents'
    __config_name_used__ = 'documents'


class Extension(MiAZModel):
    __gtype_name__ = 'Extension'
    __title__ = _('Extension')
    __title_plural__ = _('Extensions')
    __config_name__ = 'extensions'
    __config_name_available__ = 'extensions'
    __config_name_used__ = 'extensions'


class File(MiAZModel):
    __gtype_name__ = 'File'
    __title__ = _('File')
    __title_plural__ = _('Files')
    __config_name__ = 'files'
    __config_name_available__ = 'files'
    __config_name_used__ = 'files'


class Group(MiAZModel):
    __gtype_name__ = 'Group'
    __title__ = _('Group')
    __title_plural__ = _('Groups')
    __config_name__ = 'groups'
    __config_name_available__ = 'groups'
    __config_name_used__ = 'groups'


class Person(MiAZModel):
    __gtype_name__ = 'Person'
    __title__ = _('Natural or legal entity')
    __title_plural__ = _('Natural or legal entities')
    __config_name__ = 'people'
    __config_name_available__ = 'people'
    __config_name_used__ = 'people'


class Purpose(MiAZModel):
    __gtype_name__ = 'Purpose'
    __title__ = _('Purpose')
    __title_plural__ = _('Purposes')
    __config_name__ = 'purposes'
    __config_name_available__ = 'purposes'
    __config_name_used__ = 'purposes'


class Repository(MiAZModel):
    __gtype_name__ = 'Repository'
    __title__ = _('Repository')
    __title_plural__ = _('Repositories')
    __config_name__ = 'repositories'
    __config_name_available__ = 'repositories'
    __config_name_used__ = 'repositories'


class SentBy(Person):
    __gtype_name__ = 'SentBy'
    __title__ = _('Sender')
    __title_plural__ = _('Senders')
    __config_name__ = 'people'
    __config_name_available__ = 'people'
    __config_name_used__ = 'senders'


class SentTo(Person):
    __gtype_name__ = 'SentTo'
    __title__ = _('Recipient')
    __title_plural__ = _('Recipients')
    __config_name__ = 'recipients'
    __config_name_available__ = 'people'
    __config_name_used__ = 'recipients'


class Plugin(MiAZModel):
    __gtype_name__ = 'Plugin'
    __title__ = _('Plugin')
    __title_plural__ = _('Plugins')
    __config_name__ = 'plugins'
    __config_name_available__ = 'plugins'
    __config_name_used__ = 'plugins'
