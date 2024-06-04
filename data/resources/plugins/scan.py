#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Scan plugin
"""

import os
import re
import glob
import tempfile
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog


class MiAZImportFromScanPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZImportFromScanPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.AddFromScanner')

    def _search_scan_app(self):
        desktop_files = glob.glob('/usr/share/applications/*.desktop')
        DAI = Gio.DesktopAppInfo()
        self.scanapp = None
        for desktop_path in desktop_files:
            desktop_name = os.path.basename(desktop_path)
            try:
                appinfo = DAI.new(desktop_name)
                if re.search('scan', appinfo.get_categories(), re.IGNORECASE):
                    self.scanapp = appinfo
                    break;
            except TypeError as error:
                pass

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.workspace = self.app.get_widget('workspace')
        self._search_scan_app()
        if self.scanapp is not None:
            self.workspace.connect('workspace-loaded', self.add_menuitem)
            self.log.debug("Plugin Scan activated")

    def do_deactivate(self):
        # Remove button
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-in-add-document') is None:
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = self.factory.create_menuitem('add_from_scan', '... from scanner', self.exec_scanner, None, [])
            menu_add.append_item(menuitem)

    def exec_scanner(self, *args):
        if self.scanapp is not None:
            self.scanapp.launch()
