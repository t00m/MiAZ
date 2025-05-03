#!/usr/bin/python3
# pylint: disable=E1101
# File: adddir.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Add a directory to repository

import os
import glob
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.status import MiAZStatus
from MiAZ.backend.pluginsystem import MiAZPlugin
from MiAZ.frontend.desktop.services.dialogs import MiAZFileChooserDialog


class MiAZAddDirectoryPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZAddDirectoryPlugin'
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

        # Connect signals to startup
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)


    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        # Create menu item for plugin
        menuitem = self.plugin.get_menu_item(callback=self.import_directory)

        # Add plugin to its default (sub)category
        self.plugin.install_menu_entry(menuitem)


    def import_directory(self, *args):
        factory = self.app.get_service('factory')
        srvutl = self.app.get_service('util')
        srvrepo = self.app.get_service('repo')

        def filechooser_response(dialog, response, clsdlg):
            if response == 'apply':
                filechooser = self.app.get_widget('plugin-adddir-filechooser')
                toggle = self.app.get_widget('plugin-adddir-togglebutton')
                recursive = toggle.get_active()
                gfile = filechooser.get_file()
                if gfile is not None:
                    self.app.set_status(MiAZStatus.BUSY)
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
                    self.app.set_status(MiAZStatus.RUNNING)

        window = self.app.get_widget('window')
        clsdlg = MiAZFileChooserDialog(self.app)
        filechooser_dialog = clsdlg.create(
                    title=_('Import a directory'),
                    target = 'FOLDER',
                    callback = filechooser_response)
        filechooser_widget = self.app.add_widget('plugin-adddir-filechooser', clsdlg.get_filechooser_widget())
        filechooser_dialog.get_style_context().add_class(class_name='toolbar')
        filechooser_widget.get_style_context().add_class(class_name='frame')
        filechooser = filechooser_dialog.get_extra_child()
        gtkbin = filechooser.get_parent()
        contents = gtkbin.get_parent()
        hbox = factory.create_box_horizontal()
        hbox.get_style_context().add_class(class_name='toolbar')
        label = Gtk.Label()
        title=_('<big><b>Walk recursively</b></big>')
        label.set_markup(title)
        toggle = factory.create_button_switch(callback=None)
        self.app.add_widget('plugin-adddir-togglebutton', toggle)
        hbox.append(toggle)
        hbox.append(label)
        contents.append(hbox)
        contents.get_style_context().add_class(class_name='toolbar')
        filechooser_dialog.present(window)
