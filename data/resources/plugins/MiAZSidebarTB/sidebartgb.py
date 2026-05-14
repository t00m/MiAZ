#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: sidebartgb.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Sidebar toggle button plugin
"""

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'sidebartgb',
        'Name':          'MiAZSidebarTB',
        'Loader':        'Python3',
        'Description':   _('Toggle sidebar'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      'Customisation and Personalisation',
        'Subcategory':   'User Interface'
    }


class MiAZSidebarTBPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZSidebarTBPlugin'
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
        self.factory = self.app.get_service('factory')

        # Connect signals to startup
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        tgb = self.app.get_widget('workspace-togglebutton-sidebar')
        if tgb is not None:
            parent = tgb.get_parent()
            if parent is not None:
                parent.remove(tgb)
        evk = self.app.get_widget('window-event-controller')
        if hasattr(self, '_key_handler'):
            evk.disconnect(self._key_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # No need of menu item for plugin

            sidebar = self.app.get_widget('sidebar')
            hdb_left = self.app.get_widget('headerbar-left-box')
            tgbSidebar = self.app.get_widget('workspace-togglebutton-sidebar')
            if tgbSidebar is None:
                tgbSidebar = self.factory.create_button_toggle('io.github.t00m.MiAZ-sidebar-show-left-symbolic', callback=self.toggle_sidebar)
                self.app.add_widget('workspace-togglebutton-sidebar', tgbSidebar)
                tgbSidebar.set_tooltip_text("Show sidebar and filters")
                tgbSidebar.set_active(True)
                tgbSidebar.set_hexpand(False)
                tgbSidebar.add_css_class('dimmed')

                visible = self.plugin.get_config_key('icon_visible')
                if visible is None:
                    visible = True
                    self.plugin.set_config_key('icon_visible', True)
                tgbSidebar.set_visible(visible)

                hdb_left.append(tgbSidebar)

                evk = self.app.get_widget('window-event-controller')
                self._key_handler = evk.connect("key-pressed", self._on_key_press)

                self.log.debug("Plugin sidebartgb activated")

            # Plugin configured
            self.plugin.set_started(started=True)

    def toggle_sidebar(self, *args):
        """ Sidebar not visible when active = False"""
        sidebar = self.app.get_widget('sidebar')
        tgbSidebar = self.app.get_widget('workspace-togglebutton-sidebar')
        active = tgbSidebar.get_active()
        sidebar.set_visible(active)

    def _on_key_press(self, event, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            tgbSidebar = self.app.get_widget('workspace-togglebutton-sidebar')
            active = tgbSidebar.get_active()
            tgbSidebar.set_active(not active)

    def _on_settings_loaded(self, *args):
        group = self.app.get_widget('window-preferences-page-aspect-group-ui')
        row = Adw.SwitchRow(title=_("Display sidebar toggle button?"))
        row.connect('notify::active', self._on_activate_setting)
        tgbSidebar = self.app.get_widget('workspace-togglebutton-sidebar')
        visible = tgbSidebar.get_visible()
        row.set_active(visible)
        group.add(row)

    def _on_activate_setting(self, row, gparam):
        # Set togglebutton status
        togglebutton = self.app.get_widget('workspace-togglebutton-sidebar')
        visible = row.get_active()
        togglebutton.set_visible(visible)

        # Update plugin config
        self.plugin.set_config_key('icon_visible', visible)

    def show_settings(self, widget):
        # Build preferences dialog
        dialog = Adw.PreferencesDialog()
        desc = self.plugin.get_plugin_info_key('Description')
        page_title = _(desc)
        page_icon = "io.github.t00m.MiAZ-preferences-ui"
        page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        dialog.add(page)
        group = Adw.PreferencesGroup()
        group.set_title('User interface')
        page.add(group)

        # Row for option "Display Sidebar Togglebutton?"
        row = Adw.SwitchRow(title=_("Display Sidebar togglebutton?"))
        row.connect('notify::active', self._on_activate_setting)

        config = self.plugin.get_config_data()
        try:
            visible = config['icon_visible']
        except KeyError:
            visible = config['icon_visible'] = True
            self.plugin.set_config_data(config)

        tgbWSToggleView = self.app.get_widget('workspace-togglebutton-sidebar')
        row.set_active(visible)
        group.add(row)

        dialog.present(widget.get_root())
