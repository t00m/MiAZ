#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger


class MiAZStatsBrowser(Gtk.Box):



class MiAZStatsPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZStatsPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Stats')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')

        stack = self.get_widget('stack')
        widget_stats = self.get_widget('stats')
        if widget_stats is None:
            widget_stats = self.add_widget('stats', MiAZStatsBrowser(self))
            page_stats = stack.add_titled(widget_stats, 'stats', 'MiAZ')
            page_stats.set_icon_name('MiAZ')
            page_stats.set_visible(True)