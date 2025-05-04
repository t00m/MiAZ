import os
import json
import base64
import pprint
import requests
from pathlib import Path
from datetime import datetime, timedelta
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GObject

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Plugin
from MiAZ.backend.pluginsystem import MiAZPluginType
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
        title = "These system plugins are always enabled for any repository"
        title += "\n\n<small>Check your repository preferences to manage user plugins</small>"
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
        frame = Gtk.Frame()
        viewbox = self._create_plugin_view(MiAZPluginType.SYSTEM)
        frame.set_child(viewbox)
        toolbar = self._create_plugin_view_toolbar(MiAZPluginType.SYSTEM)
        box.append(frame)
        box.append(toolbar)

        pm = self.app.get_service('plugin-system')
        view = self.app.get_widget('app-settings-plugins-system-view')
        items = []
        item_type = Plugin
        for plugin in pm.plugins:
            if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                pid = plugin.get_module_name()
                title = plugin.get_description()
                items.append(item_type(id=pid, title=title))
        view.update(items)
        return box

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
        toolbar = self.factory.create_box_vertical(margin=0, spacing=6, hexpand=False, vexpand=False)
        btnInfo = self.factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic')
        btnInfo.set_valign(Gtk.Align.CENTER)
        btnInfo.set_has_frame(False)
        toolbar.append(btnInfo)
        btnConfig = self.factory.create_button(icon_name='io.github.t00m.MiAZ-config-symbolic', callback=self._configure_plugin_options, css_classes=['flat'])
        btnConfig.set_valign(Gtk.Align.CENTER)
        btnConfig.set_has_frame(False)
        toolbar.append(btnConfig)
        return toolbar

    def _configure_plugin_options(self, *args):
        view = self.app.get_widget(f'app-settings-plugins-{MiAZPluginType.SYSTEM}-view')
        selected_plugin = view.get_selected()
        if selected_plugin is None:
            return
        self.log.info(f"{selected_plugin.id}: {selected_plugin.title}")
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        plugin_system = self.app.get_service('plugin-system')
        user_plugins = util.json_load(ENV['APP']['PLUGINS']['LOCAL_INDEX'])
        module = user_plugins[selected_plugin.id]['Module']
        plugin = self.app.get_widget(f'plugin-{module}')
        if plugin is not None:
            if hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings')):
                try:
                    plugin.show_settings()
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.info(f"Plugin {selected_plugin.id} doesn't have a settings dialog")

    # ~ def update_user_plugins(self):
        # ~ ENV = self.app.get_env()
        # ~ plugin_system = self.app.get_service('plugin-system')
        # ~ plugin_system.rescan_plugins()
        # ~ view = self.app.get_widget('app-settings-plugins-user-view')
        # ~ items = []
        # ~ item_type = Plugin
        # ~ for plugin in plugin_system.plugins:
            # ~ ptype = plugin_system.get_plugin_type(plugin)
            # ~ if ptype == MiAZPluginType.USER:
                # ~ base_dir = plugin.get_name()
                # ~ module_name = plugin.get_module_name()
                # ~ plugin_path = os.path.join(ENV['LPATH']['PLUGINS'], base_dir, f"{module_name}.plugin")
                # ~ if os.path.exists(plugin_path):
                    # ~ title = plugin.get_description()
                    # ~ items.append(item_type(id=module_name, title=title))
        # ~ view.update(items)

    # ~ def on_filechooser_response(self, dialog, response, clsdlg):
        # ~ if response == 'apply':
            # ~ plugin_system = self.app.get_service('plugin-system')
            # ~ filechooser = clsdlg.get_filechooser_widget()
            # ~ gfile = filechooser.get_file()
            # ~ if gfile is None:
                    # ~ self.log.debug('No directory set. Do nothing.')
                    # ~ # FIXME: Show warning message. Priority: low
                    # ~ return
            # ~ plugin_path = gfile.get_path()
            # ~ imported = plugin_system.import_plugin(plugin_path)
            # ~ self.log.debug(f"Plugin imported? {imported}")
            # ~ if imported:
                # ~ self.update_user_plugins()

    # ~ def _on_plugin_add(self, *args):
        # ~ plugin_filter = Gtk.FileFilter()
        # ~ plugin_filter.add_pattern('*.zip')
        # ~ window = self.app.get_widget('window-app-settings')
        # ~ clsdlg = MiAZFileChooserDialog(self.app)
        # ~ filechooser_dialog = clsdlg.create(
                        # ~ parent=window,
                        # ~ title=_('Import a single file'),
                        # ~ target = 'FILE',
                        # ~ callback = self.on_filechooser_response,
                        # ~ data=clsdlg)
        # ~ filechooser_widget = clsdlg.get_filechooser_widget()
        # ~ filechooser_widget.set_filter(plugin_filter)
        # ~ filechooser_dialog.present()

    # ~ def _on_plugin_remove(self, *args):
        # ~ plugin_system = self.app.get_service('plugin-system')
        # ~ view = self.app.get_widget('app-settings-plugins-user-view')
        # ~ try:
            # ~ module = view.get_selected()
            # ~ plugin = plugin_system.get_plugin_info(module.id)
            # ~ deleted = plugin_system.remove_plugin(plugin)
            # ~ if deleted:
                # ~ self.log.debug(f"Plugin '{module.id}' deleted")
                # ~ self.update_user_plugins()
        # ~ except IndexError as error:
            # ~ self.log.debug("No user plugins installed and/or selected")
            # ~ raise

    # ~ def get_plugin_status(self, name: str) -> bool:
        # ~ plugins = self.config['App'].get('plugins')
        # ~ if plugins is None:
            # ~ return False

        # ~ if name in plugins:
            # ~ return True
        # ~ return False

    # ~ def set_plugin_status(self, checkbox, plugin_name):
        # ~ active = checkbox.get_active()
        # ~ plugins = self.config['App'].get('plugins')
        # ~ if plugins is None:
            # ~ plugins = []
        # ~ if active:
            # ~ if plugin_name not in plugins:
                # ~ plugins.append(plugin_name)
        # ~ else:
            # ~ plugins.remove(plugin_name)
        # ~ self.config['App'].set('plugins', plugins)

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
            util.json_save(ENV['APP']['PLUGINS']['LOCAL_INDEX'], plugin_index)
            plugin_system = self.app.get_service('plugin-system')
            user_plugins = plugin_system.get_user_plugins()
            plugin_list = []
            for pid in plugin_index:
                desc = plugin_index[pid]['Description']
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
