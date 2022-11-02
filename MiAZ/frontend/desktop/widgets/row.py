#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

class MiAZListViewRow(Gtk.Box):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZListViewRow'

    def __init__(self, app):
        super(MiAZListViewRow, self).__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        self.set_hexpand(True)
        self.app = app
        self.factory = self.app.get_factory()
        self.workspace = self.app.get_workspace()
        self.actions = self.app.get_actions()

        boxRow = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        boxRow.set_hexpand(True)

        boxStart = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        boxStart.set_hexpand(False)
        icon_mime = Gtk.Image()
        icon_mime.set_pixel_size(36)
        btnMime = Gtk.Button()
        btnMime.get_style_context().add_class(class_name='flat')
        btnMime.set_child(icon_mime)
        btnMime.set_hexpand(False)
        btnMime.connect('clicked', self.actions.document_display)
        boxStart.append(btnMime)

        icon_edit = Gtk.Image()
        icon_edit.set_pixel_size(32)
        btnEdit = Gtk.Button()
        btnEdit.get_style_context().add_class(class_name='flat')
        btnEdit.set_child(icon_edit)
        btnEdit.set_hexpand(False)
        btnEdit.connect('clicked', self.actions.document_rename)
        boxStart.append(btnEdit)

        boxCenter = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        boxCenter.set_hexpand(True)
        label = self.factory.create_label()
        boxCenter.append(label)

        boxEnd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) #, css_classes=['frame'])
        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect('state-set', self.actions.document_switch)
        boxEnd.append(switch)
        boxEnd.set_hexpand(False)

        boxRow.append(boxStart)
        boxRow.append(boxCenter)
        boxRow.append(boxEnd)
        self.append(boxRow)

# ~ class MiAZFlowBoxRow(Gtk.Box):
    # ~ """ MiAZ Doc Browser Widget"""
    # ~ __gtype_name__ = 'MiAZFlowBoxRow'

    # ~ def __init__(self):
        # ~ super(MiAZFlowBoxRow, self).__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
        # ~ self.set_margin_top(margin=3)
        # ~ self.set_margin_end(margin=3)
        # ~ self.set_margin_bottom(margin=3)
        # ~ self.set_margin_start(margin=3)
        # ~ self.set_hexpand(True)
        # ~ icon = Gtk.Image()
        # ~ label = Gtk.Label()
        # ~ self.append(icon)
        # ~ self.append(label)

# ~ class MiAZFlowBoxRowOld(Gtk.Box):
    # ~ """ MiAZ Doc Browser Widget"""
    # ~ __gtype_name__ = 'MiAZFlowBoxRowOld'

    # ~ def __init__(self, app, filepath: str, filedict: dict):
        # ~ super(MiAZFlowBoxRow, self).__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
        # ~ self.set_margin_top(margin=3)
        # ~ self.set_margin_end(margin=3)
        # ~ self.set_margin_bottom(margin=3)
        # ~ self.set_margin_start(margin=3)
        # ~ self.set_hexpand(True)

        # ~ self.app = app
        # ~ self.filepath = filepath
        # ~ self.filedict = filedict
        # ~ self.factory = self.app.get_factory()
        # ~ self.workspace = self.app.get_workspace()

        # ~ boxRow = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        # ~ boxRow.set_hexpand(True)

        # ~ boxStart = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # ~ boxStart.set_hexpand(False)
        # ~ icon_mime = self.app.icman.get_icon_mimetype_from_file(filepath, 32)
        # ~ btnMime = Gtk.Button()
        # ~ btnMime.get_style_context().add_class(class_name='flat')
        # ~ btnMime.set_child(icon_mime)
        # ~ btnMime.set_hexpand(False)
        # ~ btnMime.connect('clicked', self.workspace.on_display_document, filepath)
        # ~ boxStart.append(btnMime)


        # ~ boxCenter = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # ~ boxCenter.set_hexpand(True)

        # ~ boxEnd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) #, css_classes=['frame'])
        # ~ boxEnd.set_hexpand(False)

        # ~ if filedict['valid']:
            # ~ btnFileEdit = self.factory.create_button('miaz-edit', '', self.workspace.action_rename_manually, data=self)
            # ~ btnFileEdit.get_style_context().add_class(class_name='flat')
            # ~ btnFileEdit.set_valign(Gtk.Align.CENTER)
            # ~ btnFileEdit.set_hexpand(False)
            # ~ btnFileEdit.set_margin_end(6)
            # ~ boxStart.append(btnFileEdit)

            # ~ basename = os.path.basename(filepath)
            # ~ dot = basename.rfind('.')
            # ~ doc = basename[:dot]
            # ~ ext = basename[dot+1:]
            # ~ who = self.app.get_config('organizations')
            # ~ fields = doc.split('-')
            # ~ btnCol = self.factory.create_button('', "<span color='blue'>%s</span>" % fields[2])
            # ~ btnCol.get_style_context().add_class(class_name='flat')
            # ~ btnCol.set_margin_end(6)
            # ~ btnCol.set_hexpand(False)
            # ~ boxEnd.append(btnCol)
            # ~ who_from = who.get(fields[3])
            # ~ if who_from is not None:
                # ~ if len(who_from) == 0:
                    # ~ who_from = fields[3]
            # ~ who_to = who.get(fields[6])
            # ~ if who_to is not None:
                # ~ if len(who_from) == 0:
                    # ~ who_to = fields[6]
            # ~ self.explain = "%s from %s about %s to %s" % (fields[4].title(), who_from, fields[5], who_to)
            # ~ lblExplain = self.factory.create_label(self.explain)
            # ~ lblExplain.set_margin_start(6)
            # ~ lblExplain.set_xalign(0.0)
            # ~ lblExplain.set_hexpand(True)
            # ~ boxCenter.append(lblExplain)
            # ~ self.date = fields[0]
            # ~ adate = datetime.strptime(self.date, "%Y%m%d")
            # ~ lblDate = self.factory.create_label(adate.strftime("%Y.%m.%d"))
            # ~ lblDate.set_margin_end(6)
            # ~ boxEnd.append(lblDate)
            # ~ icon_flag = self.app.icman.get_flag(fields[1], 32)
            # ~ boxEnd.append(icon_flag)
        # ~ else:
            # ~ self.explain = ''
            # ~ btnFileInfo = Gtk.MenuButton()
            # ~ lblFileInfo = self.factory.create_label(os.path.basename(filepath))
            # ~ btnFileInfo.set_child(lblFileInfo)
            # ~ btnFileInfo.get_style_context().add_class(class_name='flat')
            # ~ popover = self.__create_popover_fileinfo()
            # ~ btnFileInfo.set_popover(popover)
            # ~ btnFileInfo.set_valign(Gtk.Align.CENTER)
            # ~ btnFileInfo.set_hexpand(False)
            # ~ boxCenter.append(btnFileInfo)

            # ~ suggested = filedict['suggested'].split('-')
            # ~ self.date = suggested[0]
            # ~ try:
                # ~ adate = datetime.strptime(self.date, "%Y%m%d")
            # ~ except:
                # ~ print(self.filepath)
                # ~ raise
            # ~ lblDate = self.factory.create_label(adate.strftime("%Y.%m.%d"))
            # ~ lblDate.set_margin_end(6)
            # ~ boxEnd.append(lblDate)

            # ~ btnFileEdit = self.factory.create_button('miaz-edit', '', self.workspace.action_rename_manually, data=self)
            # ~ btnFileEdit.set_valign(Gtk.Align.CENTER)
            # ~ btnFileEdit.set_hexpand(False)
            # ~ btnFileEdit.set_margin_end(6)

            # ~ btnFileSelect = self.factory.create_switch_button('', '')
            # ~ btnFileSelect.set_valign(Gtk.Align.CENTER)
            # ~ btnFileSelect.set_hexpand(False)

            # ~ boxEnd.append(btnFileEdit)
            # ~ boxEnd.append(btnFileSelect)

        # ~ boxRow.append(boxStart)
        # ~ boxRow.append(boxCenter)
        # ~ boxRow.append(boxEnd)
        # ~ self.append(boxRow)

    def __create_popover_fileinfo(self):
        trvreasons = Gtk.TreeView()
        trvreasons.set_vexpand(True)
        trvreasons.set_hexpand(False)
        trvreasons.set_headers_visible(False)
        model = Gtk.ListStore(Pixbuf, str)

        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn('Type', renderer, pixbuf=0)
        renderer.set_alignment(0.0, 0.5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        trvreasons.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Reason', renderer, text=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        trvreasons.append_column(column)
        icon_ko = self.app.icman.get_pixbuf_by_name('miaz-ko', 32)
        icon_ok = self.app.icman.get_pixbuf_by_name('miaz-ok', 32)

        for reason in self.filedict['reasons']:
            passed, message = reason
            if passed:
                model.insert_with_values(-1, (0, 1), (icon_ok, message))
            else:
                model.insert_with_values(-1, (0, 1), (icon_ko, message))
        trvreasons.set_model(model)

        popover = Gtk.Popover()
        popover.set_child(trvreasons)

        return popover

    def get_filepath(self):
        return self.filepath

    def get_filedict(self):
        return self.filedict

    def get_date(self):
        return self.date

    def get_explain(self):
        return self.explain
