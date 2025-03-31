import os
import json
import base64
import requests
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GObject

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Plugin
# ~ from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.widgets.configview import MiAZUserPlugins
from MiAZ.frontend.desktop.widgets.window import MiAZCustomWindow
from MiAZ.backend.pluginsystem import MiAZPluginType


class MiAZPluginUIManager(MiAZCustomWindow):
    __gtype_name__ = 'MiAZPluginUIManager'

    def __init__(self, app, **kwargs):
        self.app = app
        self.log = MiAZLog('MiAZ.MiAZPluginUIManager')
        self.name = 'plugin-ui-manager'
        self.title = f"Plugin Manager"
        super().__init__(app, self.name, self.title, **kwargs)


    def _build_ui(self):
        factory = self.app.get_service('factory')
        self.set_default_size(800, 600)
        vbox = self.factory.create_box_vertical(margin=0, spacing=6, hexpand=True, vexpand=True)

        # Toolbar
        toolbar = Gtk.ActionBar()
        vbox.append(toolbar)

        # Toolbar refresh button
        button = factory.create_button(icon_name='io.github.t00m.MiAZ-view-refresh-symbolic', tooltip='Refresh plugin list', callback=self.refresh_available_plugin_list)
        toolbar.pack_start(button)

        scrwin = self.factory.create_scrolledwindow()
        self.app.add_widget('window-plugin-ui-manager-scrwin', scrwin)
        vbox.append(scrwin)
        pm = self.app.get_service('plugin-manager')
        view = self.app.add_widget('window-plugin-ui-manager-view', MiAZUserPlugins(self.app))
        view.set_hexpand(True)
        view.set_vexpand(True)
        scrwin.set_child(view)
        self.mainbox.append(vbox)

        # System Plugins
        # ~ items = []
        # ~ item_type = Plugin
        # ~ for plugin in pm.plugins:
            # ~ if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                # ~ pid = plugin.get_module_name()
                # ~ title = plugin.get_description()
                # ~ items.append(item_type(id=pid, title=title))
        # ~ view.update(items)

        # ~ return vbox

    def refresh_available_plugin_list(self, *args):
        """Retrieve MiAZ plugin index file"""
        # ~ owner = "t00m"
        # ~ repo = "MiAZ-Plugins"
        # ~ file_name = "index-plugins.json"
        # ~ branch = "sandbox"  # Specify your branch here
        # TOKEN_PLUGINS_REPO_READ_ONLY
        # ~ token_encoded = "Z2l0aHViX3BhdF8xMUFBQzZNWlEwT0NNM210bm1LV3JYX016NzdyYkVKekFxUkQ4M1ozdlF4T3FhQ1lBc29hMm9HeW5LeTlrWTZ4WUdRTlBXUkFJNHpiVUVxZzQz"
        # ~ token = base64.b64decode(token_encoded.encode('utf-8')).decode('utf-8')
        # ~ self.log.debug(token)
        # ~ headers = {'Authorization': f'token {token}'} if token else {}
        # ~ base_url = f'https://api.github.com/repos/{owner}/{repo}/contents/'
        # ~ params = {'ref': branch}  # This parameter specifies the branch
        url = "https://raw.githubusercontent.com/t00m/MiAZ-Plugins/refs/heads/sandbox/index-plugins.json"

        try:
            response = requests.get(url)
            response.raise_for_status()
            contents = response.json()
            index_plugins = os.path.join(ENV['LPATH']['CACHE'], "index-plugins.json")
            with open(index_plugins, 'w') as fp:
                json.dump(contents, fp)
            self.log.info(f"Plugin index saved to {index_plugins}")
        # ~ except HTTPError as http_err:
            # ~ print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            self.log.error(f"An error occurred: {err}")






    # ~ def _create_widget_for_plugins(self):
        # ~ vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        # ~ notebook = Gtk.Notebook()
        # ~ notebook.set_show_border(False)
        # ~ notebook.set_tab_pos(Gtk.PositionType.LEFT)
        # ~ widget = self._create_view_plugins_system()
        # ~ label = self.factory.create_notebook_label(icon_name='io.github.t00m.MiAZ-res-plugins-system', title='System')
        # ~ notebook.append_page(widget, label)
        # ~ widget = self._create_view_plugins_user()
        # ~ label = self.factory.create_notebook_label(icon_name='io.github.t00m.MiAZ-res-plugins', title='User')
        # ~ notebook.append_page(widget, label)
        # ~ vbox.append(notebook)
        # ~ return vbox

    # ~ def _create_view_plugins_system(self):
        # ~ vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        # ~ scrwin = self.factory.create_scrolledwindow()
        # ~ self.app.add_widget('app-settings-plugins-system-scrwin', scrwin)
        # ~ vbox.append(scrwin)
        # ~ pm = self.app.get_service('plugin-manager')
        # ~ view = MiAZColumnViewPlugin(self.app)
        # ~ view.set_hexpand(True)
        # ~ view.set_vexpand(True)
        # ~ self.app.add_widget('app-settings-plugins-system-view', view)
        # ~ scrwin.set_child(view)

        # ~ # System Plugins
        # ~ items = []
        # ~ item_type = Plugin
        # ~ for plugin in pm.plugins:
            # ~ if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                # ~ pid = plugin.get_module_name()
                # ~ title = plugin.get_description()
                # ~ items.append(item_type(id=pid, title=title))
        # ~ view.update(items)
        # ~ return vbox

    # ~ def _create_view_plugins_user(self):
        # ~ vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)

        # ~ # Add/Remove
        # ~ hbox = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=False)
        # ~ hbox.get_style_context().add_class(class_name='toolbar')
        # ~ hbox.append(self.factory.create_button(icon_name='io.github.t00m.MiAZ-list-add-symbolic', title='Add plugin', callback=self._on_plugin_add))
        # ~ hbox.append(self.factory.create_button(icon_name='io.github.t00m.MiAZ-list-remove-symbolic', title='Remove plugin', callback=self._on_plugin_remove))
        # ~ vbox.append(hbox)

        # ~ # User Plugins
        # ~ scrwin = self.factory.create_scrolledwindow()
        # ~ self.app.add_widget('app-settings-plugins-user-scrwin', scrwin)
        # ~ vbox.append(scrwin)
        # ~ view = MiAZColumnViewPlugin(self.app)
        # ~ view.set_hexpand(True)
        # ~ view.set_vexpand(True)
        # ~ self.app.add_widget('app-settings-plugins-user-view', view)
        # ~ scrwin.set_child(view)
        # ~ self.update_user_plugins()
        # ~ return vbox
