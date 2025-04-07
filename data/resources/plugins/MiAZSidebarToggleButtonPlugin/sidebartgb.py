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
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZSidebarToggleButtonPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZSidebarToggleButtonPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.SidebarTgb')
        self.app = None
        self.scanapp = None

    def do_activate(self):
        self.app = self.object.app
        actions = self.app.get_service('actions')
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)
        actions.connect('settings-loaded', self._on_settings_loaded)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-togglebutton-filters') is None:
            factory = self.app.get_service('factory')
            sidebar = self.app.get_widget('sidebar')
            hdb_left = self.app.get_widget('headerbar-left-box')
            tgbSidebar = factory.create_button_toggle('io.github.t00m.MiAZ-sidebar-show-left-symbolic', callback=sidebar.toggle)
            self.app.add_widget('workspace-togglebutton-filters', tgbSidebar)
            tgbSidebar.set_tooltip_text("Show sidebar and filters")
            tgbSidebar.set_active(True)
            tgbSidebar.set_hexpand(False)
            tgbSidebar.get_style_context().add_class(class_name='dimmed')
            # ~ tgbSidebar.get_style_context().remove_class(class_name='flat')
            # ~ tgbSidebar.set_valign(Gtk.Align.CENTER)
            hdb_left.append(tgbSidebar)
            self.log.debug("Plugin sidebartgb initialitez")


            # Create menu item for plugin
            menuitem = factory.create_menuitem('togglebutton_sidebar', 'Toggle sidebar button', None, None, [])
            self.app.add_widget('window-headerbar-togglebutton-sidebar', menuitem)

            # ~ # Add plugin to its default (sub)category
            category = self.app.get_widget('workspace-menu-plugins-visualisation-and-diagrams-dashboard-widgets')
            category.append_item(menuitem)

            # This is a common action: add to shortcuts
            # ~ menu_shortcut_import = self.app.get_widget('workspace-menu-shortcut-import')
            # ~ menu_shortcut_import.append_item(menuitem)

    def _on_settings_loaded(self, *args):
        group = self.app.get_widget('window-preferences-page-aspect-group-ui')
        row = Adw.SwitchRow(title=_("Display sidebar toggle button?"), subtitle=_('Plugin Sidebar ToggleButton'))
        row.connect('notify::active', self._on_activate_setting)
        tgbSidebar = self.app.get_widget('workspace-togglebutton-filters')
        visible = tgbSidebar.get_visible()
        row.set_active(visible)
        group.add(row)

    def _on_activate_setting(self, row, gparam):
        active = row.get_active()
        togglebutton = self.app.get_widget('workspace-togglebutton-filters')
        togglebutton.set_visible(active)




