#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.pluginsystem import MiAZPlugin
from MiAZ.frontend.desktop.services.dialogs import MiAZFileChooserDialog


class MiAZAddDocumentPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDocumentPlugin'
    object = GObject.Property(type=GObject.Object)
    plugin = None
    name = 'AddDocs'     # Plugin internal name
    desc = '... document(s)'   # Plugin menuitem entry
    file = __file__.replace('.py', '.plugin')

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self.file, self)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Connect signals to startup
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        if not self.plugin.menu_item_loaded():
            # Create menu item for plugin
            menuitem = self.plugin.get_menu_item(callback=self.import_file)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

    def import_file(self, *args):
        factory = self.app.get_service('factory')
        srvutl = self.app.get_service('util')
        srvrepo = self.app.get_service('repo')

        def filechooser_response(dialog, response, clsdlg):
            if response == 'apply':
                filechooser = clsdlg.get_filechooser_widget()
                gfile = filechooser.get_file()
                if gfile is not None:
                    source = gfile.get_path()
                    btarget = srvutl.filename_normalize(source)
                    target = os.path.join(srvrepo.docs, btarget)
                    srvutl.filename_import(source, target)

        window = self.app.get_widget('window')
        clsdlg = MiAZFileChooserDialog(self.app)
        filechooser = clsdlg.create(
                        title=_('Import a single file'),
                        target = 'FILE',
                        callback = filechooser_response,
                        data=clsdlg)
        filechooser.present(window)

