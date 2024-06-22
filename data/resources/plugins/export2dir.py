#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2dir.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to a given directory
"""

import os
from datetime import datetime
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


class Export2Dir(GObject.GObject, Peas.Activatable):
    """Export selected documents to a directory"""

    __gtype_name__ = 'MiAZExport2DirPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.Export2Dir')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        print("do_deactivate")

    def add_menuitem(self, *args):
        if self.app.get_widget('workspace-menu-multiple-menu-export-item-export2dir') is None:
            factory = self.app.get_service('factory')
            submenu_export = self.app.get_widget('workspace-menu-selection-submenu-export')
            menuitem = factory.create_menuitem('export-to-dir', _('...to directory'), self.export, None, [])
            submenu_export.append_item(menuitem)
            self.app.add_widget('workspace-menu-multiple-menu-export-item-export2dir', menuitem)

    def export(self, *args):
        factory = self.app.get_service('factory')
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items()

        def get_pattern_paths(item):
            fields = util.get_fields(item.id)
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
                            thispath = []
                            thispath.append(dirpath)
                            try:
                                paths = get_pattern_paths(item)
                                for key in keys:
                                    thispath.append(paths[key])
                                target = os.path.join(*thispath)
                                os.makedirs(target, exist_ok=True)
                                source = os.path.join(repository.docs, item.id)
                                util.filename_export(source, target)
                            except ValueError as error:
                                self.log.error(f"{os.path.basename(source)} couldn't be exported.")
                                self.log.error("Reason: filename not compliant with MiAZ format")
                    else:
                        for item in items:
                            source = os.path.join(repository.docs, item.id)
                            target = os.path.join(dirpath, os.path.basename(item.id))
                            util.filename_export(source, target)
                    util.directory_open(dirpath)
            dialog.destroy()

        patterns = {
            'Y': _('Year'),
            'm': _('Month'),
            'd': _('Day'),
            'C': _('Country'),
            'G': _('Group'),
            'P': _('Purpose'),
            'B': _('Sent by'),
            'T': _('Sent to'),
        }
        window = self.app.get_widget('window')
        filechooser = factory.create_filechooser(
                    parent=window,
                    title=_('Export selected items to this directory'),
                    target='FOLDER',
                    callback=filechooser_response,
                    data=patterns
                    )

        # Export with pattern
        contents = filechooser.get_content_area()
        box = contents.get_first_child()
        hbox = factory.create_box_horizontal()
        chkPattern = factory.create_button_check(title=_('Export with pattern'), callback=None)
        etyPattern = Gtk.Entry()
        etyPattern.set_text('CYmGP')  # /{target}/{Country}/{Year}/{month}/{Group}/{Purpose}
        widgets = []
        for key in patterns:
            label = Gtk.Label()
            label.set_markup(f'<b>{key}</b> = {patterns[key]}')
            label.set_xalign(0.0)
            widgets.append(label)
        btpPattern = factory.create_button_popover(icon_name='com.github.t00m.MiAZ-dialog-information-symbolic', widgets=widgets)
        hbox.append(chkPattern)
        hbox.append(etyPattern)
        hbox.append(btpPattern)
        box.append(hbox)
        filechooser.show()
