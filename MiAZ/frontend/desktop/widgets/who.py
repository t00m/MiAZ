#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView


class MiAZWho(MiAZConfigView):
    """Class for managing Languages from Settings"""
    __gtype_name__ = 'MiAZWho'
    current = None

    def __init__(self, app):
        super().__init__(app)
        self.app = app

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: flag icon, code, name, checkbox
        self.store = Gtk.ListStore(str, str)
        self.tree = MiAZTreeView(self.app)
        self.tree.set_model(self.store)

        # Initials
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Initials', renderer, text=0)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(0)
        self.tree.append_column(column)

        # Full name
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn('Full name', renderer, text=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(1)
        self.tree.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        # ~ self.treefilter.set_visible_func(self.__clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)

        self.tree.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.tree)
        return self.scrwin

    def selection_changed(self, selection):
        if selection is None:
            return
        try:
            model, treeiter = selection.get_selected()
            code = model[treeiter][0]
            name = model[treeiter][0]
            tbuf = self.entry.get_buffer()
            tbuf.set_text("%s, %s" % (code, name), -1)
            # ~ self.current = name.upper()
        except Exception as error:
            pass

    def double_click(self, treeview, treepath, treecolumn):
        model = self.sorted_model.get_model()
        model[treepath][2] = not model[treepath][2]
        self.save_config()

    def update(self):
        if self.local_config is None:
            return

        # Check config file and create it if doesn't exist
        self.check_config_file()

        self.store.clear()
        items = self.load_config()

        n = 0
        for code in items:
            fullname = items[code]
            self.store.insert_with_values(n, (0, 1), (code, fullname))
            n += 1

    def save_config(self):
        items = []
        def row(model, path, itr):
            code = model.get(itr, 0)[0]
            checked = model.get(itr, 2)[0]
            if checked:
                items.append(code)
        self.store.foreach(row)
        with open(self.local_config, 'w') as fj:
            json.dump(sorted(items), fj)

    def __clb_row_toggled(self, cell, path):
        model = self.sorted_model.get_model()
        rpath = self.sorted_model.convert_path_to_child_path(Gtk.TreePath(path))
        model[rpath][2] = not model[rpath][2]
        self.save_config()
