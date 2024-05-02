#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import get_logger


class MiAZMenuRepo(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZMenuRepo'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.RepoSettings')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-menu", self.repo_settings_menu)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def repo_settings_menu(self, *args):
        # Add menutitem to menu for single items
        if self.app.get_widget('workspace-menu-repo-section-in-menuitem-settings') is None:
            section_common_in = self.app.get_widget('workspace-menu-repo-section-in')
            menuitem = self.factory.create_menuitem(name='repo_settings', label=_('Repository settings'), callback=self.show_repo_settings, data=None, shortcuts=[])
            self.app.add_widget('workspace-menu-repo-section-in-menuitem-settings', menuitem)
            section_common_in.append_item(menuitem)

            # ~ submenu_export_multi = self.app.get_widget('workspace-menu-selection-submenu-export')
            # ~ menuitem = self.factory.create_menuitem('export-to-csv', '...to CSV', self.export, None, [])
            # ~ self.app.add_widget('workspace-menu-multiple-menu-export-item-export2csv', menuitem)
            # ~ submenu_export_multi.append_item(menuitem)

    def show_repo_settings(self, *args):
        self.app.show_stack_page_by_name('settings_repo')
