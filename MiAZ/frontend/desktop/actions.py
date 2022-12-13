#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
import shutil

from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog

class MiAZActions(GObject.GObject):
    def __init__(self, app):
        self.log = get_logger('MiAZActions')
        self.app = app
        # ~ self.workspace = self.app.get_workspace()
        self.backend = self.app.get_backend()

    def add_directory_to_repo(self, dialog, response):
        target = self.backend.get_repo_target()
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            if gfile is not None:
                dirpath = gfile.get_path()
                files = glob.glob(os.path.join(dirpath, '*.*'))
                for filepath in files:
                    shutil.copy(filepath, target)
                    self.log.debug("Copied '%s' to target: %s",
                                        os.path.basename(filepath),
                                        target)
        dialog.destroy()

    def add_file_to_repo(self, dialog, response):
        target = self.backend.get_repo_target()
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            if gfile is not None:
                filepath = gfile.get_path()
                shutil.copy(filepath, target)
                self.log.debug("Copied '%s' to target: %s",
                                        os.path.basename(filepath),
                                        target)
        dialog.destroy()

    def document_display(self, filepath):
        os.system("xdg-open '%s'" % filepath)

    def document_rename(self, item):
        repodct = self.backend.get_repo_dict()
        source = item.id
        if repodct[source]['valid']:
            basename = os.path.basename(source)
            filename = basename[:basename.rfind('.')]
            target = filename.split('-')
        else:
            target = repodct[source]['suggested'].split('-')
        dialog = MiAZRenameDialog(self.app, source, target)
        dialog.show()

    def dropdown_populate(self, dropdown, item_type, keyfilter = False, intkeys=[], any_value=True):
        # Populate the model
        model = dropdown.get_model()
        config = self.app.get_config(item_type.__gtype_name__)
        items = config.load()
        config_is = config.get_config_is()

        # foreign key is used when the local configuration is saved as a
        # list, but it gets the name from global dictionary (eg.: Countries)
        foreign = config.get_config_foreign()
        if foreign:
            gitems = config.load_global()

        items = config.load()
        if isinstance(items, list):
            items = sorted(items)

        model.remove_all()

        if any_value:
            model.append(item_type(id='Any', title='Any'))

        for key in items:
            if config_is is dict:
                if foreign:
                    if keyfilter:
                        if key in intkeys:
                            model.append(item_type(id=key, title="%s (%s)" % (gitems[key], key)))
                    else:
                        model.append(item_type(id=key, title="%s (%s)" % (gitems[key], key)))
                else:
                    if keyfilter:
                        if key in intkeys:
                            model.append(item_type(id=key, title="%s (%s)" % (items[key], key)))
                    else:
                        if keyfilter:
                            if key in intkeys:
                                model.append(item_type(id=key, title="%s (%s)" % (items[key], key)))
                        else:
                            model.append(item_type(id=key, title="%s (%s)" % (items[key], key)))
            else:
                if keyfilter:
                    if key in intkeys:
                        model.append(item_type(id=key, title=key))
                else:
                    model.append(item_type(id=key, title=key))

