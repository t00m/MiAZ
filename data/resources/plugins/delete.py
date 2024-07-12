#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: delete.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for deleting items
"""

import os
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
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-selection-section-danger-menuitem-delete') is None:
            factory = self.app.get_service('factory')
            section_danger = self.app.get_widget('workspace-menu-selection-section-danger')
            menuitem = factory.create_menuitem('delete', _('Delete documents'), self.document_delete, None, [])
            self.app.add_widget('workspace-menu-selection-section-danger-menuitem-delete', menuitem)
            section_danger.append_item(menuitem)

    def document_delete(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        workspace = self.app.get_widget('workspace')
        srvdlg = self.app.get_service('dialogs')

        def dialog_response(dialog, response, items):
            if response == Gtk.ResponseType.ACCEPT or response == Gtk.ResponseType.YES:
                for item in items:
                    filepath = os.path.join(repository.docs, item.id)
                    util.filename_delete(filepath)
            dialog.destroy()

        items = workspace.get_selected_items()
        if actions.stop_if_no_items(items):
            return

        frame = Gtk.Frame()
        box, view = factory.create_view(MiAZColumnViewMassDelete)
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        box.append(frame)
        window = self.app.get_widget('window')
        body = _("<big>These documents are going to be deleted.\n<b>Are you sure?</b></big>")
        dialog = srvdlg.create(parent=window, dtype='question', title=_('Mass deletion'), body=body, widget=box, width=600, height=480)
        dialog.connect('response', dialog_response, items)
        dialog.present()
