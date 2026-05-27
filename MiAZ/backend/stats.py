#!/usr/bin/python3

"""
# File: stats.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage MiAZ stats
"""

from collections import defaultdict
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Field, Group, Country
from MiAZ.backend.models import Purpose, Concept, SentBy
from MiAZ.backend.models import SentTo, Date


class MiAZStats(GObject.GObject):
    __gtype_name__ = 'MiAZStats'
    __gsignals__ = {
        "stats-updated": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZStats')
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.stats = {}

    def _build(self, *args):
        self.stats = {}
        date_title = _(Date.__title__)
        self.stats[date_title] = {
            _('year'): defaultdict(int),
            _('month'): defaultdict(int),
            _('day'): defaultdict(int),
        }
        for prop in [Country, Group, SentBy, Purpose, SentTo]:
            self.stats[_(prop.__title__)] = defaultdict(int)

        for document in self.util.get_files(self.repository.docs):
            fields = self.util.get_fields(document)

            # Date
            adate = self.util.string_to_datetime(fields[0])
            if adate is None:
                continue
            year = str(adate.year)
            month = '%s%02d' % (year, adate.month)
            day = '%s%02d' % (month, adate.day)

            self.stats[date_title][_('year')][year] += 1
            self.stats[date_title][_('month')][month] += 1
            self.stats[date_title][_('day')][day] += 1

            # Rest of metadata
            for prop in [Country, Group, SentBy, Purpose, SentTo]:
                item = fields[Field[prop]]
                self.stats[_(prop.__title__)][item] += 1

        self.log.debug("Stats updated")
        self.emit('stats-updated')

    def get(self):
        if not self.stats:
            self._build()
        return self.stats
