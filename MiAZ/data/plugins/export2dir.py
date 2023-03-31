#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import tempfile
from datetime import datetime

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

class Export2Dir(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZExport2DirPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.Export2Dir')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-menu", self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")
        API = self.object
        # ~ API.app.disconnect_by_func(self.processInputCb)

    def add_menuitem(self, *args):
        submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
        menuitem = self.factory.create_menuitem('export-to-dir', '...to directory', self.export, None, [])
        submenu_export.append_item(menuitem)

    def export(self, *args):
        items = self.workspace.get_selected_items()

        def get_pattern_paths(item):
            fields = self.util.get_fields(item.id)
            paths = {}
            paths['Y'] = '%04d' % datetime.strptime(fields[0], '%Y%m%d').year
            paths['m'] = "%02d" % datetime.strptime(fields[0], '%Y%m%d').month
            paths['d'] = "%02d" % datetime.strptime(fields[0], '%Y%m%d').day
            paths['C'] = fields[Field[Country]]
            paths['G'] = fields[Field[Group]]
            paths['P'] = fields[Field[Purpose]]
            paths['B'] = fields[Field[SentBy]]
            paths['T'] = fields[Field[SentTo]]
            return paths

        def filechooser_response(dialog, response, patterns):
            config = self.backend.repo_config()
            target_dir = config['dir_docs']
            if response == Gtk.ResponseType.ACCEPT:
                content_area = dialog.get_content_area()
                box = content_area.get_first_child()
                filechooser = box.get_first_child()
                hbox = box.get_last_child()
                toggle_pattern = hbox.get_first_child()
                gfile = filechooser.get_file()
                if gfile is not None:
                    dirpath = gfile.get_path()
                    if toggle_pattern.get_active():
                        entry = toggle_pattern.get_next_sibling()
                        keys = [key for key in entry.get_text()]
                        for item in items:
                            basename = os.path.basename(item.id)
                            thispath = []
                            thispath.append(dirpath)
                            paths = get_pattern_paths(item)
                            for key in keys:
                                thispath.append(paths[key])
                            target = os.path.join(*thispath)
                            os.makedirs(target, exist_ok = True)
                            self.util.filename_export(item.id, target)
                    else:
                        for item in items:
                            target = os.path.join(dirpath, os.path.basename(item.id))
                            self.util.filename_export(item.id, target)
                    self.util.directory_open(dirpath)
            dialog.destroy()

        patterns = {
            'Y': 'Year',
            'm': 'Month',
            'd': 'Day',
            'C': 'Country',
            'G': 'Group',
            'P': 'Purpose',
            'B': 'Sent by',
            'T': 'Sent to',
        }
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Export selected items to this directory',
                    target = 'FOLDER',
                    callback = filechooser_response,
                    data = patterns
                    )

        # Export with pattern
        contents = filechooser.get_content_area()
        box = contents.get_first_child()
        hbox = self.factory.create_box_horizontal()
        chkPattern = self.factory.create_button_check(title='Export with pattern', callback=None)
        etyPattern = Gtk.Entry()
        etyPattern.set_text('CYmGP') #/{target}/{Country}/{Year}/{month}/{Group}/{Purpose}
        widgets = []
        for key in patterns:
            label = Gtk.Label()
            label.set_markup('<b>%s</b> = %s' % (key, patterns[key]))
            label.set_xalign(0.0)
            widgets.append(label)
        btpPattern = self.factory.create_button_popover(icon_name='miaz-info', widgets=widgets)
        hbox.append(chkPattern)
        hbox.append(etyPattern)
        hbox.append(btpPattern)
        box.append(hbox)
        filechooser.show()