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
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

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
        'Category':      'Data Management',
        'Subcategory':   'Import'
    }


class MiAZAddDirectoryPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZAddDirectoryPlugin'
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

        # Load other services
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

        # Connect signals to startup
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
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Add documents from directory'), callback=self.select_directory, shortcuts=['<Shift>Insert'])

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def select_directory(self, *args):
        self.factory.create_filechooser_for_directories(self._on_filechooser_response)

    def _on_filechooser_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error as err:
            # Closing the folder chooser is a normal action, not an error.
            dismissed = (
                err.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED)
                or err.matches(Gtk.DialogError.quark(), Gtk.DialogError.CANCELLED)
            )
            if dismissed:
                self.log.debug("Directory import cancelled by the user")
                self.srvdlg.show_toast(_('Document import cancelled'))
                return
            self.log.error(f"Could not open the folder chooser: {err.message}")
            self.srvdlg.show_error(
                title=_('Could not open folder'),
                body=_('The folder chooser could not be opened.\n\n{error}').format(
                    error=err.message))
            return

        dirpath = folder.get_path()
        filepaths = glob.glob(os.path.join(dirpath, '*'))
        workspace = self.app.get_widget('workspace')
        suspend = workspace.suspend_updates()
        threading.Thread(target=self.import_directory,
                         args=(filepaths, suspend), daemon=True).start()

    def import_directory(self, filepaths, suspend=None):
        total_files = len(filepaths)
        watcher = self.app.get_service('watcher')
        watcher.set_active(False)
        try:
            for i, filepath in enumerate(filepaths):
                if hasattr(self, 'cancelled') and self.cancelled:
                    break

                progress = (i + 1) / total_files
                self.log.debug(f"Importing file from {filepath}")
                GLib.idle_add(self.update_progress, progress, f"Importing file {i+1}/{total_files}")

                btarget = self.util.filename_normalize(filepath)
                target = os.path.join(self.repository.docs, btarget)
                self.util.filename_import(filepath, target)
        finally:
            workspace = self.app.get_widget('workspace')
            GLib.idle_add(watcher.set_active, True)
            # Ask while still suspended: the gate records the request and runs
            # one refresh when the last holder releases.
            GLib.idle_add(workspace.update)
            if suspend is not None:
                GLib.idle_add(suspend.release)

    def update_progress(self, fraction, text):
        self.log.info(f"{fraction} {text}")
        if fraction >= 1.0:
            self.srvdlg.show_toast(_('All documents imported successfully'))
