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
# ~ from MiAZ.backend.models import Plugin
# ~ from MiAZ.frontend.desktop.widgets.configview import MiAZUserPlugins
# ~ from MiAZ.frontend.desktop.widgets.window import MiAZCustomWindow
# ~ from MiAZ.backend.pluginsystem import MiAZPluginType


class MiAZPluginUIManager(Adw.PreferencesDialog):
    __gtype_name__ = 'MiAZPluginUIManager'
    pages = {}
    groups = {}

    def __init__(self, app, **kwargs):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.MiAZPluginUIManager')
        self.log.debug("UI Plugin Manager")
        self._build_ui()
        self.refresh_available_plugin_list()

    def _build_ui(self):
        factory = self.app.get_service('factory')
        self.set_title('Plugin management')
        self.set_search_enabled(True)
        # ~ page_title = _("Available plugins")
        # ~ page_icon = "io.github.t00m.MiAZ-res-plugins"
        # ~ self.page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        # ~ self.add(self.page)

        ## Group plugins
        # ~ self.group = Adw.PreferencesGroup()
        # ~ self.group.set_title('Plugins')
        # ~ self.page.add(self.group)

    def refresh_available_plugin_list(self, *args):
        """Retrieve MiAZ plugin index file if:
            - Plugin index file doesn't exist
            - It is older than one day
        """
        factory = self.app.get_service('factory')
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

        with open(ENV['FILE']['PLUGINS'], 'r') as fp:
            plugins = json.load(fp)
            for pid in plugins:
                name = plugins[pid]['Name']
                self.log.debug(f"Adding plugin {name}")
                version = plugins[pid]['Version']
                description = plugins[pid]['Description']
                category = plugins[pid]['Category']
                subcategory = plugins[pid]['Subcategory']
                row = Adw.SwitchRow(title=description) #, subtitle=description)
                group = self.get_group(category, subcategory)
                group.add(row)

    def get_group(self, category, subcategory):
        try:
            page = self.pages[category]
        except:
            page = Adw.PreferencesPage(title=category)
            self.add(page)
            self.pages[category] = page

        try:
            group = self.groups[page][subcategory]
        except:
            self.groups[page] = {}
            group = Adw.PreferencesGroup()
            group.set_title(subcategory)
            page.add(group)
            self.groups[page][subcategory] = group

        self.log.debug(f"{page} {group} {category} {subcategory}")
        return group


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
