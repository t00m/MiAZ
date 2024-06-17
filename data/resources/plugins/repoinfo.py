#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: repoinfo.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for display/edit repository configuration
"""

from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZRepositoryInfoPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZRepositoryInfoPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.RepoInfo')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        if self.app.get_widget('workspace-menu-selection-section-app-repository-info') is None:
            section_app = self.app.get_widget('workspace-menu-selection-section-app')
            menuitem = factory.create_menuitem('repoinfo', _('Repository properties'), actions.show_repository_settings, None, [])
            self.app.add_widget('workspace-menu-selection-section-app-repository-info', menuitem)
            section_app.append_item(menuitem)
