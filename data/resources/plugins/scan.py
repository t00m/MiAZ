#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Scan plugin
"""

import os
import re
import glob

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZImportFromScanPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZImportFromScanPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.AddFromScanner')
        self.app = None
        self.scanapp = None

    def _search_scan_app(self):
        scanapp = None
        desktop_files = glob.glob('/usr/share/applications/*.desktop')
        DAI = Gio.DesktopAppInfo()
        for desktop_path in desktop_files:
            desktop_name = os.path.basename(desktop_path)
            try:
                appinfo = DAI.new(desktop_name)
                if re.search('scan', appinfo.get_categories(), re.IGNORECASE):
                    scanapp = appinfo
                    break
            except TypeError:
                pass
        return scanapp

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        scanapp = self._search_scan_app()
        if scanapp is not None:
            workspace.connect('workspace-loaded', self.add_menuitem)
            self.log.debug("Plugin Scan activated")

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-in-add-document') is None:
            factory = self.app.get_service('factory')
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = factory.create_menuitem('add_from_scan', '... from scanner', self.exec_scanner, None, [])
            menu_add.append_item(menuitem)

    def exec_scanner(self, *args):
        scanapp = self._search_scan_app()
        if scanapp is not None:
            scanapp.launch()
