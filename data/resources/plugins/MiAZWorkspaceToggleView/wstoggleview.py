#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Scan plugin
"""

import os
import re
import glob

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.pluginsystem import MiAZPlugin


class MiAZWorkspaceToggleViewPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZWorkspaceToggleViewPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None
    file = __file__.replace('.py', '.plugin')

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self.file)

        ## Get logger
        self.log = self.plugin.get_logger()

        # Connect signals to startup
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.error("Plugin deactivated")

    def check_plugin(self, *args):
        self.log.info(f"Plugin loaded? {self.plugin_info.is_loaded()}")

    def startup(self, *args):
        factory = self.app.get_service('factory')
        hdb_right = self.app.get_widget('headerbar-right-box')
        tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
        if tgbWSToggleView is None:
            tgbWSToggleView = factory.create_button_toggle('io.github.t00m.MiAZ-view-details', callback=self.toggle_workspace_view)
            self.app.add_widget('workspace-togglebutton-view', tgbWSToggleView)
            tgbWSToggleView.set_tooltip_text("Show sidebar and filters")
            tgbWSToggleView.set_active(False)
            tgbWSToggleView.set_hexpand(False)
            hdb_right.append(tgbWSToggleView)

            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=None)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            evk = self.app.get_widget('window-event-controller')
            evk.connect("key-pressed", self._on_key_press)

    def toggle_workspace_view(self, *args):
        """ Sidebar not visible when active = False"""
        workspace = self.app.get_widget('workspace')
        wsview = self.app.get_widget('workspace-view')
        tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
        active = tgbWSToggleView.get_active()
        if active:
            wsview.column_title.set_visible(True)
            wsview.column_title.set_expand(True)
            wsview.column_flag.set_visible(False)
            wsview.column_icon_type.set_visible(False)
            wsview.column_subtitle.set_visible(False)
            wsview.column_group.set_visible(False)
            wsview.column_purpose.set_visible(False)
            wsview.column_sentby.set_visible(False)
            wsview.column_sentto.set_visible(False)
            wsview.column_date.set_visible(False)
        else:
            workspace.set_default_columnview_attrs()

    def _on_key_press(self, event, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'F3':
            tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
            active = tgbWSToggleView.get_active()
            tgbWSToggleView.set_active(not active)

    def _on_settings_loaded(self, *args):
        group = self.app.get_widget('window-preferences-page-aspect-group-ui')
        row = Adw.SwitchRow(title=_("Display Workspace toggle view button?"), subtitle=_('Plugin Workspace toggle view'))
        row.connect('notify::active', self._on_activate_setting)
        tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
        visible = tgbWSToggleView.get_visible()
        row.set_active(visible)
        group.add(row)

    def _on_activate_setting(self, row, gparam):
        active = row.get_active()
        togglebutton = self.app.get_widget('workspace-togglebutton-view')
        togglebutton.set_visible(active)

    def show_settings(self, *args):
        self.log.info(args)
