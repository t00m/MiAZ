#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: scan.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Scan plugin
"""

import os
import re
import glob
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'scan',
        'Name':          'MiAZImportFromScan',
        'Loader':        'Python3',
        'Description':   _('Import document from scanner'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Data Management',
        'Subcategory':   'Import'
    }


class MiAZImportFromScanPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZImportFromScanPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.factory = self.app.get_service('factory')

        # Connect signals to startup
        self.workspace = self.app.get_widget('workspace')

        # Check any scan app and connect signal to startup
        scanapp = self._search_scan_app()
        if scanapp is not None:
            self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.warning("Deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Scan a document'), callback=self.exec_scanner)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

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
                    self.log.debug(f"Skipping desktop entry '{desktop_name}': {error}")

        except AttributeError as error:
            # Not available in Windows/MSYS2
            self.log.error(f"Plugin 'scan' couldn't be activated: {error}")
        return scanapp

    def exec_scanner(self, *args):
        scanapp = self._search_scan_app()
        if scanapp is not None:
            scanapp.launch()
