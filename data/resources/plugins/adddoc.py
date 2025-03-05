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
from MiAZ.frontend.desktop.services.dialogs import MiAZFileChooserDialog


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
            factory = self.app.get_service('factory')
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = factory.create_menuitem('add_docs', '... document(s)', self.import_file, None, [])
            self.app.add_widget('workspace-menu-in-add-document', menuitem)
            menu_add.append_item(menuitem)

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
            dialog.destroy()

        window = self.app.get_widget('window')
        clsdlg = MiAZFileChooserDialog(self.app)
        filechooser = clsdlg.create(
                        enable_response=True,
                        title=_('Import a single file'),
                        target = 'FILE',
                        callback = filechooser_response,
                        data=clsdlg)
        filechooser.present(window)

