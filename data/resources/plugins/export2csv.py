#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import csv
import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class Export2CSV(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2CSVPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.Export2CSV')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-multiple-menu-export-item-export2csv') is None:
            factory = self.app.get_service('factory')
            submenu_export_multi = self.app.get_widget('workspace-menu-selection-submenu-export')
            menuitem = factory.create_menuitem('export-to-csv', _('...to CSV'), self.export, None, [])
            self.app.add_widget('workspace-menu-multiple-menu-export-item-export2csv', menuitem)
            submenu_export_multi.append_item(menuitem)

    def export(self, *args):
        util = self.app.get_service('util')
        actions = self.app.get_service('actions')
        srvdlg = self.app.get_service('dialogs')
        workspace = self.app.get_widget('workspace')
        window = workspace.get_root()
        ENV = self.app.get_env()
        fields = [_('Date'), _('Country'), _('Group'), _('Send by'), _('Purpose'), _('Concept'), _('Send to'), _('Extension')]
        items = workspace.get_selected_items()
        if actions.stop_if_no_items(items):
            return

        rows = []
        for item in items:
            name, ext = util.filename_details(item.id)
            row = name.split('-')
            row.append(ext)
            rows.append(row)
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.csv')
        with open(filepath, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)
            csvwriter.writerows(rows)
        util.filename_display(filepath)
        body = f"<big>Check your default spreadsheet application</big>"
        srvdlg.create(parent=window, dtype='info', title=_('Export successfull'), body=body).present()
