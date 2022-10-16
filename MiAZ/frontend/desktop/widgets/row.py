#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
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

        boxStart = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
        icon_mime = self.app.icman.get_icon_mimetype_from_file(filepath, 32)
        btnMime = Gtk.Button(css_classes=['flat'])
        btnMime.set_child(icon_mime)
        btnMime.set_valign(Gtk.Align.CENTER)
        btnMime.connect('clicked', self.workspace.on_display_document, filepath)
        boxStart.append(btnMime)


        boxCenter = Gtk.Box()
        boxCenter.set_hexpand(True)
        boxCenter.set_margin_start(6)
        boxCenter.set_margin_end(6)

        boxEnd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])

        if filedict['valid']:
            wdgCenter = Gtk.Label()
            boxCenter.append(wdgCenter)
            icon_flag = self.app.icman.get_flag('ES', 32)
            boxEnd.append(icon_flag)
        else:
            btnFileInfo = Gtk.MenuButton()
            btnFileInfo.set_label(os.path.basename(filepath))
            btnFileInfo.get_style_context().add_class(class_name='flat')
            # ~ btnFileInfo.set_icon_name('miaz-reasons-info')
            popover = self.__create_popover_fileinfo()
            btnFileInfo.set_popover(popover)
            btnFileInfo.set_valign(Gtk.Align.CENTER)
            btnFileInfo.set_hexpand(False)
            boxCenter.append(btnFileInfo)
            # ~ boxEnd.append()

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
