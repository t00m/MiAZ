# pylint: disable=E1101

"""
# File: export2text.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items filenames to plain text
"""

import os
import tempfile
from gettext import gettext as _

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'export2text',
        'Name':          'MiAZExport2Text',
        'Loader':        'Python3',
        'Description':   _('Export to text editor'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.6',
        'Category':      'Documents',
        'Subcategory':   'Export',
        'MenuEntries':   [
            ('export', _('Export to text editor')),
        ]
    }


class Export2Text(MiAZExtension):
    """Export the selected document filenames to a plain text file.

    Adds a workspace menu entry. Writes one filename per line and opens the
    file with the default text editor.
    """
    __gtype_name__ = 'MiAZExport2TextPlugin'
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
        self.srvdlg = self.app.get_service('dialogs')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')

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
            self.plugin.install_menu_entries({'export': self.export})
            self.plugin.set_started(started=True)

    def export(self, *args):
        """Write the selected document filenames to a text file and open it.

        One filename per line. The file is created in the repository temp dir
        and opened with the default text editor. Does nothing when no items
        are selected.
        """
        ENV = self.app.get_env()
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        text = ""
        for item in items:
            text += f"{item.id}\n"

        # mkstemp returns an open file descriptor we do not use; close it and
        # reopen the path for writing.
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.txt')
        os.close(fp)
        with open(filepath, 'w', encoding='utf-8') as temp:
            temp.write(text)
        self.util.filename_display(filepath)
        self.srvdlg.show_toast(_('Check your default text editor'))
