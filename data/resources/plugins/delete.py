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
from MiAZ.backend.models import File
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete


class MiAZDeleteItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZDeleteItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.DeleteItem')

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
        if self.app.get_widget('workspace-menu-selection-section-danger-menuitem-delete') is None:
            section_danger = self.app.get_widget('workspace-menu-selection-section-danger')
            menuitem = self.factory.create_menuitem('delete', _('Delete documents'), self.document_delete, None, [])
            self.app.add_widget('workspace-menu-selection-section-danger-menuitem-delete', menuitem)
            section_danger.append_item(menuitem)

    def document_delete(self, *args):
        def dialog_response(dialog, response, items):
            if response == Gtk.ResponseType.ACCEPT:
                for item in items:
                    filepath = os.path.join(self.repository.docs, item.id)
                    self.util.filename_delete(filepath)
            dialog.destroy()

        self.log.debug("Mass deletion")
        items = self.workspace.get_selected_items()
        frame = Gtk.Frame()
        box, view = self.factory.create_view(MiAZColumnViewMassDelete, _("Mass deletion"))
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, _('Mass deletion'), box, width=1024, height=600)
        dialog.connect('response', dialog_response, items)
        dialog.show()
