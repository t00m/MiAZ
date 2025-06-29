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
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete

plugin_info = {
        'Module':        'delete',
        'Name':          'MiAZDeleteDoc',
        'Loader':        'Python3',
        'Description':   _('Delete selected documents'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      _('Data Management'),
        'Subcategory':   _('Deletion')
    }


class MiAZDeleteItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZDeleteItemPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

        ## Connect signals
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Delete selected documents'), callback=self.document_delete)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def document_delete(self, *args):
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items(items):
            return

        frame = Gtk.Frame()
        box, view = self.factory.create_view(MiAZColumnViewMassDelete)
        citems = []
        for item in items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        view.update(citems)
        frame.set_child(view)
        box.append(frame)
        window = self.app.get_widget('window')
        body = _("<b>Are you sure?</b>\n\nThe following documents will be deleted:")
        dialog = self.srvdlg.show_question(title=_('Mass deletion'), body=body, widget=box, width=600, height=480)
        dialog.connect('response', self._on_document_delete_response, items)
        dialog.present(window)

    def _on_document_delete_response(self, dialog, response, items):
        parent = self.app.get_widget('window')
        if response == 'apply':
            filepaths = set()
            for item in items:
                filepath = os.path.join(self.repository.docs, item.id)
                filepaths.add(filepath)
            self.util.filename_delete(filepaths)
            title = _('Repository management')
            body = _('{num_docs} documents deleted from repository').format(num_docs=len(items))
            self.srvdlg.show_warning(title=title, body=body, parent=parent)
        else:
            title = _('Repository management')
            body = _('Action canceled by user')
            self.srvdlg.show_warning(title=title, body=body, parent=parent)
