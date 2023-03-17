#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import tempfile

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger


class Export2CSV(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2CSVPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Export2CSV')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.util = self.backend.util
        self.workspace = API.app.get_workspace()
        self.workspace.connect("extend-menu-export", self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        API = self.object
        # ~ API.app.disconnect_by_func(self.processInputCb)

    def add_menuitem(self, *args):
        submenu_export = self.app.get_widget('workspace-submenu-export')
        menuitem = self.factory.create_menuitem('export-to-csv', '...to CSV', self.export, None, [])
        submenu_export.append_item(menuitem)
        self.log.debug("Added menu item to submenu export for exporting to CSV")

    def export(self, *args):
        import csv
        fields = ['Date', 'Country', 'Group', 'Send by', 'Purpose', 'Concept', 'Send to', 'Extension']
        items = self.workspace.get_selected_items()
        rows = []
        for item in items:
            name, ext = self.util.filename_details(item.id)
            row = name.split('-')
            row.append(ext)
            rows.append(row)
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.csv')
        with open(filepath, 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)
            csvwriter.writerows(rows)
        self.util.filename_display(filepath)