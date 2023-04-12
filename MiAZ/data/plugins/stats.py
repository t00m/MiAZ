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
from gi.repository import Gtk
from gi.repository import Peas

import pygal

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy
from MiAZ.backend.models import SentTo, Date, Extension

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
        self.stats = self.app.get_service('stats')
        stats = self.stats.get()
        stack = self.app.get_widget('stack')
        widget_stats = self.app.get_widget('stats')
        if widget_stats is None:
            import pygal                                                       # First import pygal
            bar_chart = pygal.Pie(print_values=True)                                            # Then create a bar graph object
            bar_chart.title = 'Documents per country'
            key = _(Country.__title__)
            for code in stats[key]:
                bar_chart.add(code, stats[key][code])
            # ~ bar_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])  # Add some values
            bar_chart.render_to_file('/tmp/bar_chart.svg')                          # Save the svg to a file
            widget_stats = self.app.add_widget('stats', Gtk.Image.new_from_file('/tmp/bar_chart.svg'))
            page_stats = stack.add_titled(widget_stats, 'stats', 'MiAZ')
            page_stats.set_icon_name('MiAZ')
            page_stats.set_visible(True)