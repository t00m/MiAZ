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
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPluginType
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
        title = _("These system plugins are always enabled for any repository")
        title += _("\n\n<small>Check your repository preferences to manage user plugins</small>")
        banner = Adw.Banner.new(title)
        banner.set_use_markup(True)
        banner.set_revealed(True)
        widget = self._create_view_plugins_system()
        box.append(banner)
        box.append(widget)
        self.append(box)

    def _create_view_plugins_system(self):
        box = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=True)
        box.get_style_context().add_class(class_name='toolbar')
        frame_view = Gtk.Frame()
        viewbox = self._create_plugin_view(MiAZPluginType.SYSTEM)
        frame_view.set_child(viewbox)

        # ~ frame_toolbar = Gtk.Frame()
        toolbar = self._create_plugin_view_toolbar(MiAZPluginType.SYSTEM)
        toolbar.get_style_context().add_class(class_name='linked')
        # ~ frame_toolbar.set_child(toolbar)
        box.append(frame_view)
        box.append(toolbar)

        pm = self.app.get_service('plugin-system')
        view_type = MiAZPluginType.SYSTEM
        view = self.app.get_widget(f'app-settings-plugins-{view_type}-view')
        items = []
        item_type = Plugin
        for plugin in pm.plugins:
            if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                pid = plugin.get_name()
                title = plugin.get_description()
                items.append(item_type(id=pid, title=_(title)))
        view.update(items)

        # Action to be done when selecting an used plugin
        # ~ selection_model = self.viewSl.cv.get_model()
        # ~ selection_model.connect('selection-changed', self._on_plugin_system_selected)

        return box

    def _on_plugin_system_selected(self, selection_model, position, n_items):
        btnConfig = self.app.get_widget('plugin-view-system-button-config')
        selected_plugin = selection_model.get_selected_item()
        plugin_id = f"plugin-{selected_plugin.id}"
        plugin = self.app.get_widget(plugin_id)
        has_settings = False
        if plugin is not None:
            has_settings = hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings'))
        btnConfig.set_visible(has_settings)

    def _create_plugin_view(self, plugin_view: MiAZPluginType = MiAZPluginType.SYSTEM):
        scrwin = self.factory.create_scrolledwindow()
        view_type = str(plugin_view)
        self.app.add_widget(f'app-settings-plugins-{view_type}-scrwin', scrwin)
        view = MiAZColumnViewPlugin(self.app)
        view.set_hexpand(True)
        view.set_vexpand(True)
        self.app.add_widget(f'app-settings-plugins-{view_type}-view', view)
        scrwin.set_child(view)
        return scrwin

    def _create_plugin_view_toolbar(self, plugin_view: MiAZPluginType = MiAZPluginType.SYSTEM):
        toolbar = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=False, vexpand=False)
        btnInfo = self.factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', callback=self._show_plugin_info, css_classes=[''])
        btnInfo.set_valign(Gtk.Align.CENTER)
        toolbar.append(btnInfo)
        btnConfig = self.factory.create_button(icon_name='io.github.t00m.MiAZ-config-symbolic', callback=self._configure_plugin_options, css_classes=[''])
        self.app.add_widget('plugin-view-system-button-config', btnConfig)
        btnConfig.set_valign(Gtk.Align.CENTER)
        toolbar.append(btnConfig)
        return toolbar

    def _show_plugin_info(self, *args):
        plugin_system = self.app.get_service('plugin-system')
        view = self.app.get_widget(f'app-settings-plugins-{MiAZPluginType.SYSTEM}-view')
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
        view = self.app.get_widget(f'app-settings-plugins-{MiAZPluginType.SYSTEM}-view')
        selected_plugin = view.get_selected()
        if selected_plugin is None:
            return
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        plugin_system = self.app.get_service('plugin-system')
        system_plugins = util.json_load(ENV['APP']['PLUGINS']['SYSTEM_INDEX'])
        module = system_plugins[selected_plugin.id]['Module']
        plugin = self.app.get_widget(f'plugin-{selected_plugin.id}')
        if plugin is not None:
            if hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings')):
                try:
                    plugin.show_settings(self)
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.info(f"Plugin {selected_plugin.id} doesn't have a settings dialog")

    def _refresh_index_plugin_file(self, *args):
        ENV = self.app.get_env()
        source = ENV['APP']['PLUGINS']['SOURCE']
        url_base = ENV['APP']['PLUGINS']['REMOTE_INDEX']
        url = url_base % source
        url_plugin_base = ENV['APP']['PLUGINS']['DOWNLOAD']
        user_plugins_dir = ENV['LPATH']['PLUGINS']
        try:
            util = self.app.get_service('util')
            response = requests.get(url)
            response.raise_for_status()
            plugin_index = response.json()
            util.json_save(ENV['APP']['PLUGINS']['USER_INDEX'], plugin_index)
            plugin_system = self.app.get_service('plugin-system')
            user_plugins = plugin_system.get_user_plugins()
            plugin_list = []
            for pid in plugin_index:
                desc = _(plugin_index[pid]['Description'])
                url_plugin = url_plugin_base % (source, pid)
                self.log.info(url_plugin)
                added = util.download_and_unzip(url_plugin, user_plugins_dir)
                if added:
                    plugin_list.append((pid, desc))
            # Recreate index plugin again (useful for devel purposes)
            plugin_system.create_plugin_index()

            self.update_user_plugins()

        except HTTPError as http_error:
            self.log.error(f"HTTP error occurred: {http_error}")
        except Exception as error:
            self.log.error(f"An error occurred: {error}")
