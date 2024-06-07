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

from MiAZ.backend.log import MiAZLog


class Export2Text(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2TextPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.Export2Text')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        API = self.object
        API.app.disconnect_by_func(self.add_menuitem)

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-multiple-menu-export-item-export2text') is None:
            submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
            menuitem = self.factory.create_menuitem('export-to-text', _('...to plain text'), self.export, None, [])
            submenu_export.append_item(menuitem)
            self.app.add_widget('workspace-menu-multiple-menu-export-item-export2text', menuitem)

    def export(self, *args):
        ENV = self.app.get_env()
        items = self.workspace.get_selected_items()
        text = ""
        for item in items:
            text += "%s\n" % item.id
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.txt')
        with open(filepath, 'w') as temp:
            temp.write(text)
        temp.close()
        self.util.filename_display(filepath)
