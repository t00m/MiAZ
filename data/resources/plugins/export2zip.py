#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import shutil
import tempfile
from datetime import datetime
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Concept, Country, Date, Group
from MiAZ.backend.models import Person, Purpose, SentBy, SentTo

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6

class Export2Zip(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2ZipPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Export2Zip')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        API = self.object
        # ~ API.app.disconnect_by_func(self.processInputCb)

    def add_menuitem(self, *args):
        submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
        menuitem = self.factory.create_menuitem('export-to-zip', _('...to Zip'), self.export, None, [])
        submenu_export.append_item(menuitem)

    def export(self, *args):
        ENV = self.app.get_env()
        items = self.workspace.get_selected_items()

        def filechooser_response(dialog, response, patterns):
            target_dir = self.repository.get('dir_docs')
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                hbox = box.get_last_child()
                toggle_pattern = hbox.get_first_child()
                gfile = filechooser.get_file()
                dirpath = gfile.get_path()
                if gfile is not None:
                    dir_doc = self.repository.get('dir_docs')
                    dir_zip = self.util.get_temp_dir()
                    self.util.directory_create(dir_zip)
                    for item in items:
                        source = os.path.join(dir_doc, item.id)
                        target = dir_zip
                        self.util.filename_copy(source, target)
                    zip_file = "%s.zip" % os.path.basename(dir_zip)
                    zip_target = os.path.join(ENV['LPATH']['TMP'], zip_file)
                    repo_dir = self.repository.get('dir_docs')
                    source = zip_target
                    target = os.path.join(dirpath, zip_file)
                    self.util.zip(target, dir_zip)
                    self.util.filename_rename(source, target)
                    shutil.rmtree(dir_zip)
                    self.util.directory_open(dirpath)
                    self.log.debug(target)
            dialog.destroy()

        self.factory = self.app.get_service('factory')
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title=_('Export selected documents to a ZIP file'),
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = None
                    )

        # Export with pattern
        filechooser.show()
