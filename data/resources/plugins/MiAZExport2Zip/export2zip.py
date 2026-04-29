#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2zip.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting documents to ZIP
"""

import os
import shutil
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.models import Country, Date, Group
from MiAZ.backend.models import Purpose, SentBy, SentTo

plugin_info = {
        'Module':        'export2zip',
        'Name':          'MiAZExport2Zip',
        'Loader':        'Python3',
        'Description':   _('Compress documents into a ZIP file'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Data Management',
        'Subcategory':   'Export'
    }

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6


class Export2Zip(MiAZExtension):
    __gtype_name__ = 'MiAZExport2ZipPlugin'
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

        # Get services
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

        # Connect startup signals
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.warning("Deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Create a ZIP file'), callback=self.export)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def export(self, *args):
        self.items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return
        self.target_dir = None
        self.factory.create_filechooser_for_directories(self._on_select_folder_response)

    def _on_select_folder_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self.target_dir = folder.get_path()
            target_dir_valid = os.path.exists(self.target_dir)
            if self.target_dir is not None and target_dir_valid:
                ENV = self.app.get_env()
                dir_zip = self.util.get_temp_dir()
                self.util.directory_create(dir_zip)
                for item in self.items:
                    source = os.path.join(self.repository.docs, item.id)
                    target = dir_zip
                    self.util.filename_copy(source, target)
                basename = os.path.basename(dir_zip)
                zip_file = f"{basename}.zip"
                zip_target = os.path.join(ENV['LPATH']['TMP'], zip_file)
                source = zip_target
                target = os.path.join(self.target_dir, zip_file)
                self.util.zip(target, dir_zip)
                self.util.filename_rename(source, target)
                shutil.rmtree(dir_zip)
                self.util.directory_open(self.target_dir)

                title = _('Export successful')
                body = _('Check your default file browser')
                parent = self.workspace.get_root()
                self.srvdlg.show_toast(body)

        except Exception as error:
            self.srvdlg.show_error(title=_('Export error'), body=str(error))
            self.log.error(f"Error selecting files: {error}")
