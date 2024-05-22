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

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog


class MiAZImportFromScanPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZImportFromScanPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Scan')
        self._search_scan_app()

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

        # ~ if found is not None:
            # ~ name=appinfo.get_display_name()
            # ~ self.icon_name=appinfo.get_string("Icon")
            # ~ description=appinfo.get_description() or appinfo.get_generic_name() or ""
            # ~ keywords=appinfo.get_keywords()
            # ~ app_id=appinfo.get_id()
            # ~ executable=os.path.basename(appinfo.get_string("TryExec") or appinfo.get_executable() or "")
            # ~ self.log.info("Scan app: %s (%s) -> %s", name, executable, description)
            # ~ self.log.info(appinfo.list_actions())
            # ~ appinfo.launch()
        # ~ else:
            # ~ self.icon_name = ''


    def do_activate(self):
        API = self.object
        self.app = API.app
        self.factory = self.app.get_service('factory')
        button = self.app.get_widget('miaz-import-button-popover')
        if self.scanapp is not None:
            self.icon_name=self.scanapp.get_string("Icon")
            btnImportFromScan = self.factory.create_button(icon_name=self.icon_name, callback=self.callback)
            self.rowImportScan = self.factory.create_actionrow(title=_('Scan document'), subtitle=_('Open the scan application'), suffix=btnImportFromScan)
        else:
            self.rowImportScan = self.factory.create_actionrow(title=_('No scanner app found'), subtitle=_('FInd and install a scanner app from the Software catalog'))
        button.add_widget(self.rowImportScan)
        self.log.debug("Plugin Scan activated")

    def do_deactivate(self):
        # Remove entry from popover
        button = self.app.get_widget('miaz-import-button-popover')
        button.remove_widget(self.rowImportScan)

    def callback(self, *args):
        if self.scanapp is not None:
            self.scanapp.launch()
