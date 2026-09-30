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


from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.models import Country, Date, Group
from MiAZ.backend.models import Purpose, SentBy, SentTo

plugin_info = {
        'Module':        'export2zip',
        'Name':          'MiAZExport2Zip',
        'Loader':        'python',
        'Description':   _('Compress documents into a ZIP file'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Category':      'Documents',
        'Subcategory':   'Export',
        'MenuEntries':   [
            ('export', _('Create a ZIP file')),
        ]
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
        self.srvprg = self.app.get_service('progress')

        # Connect startup signals
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
            self.plugin.install_menu_entries({'export': self.export})
            self.plugin.set_started(started=True)

    def export(self, *args):
        self.items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return
        self.target_dir = None
        self.factory.create_filechooser_for_directories(self._on_select_folder_response)

    def _on_select_folder_response(self, dialog, result):
        """Take the target directory, then hand the work to a worker.

        Copying every selected document, compressing the lot and deleting the
        temporary tree used to happen right here, on the main loop, inside the
        file chooser's response handler. A few large scans was enough for GNOME
        to decide the window had stopped answering and put up its "not
        responding" dialog. MiAZExport2Dir already does this properly and is
        the model: the plain data is gathered here, and nothing below the
        progress dialog touches GTK.
        """
        try:
            folder = dialog.select_folder_finish(result)
        except Exception as error:
            self.log.debug(f"No directory was chosen: {error}")
            return

        self.target_dir = folder.get_path()
        if not self.target_dir or not os.path.exists(self.target_dir):
            self.srvdlg.show_error(
                title=_('Export error'),
                body=_('That directory is not there any more.'))
            return

        # Names, not workspace items: a model row belongs to the widget that
        # owns it, and the worker must not reach into one.
        names = [item.id for item in self.items]
        target_dir = self.target_dir
        self.srvprg.run(
            lambda report: self._compress_all(names, target_dir, report),
            title=_('Create a ZIP file'),
            message=_('Compressing {total} documents…').format(total=len(names)),
            parent=self.app.get_widget('window'),
            on_close=lambda ok, result: self._on_export_closed(ok, target_dir))

    def _compress_all(self, names, target_dir, report) -> str:
        """Copy, compress and tidy up. Runs in a worker thread: no GTK here."""
        ENV = self.app.get_env()
        staging = self.util.get_temp_dir()
        # Named before the copying, so the summary below has it whatever
        # happens in between.
        zip_name = f"{os.path.basename(staging)}.zip"
        self.util.directory_create(staging)
        try:
            for position, name in enumerate(names, start=1):
                report(_('Copying {name}').format(name=name),
                       position / len(names))
                source = os.path.join(self.repository.docs, name)
                self.util.filename_copy(source, staging)

            report(_('Compressing…'), None)
            staged_zip = os.path.join(ENV['LPATH']['TMP'], zip_name)
            self.util.zip(staged_zip, staging)
            # This renames the exported archive, not a repository document, so
            # keep its name as it is (no uppercase enforcement).
            self.util.filename_rename(staged_zip,
                                      os.path.join(target_dir, zip_name),
                                      upper=False)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return _('{total} documents compressed into {name}').format(
            total=len(names), name=zip_name)

    def _on_export_closed(self, ok, target_dir):
        """Open the directory once the dialog is gone and the UI is usable."""
        if not ok:
            return
        self.util.directory_open(target_dir)
        self.srvdlg.show_toast(_('Check your default file browser'))

