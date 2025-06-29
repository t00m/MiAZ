#!/usr/bin/python3
# pylint: disable=E1101
# File: adddir.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Add a directory to repository

import os
import glob
from gettext import gettext as _
import threading

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin
from MiAZ.backend.status import MiAZStatus

plugin_info = {
        'Module':        'adddir',
        'Name':          'MiAZAddFromDir',
        'Loader':        'Python3',
        'Description':   _('Add documents from directory'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      _('Data Management'),
        'Subcategory':   _('Import')
    }


class MiAZAddDirectoryPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDirectoryPlugin'
    object = GObject.Property(type=GObject.Object)
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

        # Connect signals to startup
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)

        # Load other services
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')


    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Add documents from directory'), callback=self.select_directory)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def select_directory(self, *args):
        self.factory.create_filechooser_for_directories(self._on_filechooser_response)

    def _on_filechooser_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            filepaths = glob.glob(os.path.join(folder, '*'))
            self.app.set_status(MiAZStatus.BUSY)

            threading.Thread(target=self.import_directory(filepaths), daemon=True).start()

            # ~ for source in filepaths:
                # ~ btarget = self.util.filename_normalize(source)
                # ~ target = os.path.join(self.repository.docs, btarget)
                # ~ self.util.filename_import(source, target)
            # ~ self.srvdlg.show_info(title='Import directory', body=f'{len(filepaths)} documents imported successfully')
        except Exception as error:
            self.srvdlg.show_error(title='Error selecting files', body=error)
            self.log.error(f"Error selecting files: {error}")
            raise

    def import_directory(self, filepaths):
        total_files = len(filepaths)
        watcher = self.app.get_service('watcher')
        watcher.set_active(False)

        for i, filepath in enumerate(filepaths):
            if hasattr(self, 'cancelled') and self.cancelled:
                break

            # Update progress
            progress = (i + 1) / total_files
            self.log.debug(f"Importing file from {filepath}")
            GLib.idle_add(self.update_progress, progress, f"Importing file file {i+1}/{total_files}")

            # Import file
            btarget = self.util.filename_normalize(filepath)
            target = os.path.join(self.repository.docs, btarget)
            GLib.idle_add(self.util.filename_import,filepath, target)

    def update_progress(self, fraction, text):
        self.log.info(f"{fraction} {text}")
        if fraction >= 1.0:
            watcher = self.app.get_service('watcher')
            watcher.set_active(True)
            self.app.set_status(MiAZStatus.RUNNING)
            self.srvdlg.show_info(title='Import directory', body=_('All documents imported successfully'))
