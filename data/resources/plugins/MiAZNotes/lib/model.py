#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: model.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Note model for MiAZNotes plugin
"""

from gettext import gettext as _

from gi.repository import GObject


CATEGORIES = [
    _('General'),
    _('Personal'),
    _('Work'),
    _('Finance'),
    _('Legal'),
    _('Health'),
    _('Reference'),
]

PRIORITIES = [
    _('Low'),
    _('Medium'),
    _('High'),
    _('Critical'),
]

STATUSES = [
    _('Draft'),
    _('In Progress'),
    _('Review'),
    _('Done'),
    _('Archived'),
]

DEFAULT_CATEGORY = 'General'
DEFAULT_PRIORITY = 'Medium'
DEFAULT_STATUS = 'Draft'


class Note(GObject.GObject):
    __gtype_name__ = 'MiAZNotesNote'

    path = GObject.Property(type=str)
    document_id = GObject.Property(type=str)
    author = GObject.Property(type=str)
    category = GObject.Property(type=str)
    date = GObject.Property(type=str)
    priority = GObject.Property(type=str)
    status = GObject.Property(type=str)
    summary = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if value is None:
                continue
            self.set_property(key.replace('_', '-'), value)
