#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: scripts.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import tempfile
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File
from MiAZ.backend.models import Project
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPeople
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Project'] = MiAZProjects
Configview['Date'] = Gtk.Calendar


class MiAZScriptsPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZScriptsPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.Scripts')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        # Plugin deactivated temporary
        # ~ self.workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        section_common_in = self.app.get_widget('workspace-menu-selection-section-common-in')
        if self.app.get_widget('workspace-menu-selection-menu-scripts') is None:
            submenu_scripts = Gio.Menu.new()
            menu_scripts = Gio.MenuItem.new_submenu(
                label = _('Scripts'),
                submenu = submenu_scripts,
            )
            section_common_in.append_item(menu_scripts)
            self.app.add_widget('workspace-menu-selection-menu-scripts', menu_scripts)
            self.app.add_widget('workspace-menu-selection-submenu-scripts', submenu_scripts)
            # ~ menuitem = self.factory.create_menuitem('project-assign', _('...assign project'), self.actions.noop, None, [])
            # ~ submenu_scripts.append_item(menuitem)
            # ~ menuitem = self.factory.create_menuitem('project-withdraw', _('...withdraw project'), self.actions.noop, None, [])
            # ~ submenu_project.append_item(menuitem)

