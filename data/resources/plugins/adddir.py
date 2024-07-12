#!/usr/bin/python3
# pylint: disable=E1101
# File: adddir.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Add a directory to repository

import os
import glob

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.services.dialogs import MiAZFileChooserDialog


class MiAZAddDirectoryPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDirectoryPlugin'
    object = GObject.Property(type=GObject.Object)
    enabled = False

    def __init__(self):
        self.log = MiAZLog('Plugin.AddDirectory')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-in-add-directory') is None:
            factory = self.app.get_service('factory')
            menu_add = self.app.get_widget('workspace-menu-in-add')
            menuitem = factory.create_menuitem('add_dir', '... from a directory', self.import_directory, None, [])
            self.app.add_widget('workspace-menu-in-add-directory', menuitem)
            menu_add.append_item(menuitem)

    def import_directory(self, *args):
        factory = self.app.get_service('factory')
        srvutl = self.app.get_service('util')
        srvrepo = self.app.get_service('repo')

        def filechooser_response(dialog, response, clsdlg):
            if response in [Gtk.ResponseType.ACCEPT, Gtk.ResponseType.OK]:
                content_area = dialog.get_content_area()
                filechooser = clsdlg.get_filechooser_widget()
                toggle = content_area.get_last_child()
                recursive = toggle.get_active()
                gfile = filechooser.get_file()
                if gfile is not None:
                    dirpath = gfile.get_path()
                    self.log.debug(f"Walk directory {dirpath} recursively? {recursive}")
                    if recursive:
                        files = srvutl.get_files_recursively(dirpath)
                    else:
                        files = glob.glob(os.path.join(dirpath, '*.*'))
                    for source in files:
                        btarget = srvutl.filename_normalize(source)
                        target = os.path.join(srvrepo.docs, btarget)
                        srvutl.filename_import(source, target)
            dialog.destroy()

        window = self.app.get_widget('window')
        clsdlg = MiAZFileChooserDialog(self.app)
        filechooser = clsdlg.create(
                    parent=window,
                    title=_('Import a directory'),
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = clsdlg)
        contents = filechooser.get_content_area()
        toggle = factory.create_button_check(title=_('Walk recursively'), callback=None)
        contents.append(toggle)
        filechooser.present()
