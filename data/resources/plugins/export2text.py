#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2text.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items filenames to plain text
"""

import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class Export2Text(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2TextPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.Export2Text')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        self.app.disconnect_by_func(self.add_menuitem)

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-multiple-menu-export-item-export2text') is None:
            factory = self.app.get_service('factory')
            submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
            menuitem = factory.create_menuitem('export-to-text', _('...to plain text'), self.export, None, [])
            submenu_export.append_item(menuitem)
            self.app.add_widget('workspace-menu-multiple-menu-export-item-export2text', menuitem)

    def export(self, *args):
        actions = self.app.get_service('actions')
        srvdlg = self.app.get_service('dialogs')
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        workspace = self.app.get_widget('workspace')
        window = workspace.get_root()
        items = workspace.get_selected_items()
        if actions.stop_if_no_items(items):
            return

        text = ""
        for item in items:
            text += f"{item.id}\n"
        fp, filepath = tempfile.mkstemp(dir=ENV['LPATH']['TMP'], suffix='.txt')
        with open(filepath, 'w') as temp:
            temp.write(text)
        temp.close()
        util.filename_display(filepath)
        body = '<big>Your should see your default editor listing the document names</big>'
        srvdlg.create(parent=window, dtype='info', title=_('Export successfull'), body=body).present()
