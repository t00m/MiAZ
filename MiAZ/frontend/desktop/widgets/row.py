#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

class MiAZFlowBoxRow(Gtk.Frame):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZFlowBoxRow'

    def __init__(self, app, filepath: str, filedict: dict):
        super(MiAZFlowBoxRow, self).__init__()
        self.app = app
        self.filepath = filepath
        self.filedict = filedict
        self.factory = self.app.get_factory()
        self.workspace = self.app.get_workspace()

        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        boxCenter = Gtk.CenterBox()
        boxCenter.set_margin_top(margin=6)
        boxCenter.set_margin_end(margin=6)
        boxCenter.set_margin_bottom(margin=6)
        boxCenter.set_margin_start(margin=6)

        icon_mime = self.app.icman.get_icon_mimetype_from_file(filepath, 32)
        btnMime = Gtk.Button(css_classes=['flat'])
        btnMime.set_child(icon_mime)
        btnMime.set_valign(Gtk.Align.CENTER)
        btnMime.connect('clicked', self.workspace.on_display_document, filepath)
        icon_flag = self.app.icman.get_flag('ES', 32)
        boxLayout = Gtk.Box()
        boxLayout.set_hexpand(True)
        boxLayout.set_margin_start(6)
        boxLayout.set_margin_end(6)
        label = self.factory.create_label(os.path.basename(filepath))
        label.set_xalign(0.0)
        if filedict['valid']:
            boxLayout.append(label)
            boxCenter.set_end_widget(icon_flag)
        else:
            expander = Gtk.Expander()
            expander.set_label_widget(label)
            wdgReasons = self.__create_trvreasons()
            expander.set_child(wdgReasons)
            boxLayout.append(expander)
        boxCenter.set_start_widget(btnMime)
        boxCenter.set_center_widget(boxLayout)
        self.set_child(boxCenter)


    def __create_trvreasons(self):
        # ~ scrreasons = Gtk.ScrolledWindow()
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
        return trvreasons
        # ~ scrreasons.set_child(trvreasons)
        # ~ scrreasons.set_min_content_height(240)
        # ~ self.log.debug(height)
        # ~ scrreasons.set_vexpand(True)
        # ~ scrreasons.set_propagate_natural_height(True)

    def get_filepath(self):
        return self.filepath

    def get_filedict(self):
        return self.filedict
