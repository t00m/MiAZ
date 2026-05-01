#!/usr/bin/python3
# File: pluginuimangager.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin UI Manager

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Plugin
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin


class MiAZPluginUIManager(Gtk.Box):
    """Plugin Manager UI Widget"""
    __gtype_name__ = 'MiAZPluginUIManager'

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, hexpand=True, vexpand=True)
        self.app = app
        self.log = MiAZLog('MiAZPluginUIManager')
        self.factory = self.app.get_service('factory')
        self._build_ui()

    def _build_ui(self):
        box = self.factory.create_box_vertical(spacing=6, hexpand=True, vexpand=True)
        widget = self._create_view_plugins()
        box.append(widget)
        self.append(box)

    def _create_view_plugins(self):
        box = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=True)
        box.get_style_context().add_class(class_name='toolbar')
        frame_view = Gtk.Frame()
        viewbox = self._create_plugin_view()
        frame_view.set_child(viewbox)

        toolbar = self._create_plugin_view_toolbar()
        toolbar.get_style_context().add_class(class_name='linked')
        box.append(frame_view)
        box.append(toolbar)

        pm = self.app.get_service('plugin-system')
        view = self.app.get_widget('app-settings-plugins-view')
        items = []
        item_type = Plugin
        for plugin in pm.plugins:
            pid = plugin.get_name()
            title = plugin.get_description()
            items.append(item_type(id=pid, title=_(title)))
        view.update(items)

        return box

    def _on_plugin_selected(self, selection_model, position, n_items):
        btnConfig = self.app.get_widget('plugin-view-button-config')
        selected_plugin = selection_model.get_selected_item()
        plugin_id = f"plugin-{selected_plugin.id}"
        plugin = self.app.get_widget(plugin_id)
        has_settings = False
        if plugin is not None:
            has_settings = hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings'))
        btnConfig.set_visible(has_settings)

    def _create_plugin_view(self):
        scrwin = self.factory.create_scrolledwindow()
        self.app.add_widget('app-settings-plugins-scrwin', scrwin)
        view = MiAZColumnViewPlugin(self.app)
        view.set_hexpand(True)
        view.set_vexpand(True)
        self.app.add_widget('app-settings-plugins-view', view)
        scrwin.set_child(view)
        return scrwin

    def _create_plugin_view_toolbar(self):
        toolbar = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=False, vexpand=False)
        btnInfo = self.factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', callback=self._show_plugin_info, css_classes=[''])
        btnInfo.set_valign(Gtk.Align.CENTER)
        toolbar.append(btnInfo)
        btnConfig = self.factory.create_button(icon_name='io.github.t00m.MiAZ-config-symbolic', callback=self._configure_plugin_options, css_classes=[''])
        self.app.add_widget('plugin-view-button-config', btnConfig)
        btnConfig.set_valign(Gtk.Align.CENTER)
        toolbar.append(btnConfig)
        return toolbar

    def _show_plugin_info(self, *args):
        plugin_system = self.app.get_service('plugin-system')
        view = self.app.get_widget('app-settings-plugins-view')
        selected_plugin = view.get_selected()
        if selected_plugin is None:
            return

        # If no repository is loaded, plugins aren't loaded either
        plugin_module = self.app.get_widget(f'plugin-{selected_plugin.id}')
        if plugin_module is None:
            return

        # Build info dialog
        plugin_info = plugin_module.plugin.get_plugin_info_dict()
        dialog = Adw.PreferencesDialog()
        dialog.set_title('Plugin info')
        page_title = _('Properties')
        page_icon = "io.github.t00m.MiAZ-dialog-information-symbolic"
        page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        dialog.add(page)
        group = Adw.PreferencesGroup()
        group.set_title('Data Sheet')
        page.add(group)

        # Add plugin info as key/value rows
        for key in plugin_info:
            lblkey = _(key)
            row = Adw.ActionRow(title=f'<b>{lblkey}</b>')
            label = Gtk.Label.new(_(plugin_info[key]))
            row.add_suffix(label)
            group.add(row)
        dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)
        dialog.present(view.get_root())

    def _configure_plugin_options(self, *args):
        view = self.app.get_widget('app-settings-plugins-view')
        selected_plugin = view.get_selected()
        if selected_plugin is None:
            return
        plugin = self.app.get_widget(f'plugin-{selected_plugin.id}')
        if plugin is not None:
            if hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings')):
                try:
                    plugin.show_settings(self)
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.info(f"Plugin {selected_plugin.id} doesn't have a settings dialog")

