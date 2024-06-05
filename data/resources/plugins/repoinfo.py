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

from MiAZ.backend.log import MiAZLog


class MiAZRepositoryInfoPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZRepositoryInfoPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.RepoInfo')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.config = self.app.get_config_dict()
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
            menuitem = self.factory.create_menuitem('repoinfo', _('Repository properties'), self.actions.show_repository_settings, None, [])
            self.app.add_widget('workspace-menu-selection-section-app-repository-info', menuitem)
            section_app.append_item(menuitem)

