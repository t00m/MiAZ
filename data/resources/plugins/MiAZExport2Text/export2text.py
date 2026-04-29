#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2text.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items filenames to plain text
"""

import tempfile
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'export2text',
        'Name':          'MiAZExport2Text',
        'Loader':        'Python3',
        'Description':   _('Export to text editor'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Data Management',
        'Subcategory':   'Export'
    }


class Export2Text(MiAZExtension):
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
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.warning("Deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Export to text editor'), callback=self.export)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def export(self, *args):
        ENV = self.app.get_env()
        parent = self.workspace.get_root()
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        text = ""
        for item in items:
            text += f"{item.id}\n"
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.txt')
        with open(filepath, 'w') as temp:
            temp.write(text)
        self.util.filename_display(filepath)
        title = _('Export successful')
        body = _('Check your default text editor')
        self.srvdlg.show_toast(body)
