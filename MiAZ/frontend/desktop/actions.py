#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob

from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog

class MiAZActions(GObject.GObject):
    def __init__(self, app):
        self.log = get_logger('MiAZActions')
        self.app = app
        self.backend = self.app.get_backend()
        self.util = self.backend.util

    def add_directory_to_repo(self, dialog, response):
        config = self.backend.repo_config()
        target_dir = config['dir_docs']
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            if gfile is not None:
                dirpath = gfile.get_path()
                files = glob.glob(os.path.join(dirpath, '*.*'))
                for source in files:
                    target = self.util.filename_normalize(source)
                    self.util.filename_copy(source, target)
        dialog.destroy()

    def add_file_to_repo(self, dialog, response):
        config = self.backend.repo_config()
        target_dir = config['dir_docs']
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            if gfile is not None:
                source = gfile.get_path()
                target = self.util.filename_normalize(source)
                self.util.filename_copy(source, target)
        dialog.destroy()

    def document_display(self, doc):
        self.log.debug("Displaying %s", doc)
        self.util.filename_display(doc)

    def document_rename(self, item):
        config = self.backend.repo_config()
        repodct = config['dct_repo']
        source = item.id
        basename = os.path.basename(source)
        filename = basename[:basename.rfind('.')]
        target = filename.split('-')
        rename = self.app.get_rename_widget()
        rename.set_data(source, target)
        self.app.show_stack_page_by_name('rename')

    def dropdown_populate(self, dropdown, item_type, keyfilter = False, intkeys=[], any_value=True, none_value=False):
        model = dropdown.get_model()
        config = self.app.get_config(item_type.__gtype_name__)
        items = config.load(config.used)
        title = item_type.__gtype_name__

        items = config.load(config.used)

        model.remove_all()

        if any_value:
            model.append(item_type(id='Any', title='Any'))

        if none_value:
            model.append(item_type(id='None', title='None'))

        for key in items:
            title = items[key]
            if len(title) == 0:
                title = key
            model.append(item_type(id=key, title=title))

