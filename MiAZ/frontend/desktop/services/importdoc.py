#!/usr/bin/python3
# File: importdoc.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Core service to add documents to the repository from the
#              local filesystem.

import os
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog


class MiAZImportDoc(GObject.GObject):
    """Add documents to the repository from the local filesystem.

    The 'Add new document(s)' action every repository needs on day one, so
    it lives in core rather than behind a togglable plugin. It builds its
    own menu item so the headerbar 'Add' menu can show it regardless of
    which Import plugins are enabled.
    """
    __gtype_name__ = 'MiAZImportDoc'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZImportDoc')
        self.util = app.get_service('util')
        self.factory = app.get_service('factory')
        self.repository = app.get_service('repo')
        self.srvdlg = app.get_service('dialogs')
        self.menuitem = self.factory.create_menuitem(
            name='import-doc', label=_('Add new document(s)'),
            callback=self.import_files, shortcuts=['<Control>Insert'])

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
