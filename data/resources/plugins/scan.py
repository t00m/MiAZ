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

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        scanapp = self._search_scan_app()
        if scanapp is not None:
            workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def _search_scan_app(self):
        scanapp = None
        try:
            desktop_files = glob.glob('/usr/share/applications/*.desktop')
            DAI = Gio.DesktopAppInfo()
            for desktop_path in desktop_files:
                desktop_name = os.path.basename(desktop_path)
                try:
                    appinfo = DAI.new(desktop_name)
                    categories = appinfo.get_categories()
                    if categories is not None:
                        if re.search('scan', categories, re.IGNORECASE):
                            scanapp = appinfo
                            break
                except TypeError as error:
                    pass
                    # ~ self.log.error(f"Plugin 'scan' couldn't be activated: {error}")

        except AttributeError as error:
            # Not available in Windows/MSYS2
            self.log.error(f"Plugin 'scan' couldn't be activated: {error}")
        return scanapp

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-in-add-scan') is None:
            factory = self.app.get_service('factory')
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = factory.create_menuitem('add_from_scan', '... from scanner', self.exec_scanner, None, [])
            self.app.add_widget('workspace-menu-in-add-scan', menuitem)
            menu_add.append_item(menuitem)

    def exec_scanner(self, *args):
        scanapp = self._search_scan_app()
        if scanapp is not None:
            scanapp.launch()
