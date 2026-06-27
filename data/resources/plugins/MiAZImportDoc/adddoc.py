#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: adddoc.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for importing documents from filesystem
"""

import os
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'adddoc',
        'Name':          'MiAZImportDoc',
        'Loader':        'Python3',
        'Description':   _('Add new document(s)'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Data Management',
        'Subcategory':   'Import'
    }


class MiAZAddDocumentPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZAddDocumentPlugin'
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
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

        ## Connect signals to startup
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
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Add new document(s)'), callback=self.import_files, shortcuts=['<Control>Insert'])

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def import_files(self, *args):
        self.factory.create_filechooser_for_files(self._on_filechooser_response)

    def _on_filechooser_response(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error as error:
            # Closing the file chooser is a normal action, not an error.
            dismissed = (
                error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED)
                or error.matches(Gtk.DialogError.quark(), Gtk.DialogError.CANCELLED)
            )
            if dismissed:
                self.log.debug("Document import cancelled by the user")
                self.srvdlg.show_toast(_('Document import cancelled'))
                return
            self.log.error(f"Could not open the file chooser: {error.message}")
            self.srvdlg.show_error(
                title=_('Could not open files'),
                body=_('The file chooser could not be opened.\n\n{error}').format(
                    error=error.message))
            return

        if not files:
            return

        imported = 0
        failed = []
        for file in files:
            source = file.get_path()
            try:
                btarget = self.util.filename_normalize(source)
                target = os.path.join(self.repository.docs, btarget)
                self.util.filename_import(source, target)
                imported += 1
            except Exception as error:
                failed.append(os.path.basename(source))
                self.log.error(f"Could not import '{source}': {error}")

        if imported > 0:
            self.srvdlg.show_toast(
                _('{count} documents imported successfully').format(count=imported))
        if failed:
            self.srvdlg.show_error(
                title=_('Some documents could not be imported'),
                body=_('These documents could not be imported:\n\n{items}').format(
                    items='\n'.join(failed)))

