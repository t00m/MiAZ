# pylint: disable=E1101

"""
# File: helloworld.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin example for MiAZ
"""

import os
import sys
from gettext import gettext as _


from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
from example.test import PluginTest

plugin_info = {
        'Module':        'helloworld',
        'Name':          'HelloWorld',
        'Loader':        'Python3',
        'Description':   _('Hello World Example Plugin'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.5',
        'Category':      'Support and Help',
        'Subcategory':   'Guides and Tutorials'
    }

class HelloWorld(MiAZExtension):
    __gtype_name__ = 'HelloWorldPlugin'
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

        ## Listen to 'workspace-loaded' signal to start up the plugin
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        """Plugin deactivation"""
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=self._on_menuitem_activate)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def _on_menuitem_activate(self, *args):
        test = PluginTest(self.app)
