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

from MiAZ.backend.models import File
from MiAZ.backend.pluginsystem import MiAZPlugin
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete


class MiAZDeleteItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZDeleteItemPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None
    file = __file__.replace('.py', '.plugin')

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self.file)

        ## Get logger
        self.log = self.plugin.get_logger()

        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        if not self.plugin.menu_item_loaded():
            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=self.document_delete)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

    def document_delete(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        workspace = self.app.get_widget('workspace')
        srvdlg = self.app.get_service('dialogs')

        def dialog_response(dialog, response, items):
            if response == 'apply':
                for item in items:
                    filepath = os.path.join(repository.docs, item.id)
                    util.filename_delete(filepath)

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
        dialog = srvdlg.create(dtype='question', title=_('Mass deletion'), body=body, widget=box, width=600, height=480)
        dialog.connect('response', dialog_response, items)
        dialog.present(window)
