#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: stats.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage MiAZ stats
"""

from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy
from MiAZ.backend.models import SentTo, Date, Extension

Fields = {}
Fields[Date] = 0
Fields[Country] = 1
Fields[Group] = 2
Fields[SentBy] = 3
Fields[Purpose] = 4
Fields[Concept] = 5
Fields[SentTo] = 6


class MiAZStats(GObject.GObject):
    __gtype_name__ = 'MiAZStats'
    __gsignals__ = {
        "stats-updated":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    stats = {}

    def __init__(self, backend):
        super(MiAZStats, self).__init__()
        self.backend = backend
        self.log = get_logger('MiAZStats')
        self.util = self.backend.util

    def _build(self, *args):
        self.stats = {}
        self.stats[_(Date.__title__)] = {}
        self.stats[_(Date.__title__)][_('year')] = {}
        self.stats[_(Date.__title__)][_('month')] = {}
        self.stats[_(Date.__title__)][_('day')] = {}
        self.stats[_(Country.__title__)] = {}
        self.stats[_(Group.__title__)] = {}
        self.stats[_(SentBy.__title__)] = {}
        self.stats[_(Purpose.__title__)] = {}
        self.stats[_(SentTo.__title__)] = {}

        for document in self.util.get_files():
            fields = self.util.get_fields(document)

            # Date
            adate = self.util.string_to_datetime(fields[0])
            year = str(adate.year)
            month = '%s%02d' % (year, adate.month)
            day = '%s%02d' % (month, adate.day)

            try:
                self.stats[_(Date.__title__)][_('year')][year] += 1
            except KeyError:
                self.stats[_(Date.__title__)][_('year')][year] = 1

            try:
                self.stats[_(Date.__title__)][_('month')][month] += 1
            except KeyError:
                self.stats[_(Date.__title__)][_('month')][month] = 1

            try:
                self.stats[_(Date.__title__)][_('day')][day] += 1
            except KeyError:
                self.stats[_(Date.__title__)][_('day')][day] = 1

            # Rest of metadata
            for prop in [Country, Group, SentBy, Purpose, SentTo]:
                item = fields[Fields[prop]]
                try:
                    self.stats[_(prop.__title__)][item] += 1
                except KeyError:
                    self.stats[_(prop.__title__)][item] = 1

        self.log.debug("Stats updated")
        self.emit('stats-updated')

    def get(self):
        self._build()
        return self.stats

