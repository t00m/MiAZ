#!/usr/bin/python3
# pylint: disable=E1101
# File: importfromzip.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for importing documents from a ZIP file

import os
import shutil
import threading
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.status import MiAZStatus

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
            zip_path = file.get_path()
            self.app.set_status(MiAZStatus.BUSY)
            threading.Thread(
                target=self._import_zip,
                args=(zip_path,),
                daemon=True
            ).start()
        except GLib.Error as err:
            self.log.debug(f"ZIP file selection cancelled or failed: {err.message}")

    def _import_zip(self, zip_path):
        # Background thread: I/O only. Signal emission happens on main thread.
        watcher = self.app.get_service('watcher')
        watcher.set_active(False)
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
                # Keep the real provenance: the zip archive and the entry
                # inside it, not the temporary extraction path.
                origin = {'type': 'zip',
                          'archive': os.path.abspath(zip_path),
                          'entry': os.path.relpath(filepath, extract_dir)}
                copied_targets.append((target, origin))
        except Exception as error:
            self.log.error(f"Error importing ZIP '{zip_path}': {error}")
            error_msg = str(error)
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
            GLib.idle_add(self._finish_import, copied_targets, error_msg)

    def _finish_import(self, targets, error_msg):
        # Main thread: emit signals and update UI.
        watcher = self.app.get_service('watcher')
        if error_msg:
            self.srvdlg.show_error(title=_('Import error'), body=error_msg)
        for target, origin in targets:
            # Emit filename-imported first so the journal can pair provenance
            # with the target before filename-added fires.
            self.util.emit('filename-imported', origin, target)
            self.util.emit('filename-added', target)
        watcher.set_active(True)
        self.app.set_status(MiAZStatus.RUNNING)
        self.app.get_widget('workspace').update()
        if targets:
            msg = _('{count} documents imported from ZIP').format(count=len(targets))
            self.srvdlg.show_toast(msg)
        return False
