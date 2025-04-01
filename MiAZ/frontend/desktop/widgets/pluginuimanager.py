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

    def refresh_available_plugin_list(self, *args):
        """Retrieve MiAZ plugin index file if:
            - Plugin index file doesn't exist
            - It is older than one day
        """
        download = False
        file = Path(ENV['FILE']['PLUGINS'])
        if not file.exists():
            download = True
            self.log.debug("Plugin index file doesn't exist")
        else:
            file_mod_time = datetime.fromtimestamp(file.stat().st_mtime)
            if datetime.now() - file_mod_time > timedelta(days=1):
                download = True
                self.log.debug(f"Plugin index file older than 1 day")

        if download:
            self.download_plugin_index()
            self.log.debug("Plugin index file downloaded")
        else:
            self.log.debug("Plugin index file is available and it is recent")

        items = []
        with open(ENV['FILE']['PLUGINS'], 'r') as fp:
            plugins = json.load(fp)
            for pid in plugins:
                name = plugins[pid]['Name']
                version = plugins[pid]['Version']
                description = plugins[pid]['Description']
                items.append((pid, description))
        view = self.app.get_widget('window-plugin-ui-manager-view')
        config = self.app.get_config('Plugin')
        config.add_available_batch(items)
        view.update_views()

    def download_plugin_index(self, *args):
        # FIXME: let user choose url?
        url = "https://raw.githubusercontent.com/t00m/MiAZ-Plugins/refs/heads/sandbox/index-plugins.json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            contents = response.json()
            with open(ENV['FILE']['PLUGINS'], 'w') as fp:
                json.dump(contents, fp)
            self.log.info(f"Plugin index downloaded and saved to {ENV['FILE']['PLUGINS']}")
        except Exception as err:
            # FIXME: raise error dialog
            self.log.error(f"An error occurred: {err}")
