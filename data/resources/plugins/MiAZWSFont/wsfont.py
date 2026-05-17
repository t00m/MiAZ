#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: wsfont.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Workspace font plugin manager
"""

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'wsfont',
        'Name':          'MiAZWSFont',
        'Loader':        'Python3',
        'Description':   _('Modify Workspace font name and size'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.1',
        'Category':      'Customisation and Personalisation',
        'Subcategory':   'User Interface'
    }


class MiAZWSFontPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZWSFontPlugin'
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
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')

        # Connect signals to startup
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        button = self.app.get_widget('workspace-button-font')
        if button is not None:
            parent = button.get_parent()
            if parent is not None:
                parent.remove(button)
        if hasattr(self, '_value_changed_handler'):
            self.spinbutton.disconnect(self._value_changed_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            sidebar = self.app.get_widget('sidebar')
            hdb_left = self.app.get_widget('headerbar-left-box')

            widgets = []
            self.spinbutton = Gtk.SpinButton.new_with_range(8, 48, 2)
            widgets.append(self.spinbutton)
            self.button = self.app.get_widget('workspace-button-font')
            if self.button is None:
                self.button = self.factory.create_button_popover(
                    icon_name='org.gnome.font-viewer-symbolic',
                    title='',
                    widgets=widgets,
                    css_classes=['flat']
                )
                self.button.set_tooltip_text(_('Workspace font size'))
                self.app.add_widget('workspace-button-font', self.button)
                self.button.set_visible(True)
                font_size = self.plugin.get_config_key('font-size')
                if font_size is None:
                    font_size = 12
                    self.plugin.set_config_key('font-size', font_size)
                else:
                    self.log.debug(f"Font size from config is: {font_size}")
                self.spinbutton.set_value(font_size)
                self._on_change_font_properties()
                self._value_changed_handler = self.spinbutton.connect('value-changed', self._on_change_font_properties)
                hdb_left.append(self.button)
                self.log.debug("Plugin WSFont activated")

            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Modify Workspace font name and size'), callback=self._on_show_action_dialog, shortcuts=['<Control>f'])

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def _on_show_action_dialog(self, *args):
        def _update_main_spin_button(spinbutton):
            new_value = spinbutton.get_value()
            self.spinbutton.set_value(new_value)

        srvdlg = self.app.get_service('dialogs')
        spinbutton = Gtk.SpinButton.new_with_range(8, 48, 2)
        font_size = self.plugin.get_config_key('font-size')
        if font_size is None:
            font_size = 12
            self.plugin.set_config_key('font-size', font_size)
        else:
            self.log.debug(f"Font size from config is: {font_size}")
        spinbutton.set_value(font_size)
        spinbutton.connect('value-changed', _update_main_spin_button)
        dialog = srvdlg.show_action(title=_('Modify Workspace font size'), widget=spinbutton)
        dialog.present(self.workspace)

    def _on_font_changed(self, *args):
        self.log.debug("Font changed: %s", args)

    def _on_change_font_properties(self, *args):
        wsview = self.workspace.get_workspace_view()
        font_name = 'Monospace'
        font_size = self.spinbutton.get_value()
        self.spinbutton.set_tooltip_text(f'Current Workspace font size is {font_size}px')
        self.plugin.set_config_key('font-size', font_size)
        css_class= """
            .custom-font {
                font-family: '%s';
                font-size: %dpx;
            }
        """ % (font_name, font_size)
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css_class.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.workspace.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        wsview.add_css_class("custom-font")

    def _on_settings_loaded(self, *args):
        group = self.app.get_widget('window-preferences-page-aspect-group-ui')
        row = Adw.SwitchRow(title=_("Display workspace font button?"))
        row.connect('notify::active', self._on_activate_setting)
        font_button = self.app.get_widget('workspace-button-font')
        visible = font_button.get_visible()
        row.set_active(visible)
        group.add(row)

    def _on_activate_setting(self, row, gparam):
        # Set togglebutton status
        togglebutton = self.app.get_widget('workspace-button-font')
        visible = row.get_active()
        togglebutton.set_visible(visible)

        # Update plugin config
        self.plugin.set_config_key('icon_visible', visible)
