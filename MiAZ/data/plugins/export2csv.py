# -*- coding: utf-8 -*-
# cfoch-peas
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import subprocess

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import get_logger


class Export2CSV(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2CSVPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Export2CSV')

    def do_activate(self):
        API = self.object
        # ~ self.log.debug("do_activate: %s (%s)" % (self.object, type(API)))
        self.app = API.app
        self.workspace = API.app.get_workspace()
        self.log.debug(self.workspace)
        self.workspace.connect("start-workspace-completed", self.hola)
        self.workspace.connect("extend-menu-export", self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        API = self.object
        # ~ API.app.disconnect_by_func(self.processInputCb)

    def hola(self, *args):
        self.log.debug("Hola")

    def add_menuitem(self, *args):
        self.log.debug(args)
        # ~ self.log.debug("Adding menu item to menu export for exporting to CSV")
        # ~ menuitem = self.factory.create_menuitem('export-to-csv', '...to CSV', self._on_handle_menu_multiple, None, [])
        # ~ submenu_export.append_item(menuitem)

    def processInputCb(self, app, text):
        print("process: %s" % app)
        print("process: %s" % text)

    def startCb(self, app):
        print("start")

    def finishCb(self, app):
        print("finish")

    def speak(self, text):
        print("speak")

