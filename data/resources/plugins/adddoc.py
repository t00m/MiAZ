#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""


from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog

class MiAZAddDocumentPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDocumentPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.AddDocument')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-in-add-document') is None:
            actions = self.app.get_service('actions')
            factory = self.app.get_service('factory')
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = factory.create_menuitem('add_docs', '... document(s)', actions.import_file, None, [])
            self.app.add_widget('workspace-menu-in-add-document', menuitem)
            menu_add.append_item(menuitem)
