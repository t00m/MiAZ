#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: scripts.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects

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
        self.app = None

    def do_activate(self):
        self.app = self.object.app

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

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
