#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Scan plugin
"""

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin

plugin_info = {
        'Module':        'wstoggleview',
        'Name':          'MiAZWSToggleView',
        'Loader':        'Python3',
        'Description':   _('Toggle Workspace view'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Customisation and Personalisation',
        'Subcategory':   'User Interface'
    }

class MiAZWorkspaceToggleViewPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZWorkspaceToggleViewPlugin'
    object = GObject.Property(type=GObject.Object)
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
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.error("Plugin deactivated")

    def check_plugin(self, *args):
        self.log.info(f"Plugin loaded? {self.plugin_info.is_loaded()}")

    def startup(self, *args):
        if not self.plugin.started():
            # No menu item for plugin

            # ToggleButton
            hdb_left = self.app.get_widget('headerbar-left-box')
            tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
            if tgbWSToggleView is None:
                tgbWSToggleView = self.factory.create_button_toggle('io.github.t00m.MiAZ-view-details', callback=self.toggle_workspace_view)
                self.app.add_widget('workspace-togglebutton-view', tgbWSToggleView)
                tgbWSToggleView.set_tooltip_text(_("Show documents raw names"))
                tgbWSToggleView.set_active(False)
                tgbWSToggleView.set_hexpand(False)
                visible = self.plugin.get_config_key('icon_visible')
                if visible is None:
                    visible = True
                    self.plugin.set_config_key('icon_visible', True)
                tgbWSToggleView.set_visible(visible)
                hdb_left.append(tgbWSToggleView)

                evk = self.app.get_widget('window-event-controller')
                evk.connect("key-pressed", self._on_key_press)

            # Plugin configured
            self.plugin.set_started(started=True)

    def toggle_workspace_view(self, *args):
        """ Sidebar not visible when active = False"""
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
            self.workspace.set_default_columnview_attrs()

    def _on_key_press(self, event, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'F3':
            tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
            active = tgbWSToggleView.get_active()
            tgbWSToggleView.set_active(not active)

    def _on_activate_setting(self, row, gparam):
        # Set togglebutton status
        togglebutton = self.app.get_widget('workspace-togglebutton-view')
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

        # Row for option "Display Workspace toggle view button?"
        row = Adw.SwitchRow(title=_("Display Workspace toggle view button?"))
        row.connect('notify::active', self._on_activate_setting)

        config = self.plugin.get_config_data()
        try:
            visible = config['icon_visible']
        except:
            visible = config['icon_visible'] = True
            self.plugin.set_config_data(config)

        tgbWSToggleView = self.app.get_widget('workspace-togglebutton-view')
        row.set_active(visible)
        group.add(row)

        dialog.present(widget.get_root())
