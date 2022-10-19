#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

class MiAZFlowBoxRow(Gtk.Box):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZFlowBoxRow'

    def __init__(self, app, filepath: str, filedict: dict):
        super(MiAZFlowBoxRow, self).__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        self.set_hexpand(True)

        self.app = app
        self.filepath = filepath
        self.filedict = filedict
        self.factory = self.app.get_factory()
        self.workspace = self.app.get_workspace()

        boxRow = Gtk.CenterBox()
        boxRow.set_margin_top(margin=6)
        boxRow.set_margin_end(margin=6)
        boxRow.set_margin_bottom(margin=6)
        boxRow.set_margin_start(margin=6)
        boxRow.set_hexpand(True)

        boxStart = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        boxStart.get_style_context().add_class(class_name='frame')
        boxStart.set_hexpand(False)
        # ~ boxStart.set_homogeneous(True)
        icon_mime = self.app.icman.get_icon_mimetype_from_file(filepath, 32)
        btnMime = Gtk.Button()
        btnMime.get_style_context().add_class(class_name='flat')
        btnMime.set_child(icon_mime)
        btnMime.set_hexpand(False)
        # ~ btnMime.set_valign(Gtk.Align.CENTER)
        btnMime.connect('clicked', self.workspace.on_display_document, filepath)
        boxStart.append(btnMime)


        boxCenter = Gtk.Box()
        boxCenter.get_style_context().add_class(class_name='frame')
        boxCenter.set_hexpand(True)
        boxCenter.set_margin_start(6)
        boxCenter.set_margin_end(6)

        boxEnd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['frame'])
        boxEnd.set_hexpand(False)

        if filedict['valid']:
            basename = os.path.basename(filepath)
            dot = basename.rfind('.')
            doc = basename[:dot]
            ext = basename[dot+1:]
            who = self.app.get_config('organizations')
            fields = doc.split('-')
            btnCol = self.factory.create_button('', "<span color='blue'>%s</span>" % fields[2])
            btnCol.get_style_context().add_class(class_name='flat')
            btnCol.set_margin_end(6)
            # ~ btnCol.set_valign(Gtk.Align.CENTER)
            btnCol.set_hexpand(False)
            boxEnd.append(btnCol)
            explain = "<b>%s from %s about %s to %s</b>" % (fields[4].title(), who.get(fields[3]), fields[5], who.get(fields[6]))
            lblExplain = Gtk.Label()
            # ~ lblExplain.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            # ~ lblExplain.set_single_line_mode(False)
            lblExplain.set_margin_start(6)
            lblExplain.set_xalign(0.0)
            lblExplain.set_hexpand(True)
            lblExplain.set_markup(explain)
            boxCenter.append(lblExplain)
            self.date = fields[0]
            adate = datetime.strptime(self.date, "%Y%m%d")
            lblDate = self.factory.create_label(adate.strftime("%Y.%m.%d"))
            lblDate.set_margin_end(6)
            boxEnd.append(lblDate)
            icon_flag = self.app.icman.get_flag(fields[1], 32)
            boxEnd.append(icon_flag)
        else:
            btnFileInfo = Gtk.MenuButton()
            btnFileInfo.set_label(os.path.basename(filepath))
            btnFileInfo.get_style_context().add_class(class_name='flat')
            popover = self.__create_popover_fileinfo()
            btnFileInfo.set_popover(popover)
            btnFileInfo.set_valign(Gtk.Align.CENTER)
            btnFileInfo.set_hexpand(False)
            boxCenter.append(btnFileInfo)

            suggested = filedict['suggested'].split('-')
            self.date = suggested[0]
            adate = datetime.strptime(self.date, "%Y%m%d")
            lblDate = self.factory.create_label(adate.strftime("%Y.%m.%d"))
            lblDate.set_margin_end(6)
            boxEnd.append(lblDate)

            btnFileEdit = self.factory.create_button('miaz-edit', '', self.workspace.action_rename_manually, data=self.filepath)
            btnFileEdit.set_valign(Gtk.Align.CENTER)
            btnFileEdit.set_hexpand(False)
            boxEnd.append(btnFileEdit)

        boxRow.set_start_widget(boxStart)
        boxRow.set_center_widget(boxCenter)
        boxRow.set_end_widget(boxEnd)
        self.append(boxRow)

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
