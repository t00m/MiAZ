#!/usr/bin/python3
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

from gi.repository import GObject
from gi.repository import Adw

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

path = os.path.join(os.path.abspath(__file__), 'example')
sys.path.insert(1, os.path.abspath(__file__))
from example.test import PluginTest

plugin_info = {
        'Module':        'helloworld',
        'Name':          'HelloWorld',
        'Loader':        'Python3',
        'Description':   _('Hello World Example Plugin'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
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

        # Get services
        self.actions = self.app.get_service('actions')
        self.srvdlg = self.app.get_service('dialogs')

        ## Listen to 'workspace-loaded' signal to start up the plugin
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

        ## Listen to 'settings-loaded' signal to add custom settings
        self.actions.connect('settings-loaded', self._on_settings_loaded)

    def do_deactivate(self):
        """Plugin deactivation"""
        self.log.warning("Deactivation not implemented. Restart app to disable plugins.")
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

    def _on_settings_loaded(self, *args):
        pass
        # ~ group = self.app.get_widget('window-preferences-page-aspect-group-ui')
        # ~ row = Adw.SwitchRow(title=_("Hello world!"), subtitle=_('Plugin HelloWorld'))
        # ~ row.connect('notify::active', self._on_activate_setting)
        # ~ group.add(row)

    def _on_activate_setting(self, row, gparam):
        active = row.get_active()
        dtype = "info"
        title = _('<big>Row active {active}</big>').format(active=active)
        body = ''
        window = row.get_root()
        dialog = self.srvdlg.create(dtype=dtype, title=title, body=body, widget=None)
        dialog.present(window)

    def show_settings(self):
        self.log.info("Got it!")
