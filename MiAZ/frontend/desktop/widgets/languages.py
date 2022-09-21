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


class MiAZLanguages(MiAZConfigView):
    """Class for managing Languages from Settings"""
    __gtype_name__ = 'MiAZLanguages'
    current = None

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.box_oper.set_visible(False)

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: flag icon, code, name, checkbox
        self.store = Gtk.ListStore(str, str, bool)
        self.tree = MiAZTreeView(self.app)
        self.tree.set_model(self.store)

        # Code
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Language Code', renderer, text=0)
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(0)
        self.tree.append_column(column)

        # Language name
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn('Country', renderer, text=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(1)
        self.tree.append_column(column)

        # Checkbox
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.__clb_row_toggled)
        column = Gtk.TreeViewColumn('Default?', renderer, active=2)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        column.set_expand(False)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(2)
        column.set_property('spacing', 50)
        self.tree.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        # ~ self.treefilter.set_visible_func(self.__clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)

        self.tree.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.tree)
        return self.scrwin

    def double_click(self, treeview, treepath, treecolumn):
        model = self.sorted_model.get_model()
        model[treepath][2] = not model[treepath][2]
        self.save_config()

    def check_config_file(self):
        if not os.path.exists(self.local_config):
            self.save_config()
            self.log.debug("Local config file for %s created empty" % self.config_for)

    def update(self):
        try:
            with open(self.global_config, 'r') as fin:
                languages = json.load(fin)
        except FileNotFoundError as error:
            self.log.error(error)
            return

        try:
            checked = self.load_config()
        except FileNotFoundError:
            checked = []

        n = 0
        for code in languages:
            name = "%s (%s)" % (languages[code], code)
            self.store.insert_with_values(n, (0, 1, 2), (code, name, code in checked))
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
