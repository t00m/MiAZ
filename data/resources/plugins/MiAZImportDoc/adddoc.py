#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin


class MiAZAddDocumentPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDocumentPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None
    name = 'AddDocs'     # Plugin internal name
    desc = '... document(s)'   # Plugin menuitem entry
    file = __file__.replace('.py', '.plugin')

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self.file, self)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Connect signals to startup
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=self.import_files)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def import_files(self, *args):
        self.factory.create_filechooser_for_files(self._on_filechooser_response)

    def _on_filechooser_response(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
            if files:

                filepaths = [file.get_path() for file in files]
                for source in filepaths:
                    btarget = self.util.filename_normalize(source)
                    target = os.path.join(self.repository.docs, btarget)
                    self.util.filename_import(source, target)
                self.srvdlg.show_info(title='Import documents', body=f'{len(filepaths)} documents imported successfully')
        except Exception as error:
            self.srvdlg.show_error(title='Error selecting files', body=error)
            self.log.error(f"Error selecting files: {error}")

