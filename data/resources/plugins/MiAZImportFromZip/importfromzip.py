#!/usr/bin/python3
# pylint: disable=E1101
# File: importfromzip.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for importing documents from a ZIP file

import os
import shutil
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.tasks import run_in_background
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':      'importfromzip',
    'Name':        'MiAZImportFromZip',
    'Loader':      'Python3',
    'Description': _('Import documents from a ZIP file'),
    'Authors':     'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':   'Copyright © 2026 Tomás Vírseda',
    'Website':     'http://github.com/t00m/MiAZ',
    'Help':        'http://github.com/t00m/MiAZ/README.adoc',
    'Version':     '0.1.26',
    'Category':    'Data Management',
    'Subcategory': 'Import'
}


class MiAZImportFromZipPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZImportFromZipPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()

        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

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
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(
                name=mnuItemName,
                label=_('Import documents from ZIP'),
                callback=self.select_zip_file
            )
            self.plugin.install_menu_entry(menuitem)
            self.plugin.set_started(started=True)

    def select_zip_file(self, *args):
        parent = self.app.get_widget('window')
        dirpath = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
        initial_folder = Gio.File.new_for_path(dirpath)
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Select a ZIP file'))
        dialog.set_initial_folder(initial_folder)
        zip_filter = Gtk.FileFilter()
        zip_filter.set_name(_('ZIP archives'))
        zip_filter.add_pattern('*.zip')
        dialog.set_default_filter(zip_filter)
        dialog.set_modal(True)
        dialog.open(parent, None, self._on_filechooser_response)

    def _on_filechooser_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error as err:
            self.log.debug(f"ZIP file selection cancelled or failed: {err.message}")
            return

        zip_path = file.get_path()
        # Suspend on the main loop before the worker starts, so there is no
        # window where the watcher is still live and reacting to the copies.
        self._suspend = self.app.get_widget('workspace').suspend_updates()
        self.app.get_service('watcher').set_active(False)
        run_in_background(
            lambda: self._import_zip(zip_path),
            on_done=self._finish_import,
            on_error=self._on_import_crashed,
            name='importfromzip')

    def _import_zip(self, zip_path):
        """Unzip and copy the documents. Returns (targets, error message or None).

        Runs off the main loop, so it does I/O only: the signals go out in
        _finish_import. A failure part way through still returns the documents
        already copied, because those files are on disk and their
        'filename-added' has to be emitted or nothing will know about them.
        """
        extract_dir = self.util.get_temp_dir()
        copied_targets = []
        error_msg = None
        try:
            self.util.directory_create(extract_dir)
            self.util.unzip(zip_path, extract_dir)

            filepaths = []
            for root, _dirs, files in os.walk(extract_dir):
                for name in files:
                    if not name.startswith('.'):
                        filepaths.append(os.path.join(root, name))

            total = len(filepaths)
            for i, filepath in enumerate(filepaths):
                self.log.info(f"Copying document {i + 1}/{total}")
                btarget = self.util.filename_normalize(filepath)
                target = os.path.join(self.repository.docs, btarget)
                self.util.filename_copy(filepath, target)
                copied_targets.append(target)
        except Exception as error:
            self.log.error(f"Error importing ZIP '{zip_path}': {error}")
            error_msg = str(error)
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
        return copied_targets, error_msg

    def _on_import_crashed(self, error):
        """The worker died before it could return anything.

        The watcher and the update gate are turned off before the thread
        starts, so something has to turn them back on. Without this the
        workspace would stop refreshing for the rest of the session.
        """
        self.log.error(f"ZIP import failed: {error}")
        self._finish_import(([], str(error)))

    def _finish_import(self, result):
        # Main thread: emit signals and update UI.
        targets, error_msg = result
        watcher = self.app.get_service('watcher')
        if error_msg:
            self.srvdlg.show_error(title=_('Import error'), body=error_msg)
        for target in targets:
            self.util.emit('filename-added', target)
        watcher.set_active(True)
        # Ask while still suspended, then release: the gate turns however many
        # requests came in during the import into one refresh.
        self.app.get_widget('workspace').update()
        if getattr(self, '_suspend', None) is not None:
            self._suspend.release()
            self._suspend = None
        if targets:
            msg = _('{count} documents imported from ZIP').format(count=len(targets))
            self.srvdlg.show_toast(msg)
