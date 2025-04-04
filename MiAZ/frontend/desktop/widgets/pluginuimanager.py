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


class MiAZPluginUIRow:
    def __init__(self, app):
        self.app = app

    def new(self, title: str = '', subtitle: str = ''):
        factory = self.app.get_service('factory')
        self._title = title
        self._subtitle = subtitle
        self.row = Adw.ActionRow(title=title, subtitle=subtitle)
        widget = factory.create_box_horizontal(spacing=6)
        separator = Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL)
        btnInfo = factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic')
        btnInfo.set_valign(Gtk.Align.CENTER)
        btnInfo.set_has_frame(False)
        widget.append(separator)
        widget.append(btnInfo)
        self.row.add_suffix(widget)
        return self.row

class MiAZPluginUIManager(Adw.PreferencesDialog):
    __gtype_name__ = 'MiAZPluginUIManager'
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
        page_title = _("Available plugins")
        page_icon = "io.github.t00m.MiAZ-res-plugins"
        self.page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        self.add(self.page)

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
        self.groups = {}
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
                row = MiAZPluginUIRow(self.app).new(title=description)
                group = self.get_group(category)
                group.add(row)
        for group_title, group_node in sorted(self.groups.items(), key=lambda item: item[0]):
            self.page.add(group_node)


    def get_group(self, category):
        try:
            group = self.groups[category]
        except KeyError:
            group = Adw.PreferencesGroup(title=category)
            self.groups[category] = group
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
