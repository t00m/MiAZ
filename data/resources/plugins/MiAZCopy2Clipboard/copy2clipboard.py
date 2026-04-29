#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: copy2clipboard.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items filenames to plain text
"""

from gettext import gettext as _

from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'copy2clipboard',
        'Name':          'MiAZCopy2Clipboard',
        'Loader':        'Python3',
        'Description':   _('Copy to clipboard'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Data Management',
        'Subcategory':   'Export'
    }

class Copy2Clipboard(MiAZExtension):
    __gtype_name__ = 'MiAZCopy2ClipboardPlugin'
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

        ## Get services
        self.srvdlg = self.app.get_service('dialogs')
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')

        ## Get widgets
        self.workspace = self.app.get_widget('workspace')

        # Connect signals to startup
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.warning("Deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Copy document names'), callback=self.export, shortcuts=['<Control>c'])

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def export(self, *args):
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        title = _('{num_items} documents copied to clipboard').format(num_items=len(items))
        text = ""
        for item in items:
            text += _('{item}\n').format(item=item.id)
        self.workspace.get_clipboard().set(text.strip())
        body = ''
        parent = self.workspace.get_root()
        self.srvdlg.show_toast(title)
