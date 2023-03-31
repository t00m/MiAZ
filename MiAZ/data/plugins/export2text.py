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


class Export2Text(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2TextPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Export2Text')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_factory()
        self.util = self.backend.util
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-menu", self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        API = self.object
        API.app.disconnect_by_func(self.add_menuitem)

    def add_menuitem(self, *args):
        submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
        menuitem = self.factory.create_menuitem('export-to-text', '...to plain text', self.export, None, [])
        submenu_export.append_item(menuitem)

    def export(self, *args):
        items = self.workspace.get_selected_items()
        text = ""
        for item in items:
            text += "%s\n" % item.id
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.txt')
        with open(filepath, 'w') as temp:
            temp.write(text)
        temp.close()
        self.util.filename_display(filepath)