#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import tempfile
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZAddDirectoryPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDirectoryPlugin'
    object = GObject.Property(type=GObject.Object)
    enabled = False

    def __init__(self):
        self.log = MiAZLog('Plugin.AddDirectory')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        self.log.debug(self.app.get_widget('workspace-menu-in-add-directory'))
        if self.app.get_widget('workspace-menu-in-add-directory') is None:
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = self.factory.create_menuitem('add_dir', '... documents from a directory', self.actions.import_directory, None, [])
            self.app.add_widget('workspace-menu-in-add-directory', menuitem)
            menu_add.append_item(menuitem)
            self.log.debug("Add menuitem Export to dir")
