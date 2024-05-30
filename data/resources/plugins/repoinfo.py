#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: delete.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for deleting items
"""

import os
import tempfile
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings


class MiAZRepositoryInfoPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZRepositoryInfoPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.RepoInfo')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.config = self.backend.get_config()
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_menuitem)


    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-selection-section-app-repository-info') is None:
            section_app = self.app.get_widget('workspace-menu-selection-section-app')
            menuitem = self.factory.create_menuitem('repoinfo', _('Repository properties'), self.repository_info, None, [])
            self.app.add_widget('workspace-menu-selection-section-app-repository-info', menuitem)
            section_app.append_item(menuitem)

    def repository_info(self, *args):
        window_main = self.app.get_widget('window')
        window_settings = self.app.get_widget('settings-repo')
        if window_settings is None:
            window_settings = self.app.add_widget('settings-repo', MiAZRepoSettings(self.app))
        window_settings.set_transient_for(window_main)
        window_settings.set_modal(True)
        window_settings.present()
