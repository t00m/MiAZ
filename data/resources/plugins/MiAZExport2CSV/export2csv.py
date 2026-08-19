# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import csv
import tempfile
from gettext import gettext as _

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'export2csv',
        'Name':          'MiAZExport2CSV',
        'Loader':        'Python3',
        'Description':   _('Export to CSV'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.5',
        'Category':      'Data Management',
        'Subcategory':   'Export'
    }


class Export2CSV(MiAZExtension):
    """Export the selected documents to a CSV file.

    Adds a workspace menu entry. Each selected document becomes one CSV row,
    with the seven filename fields split into columns plus the extension.
    """
    __gtype_name__ = 'MiAZExport2CSVPlugin'
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
        self.util = self.app.get_service('util')
        self.actions = self.app.get_service('actions')
        self.srvdlg = self.app.get_service('dialogs')

        # Connect signals
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=self.export)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def export(self, *args):
        """Write the selected documents to a CSV file and open it.

        Each selected item becomes one row, with its seven filename fields
        split into columns plus the file extension. The file is created in the
        repository temp dir and opened with the default spreadsheet
        application. Does nothing when no items are selected.
        """
        ENV = self.app.get_env()
        fields = [_('Date'), _('Country'), _('Group'), _('Send by'), _('Purpose'), _('Concept'), _('Send to'), _('Extension')]
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        rows = []
        for item in items:
            name, ext = self.util.filename_details(item.id)
            row = name.split('-')
            row.append(ext)
            rows.append(row)

        # mkstemp returns an open file descriptor we do not use; close it and
        # reopen the path with the csv writer.
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.csv')
        os.close(fp)
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)
            csvwriter.writerows(rows)
        self.util.filename_display(filepath)
        self.srvdlg.show_toast(_("Check your default spreadsheet application"))
