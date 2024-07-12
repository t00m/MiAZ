#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2zip.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to ZIP
"""

import os
import shutil
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Country, Date, Group
from MiAZ.backend.models import Purpose, SentBy, SentTo

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
        self.log = MiAZLog('Plugin.Export2Zip')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        # ~ API.app.disconnect_by_func(self.processInputCb)

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-multiple-menu-export-item-export2zip') is None:
            factory = self.app.get_service('factory')
            submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
            menuitem = factory.create_menuitem('export-to-zip', _('...to Zip'), self.export, None, [])
            submenu_export.append_item(menuitem)
            self.app.add_widget('workspace-menu-multiple-menu-export-item-export2zip', menuitem)

    def export(self, *args):
        ENV = self.app.get_env()
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items()
        if actions.stop_if_no_items(items):
            return

        def filechooser_response(dialog, response, patterns):

            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                gfile = filechooser.get_file()
                dirpath = gfile.get_path()
                if gfile is not None:
                    dir_zip = util.get_temp_dir()
                    util.directory_create(dir_zip)
                    for item in items:
                        source = os.path.join(repository.docs, item.id)
                        target = dir_zip
                        util.filename_copy(source, target)
                    basename = os.path.basename(dir_zip)
                    zip_file = f"{basename}.zip"
                    zip_target = os.path.join(ENV['LPATH']['TMP'], zip_file)
                    source = zip_target
                    target = os.path.join(dirpath, zip_file)
                    util.zip(target, dir_zip)
                    util.filename_rename(source, target)
                    shutil.rmtree(dir_zip)
                    util.directory_open(dirpath)
                    self.log.debug(target)
            dialog.destroy()

        window = self.app.get_widget('window')
        filechooser = factory.create_filechooser(
                    parent=window,
                    title=_('Export selected documents to a ZIP file'),
                    target='FOLDER',
                    callback=filechooser_response,
                    data=None
                    )

        # Export with pattern
        filechooser.show()
