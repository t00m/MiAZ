#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: stats.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage MiAZ stats
"""

from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy
from MiAZ.backend.models import SentTo, Date, Extension


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
        self.config = self.backend.conf
        for node in self.config:
            config = self.config[node]
            config.connect('available-updated', self.config_updated)
            config.connect('used-updated', self.config_updated)
        self.log.debug("Stats initialized")

    def config_updated(self, config):
        GLib.idle_add(self.build)

    def build(self, *args):
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

            # Country
            country = fields[1]
            try:
                self.stats[_(Country.__title__)][country] += 1
            except KeyError:
                self.stats[_(Country.__title__)][country] = 1

            # Group
            group = fields[2]
            try:
                self.stats[_(Group.__title__)][group] += 1
            except KeyError:
                self.stats[_(Group.__title__)][group] = 1

            # SentBy
            sentby = fields[3]
            try:
                self.stats[_(SentBy.__title__)][sentby] += 1
            except KeyError:
                self.stats[_(SentBy.__title__)][sentby] = 1

            # Purpose
            purpose = fields[4]
            try:
                self.stats[_(Purpose.__title__)][purpose] += 1
            except KeyError:
                self.stats[_(Purpose.__title__)][purpose] = 1

            # SentTo
            sentto = fields[6]
            try:
                self.stats[_(SentTo.__title__)][sentto] += 1
            except KeyError:
                self.stats[_(SentTo.__title__)][sentto] = 1
        self.log.debug("Stats updated")
        self.emit('stats-updated')

    def get(self):
        return self.stats

