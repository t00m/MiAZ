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

from MiAZ.backend.log import MiAZLog


class MiAZWorkspaceToggleViewPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZWorkspaceToggleViewPlugin'
    object = GObject.Property(type=GObject.Object)
    info = {}

    def do_activate(self):
        self.app = self.object.app
        self.log = MiAZLog('Plugin.MiAZWsToggleView')
        plugin_file = __file__.replace('.py', '.plugin')
        self.info = self.object.get_plugin_attributes(plugin_file)
        module = self.info['Module']
        self.log.error(f"Registering widget plugin plugin-{module}")
        self.app.add_widget(f'plugin-{module}', self)
        actions = self.app.get_service('actions')
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)
        actions.connect('settings-loaded', self._on_settings_loaded)
        self.log.debug("Plugin activated")

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
            menuitem = factory.create_menuitem('togglebutton_workspace_view', 'Workspace toggle view', None, None, [])
            self.app.add_widget('window-headerbar-togglebutton-workspace-view', menuitem)

            # ~ # Add plugin to its default (sub)category
            # ~ category = self.app.get_widget('workspace-menu-plugins-visualisation-and-diagrams-dashboard-widgets')
            category = self.info['Category']
            subcategory = self.info['Subcategory']
            subcategory_submenu = self.app.install_plugin_menu(category, subcategory)
            subcategory_submenu.append_item(menuitem)

            # This is a common action: add to shortcuts
            # ~ menu_shortcut_import = self.app.get_widget('workspace-menu-shortcut-import')
            # ~ menu_shortcut_import.append_item(menuitem)

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
