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
        self.box_buttons.set_visible(False)

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: flag icon, code, name, checkbox
        self.store = Gtk.ListStore(str, str, bool)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # Code
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Language Code', renderer, text=0)
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(0)
        self.treeview.append_column(column)

        # Language name
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn('Language', renderer, text=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(1)
        self.treeview.append_column(column)

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
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 2)
        self.sorted_model.set_sort_column_id(2, Gtk.SortType.DESCENDING)
        self.treeview.set_model(self.sorted_model)

        self.treeview.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.treeview)
        return self.scrwin

    def clb_visible_function(self, model, itr, data):
        item_code = model.get(itr, 0)[0]
        item_name = model.get(itr, 1)[0]
        item = item_code+item_name
        if item_code is None and item_name is None:
            self.log.debug("RETURN!!!")
            return True
        if self.search_term is None:
            self.log.debug("RETURN!!!")
            return True

        match = self.search_term.upper() in item.upper()
        if match:
            return True
        else:
            return False

    def double_click(self, treeview, treepath, treecolumn):
        model = self.sorted_model.get_model()
        model[treepath][2] = not model[treepath][2]
        self.config_save()

    def config_check(self):
        if not os.path.exists(self.config_local):
            self.config_save()
            self.log.debug("Local config file for %s created empty" % self.config_for)

    def update(self):
        try:
            with open(self.config_global, 'r') as fin:
                languages = json.load(fin)
        except FileNotFoundError as error:
            self.log.error(error)
            return

        try:
            checked = self.config_load()
        except FileNotFoundError:
            checked = []

        n = 0
        for code in languages:
            name = "%s (%s)" % (languages[code], code)
            self.store.insert_with_values(n, (0, 1, 2), (code, name, code in checked))
            n += 1

    def config_save(self):
        items = []
        def row(model, path, itr):
            code = model.get(itr, 0)[0]
            checked = model.get(itr, 2)[0]
            if checked:
                items.append(code)
        self.store.foreach(row)
        with open(self.config_local, 'w') as fj:
            json.dump(sorted(items), fj)

    def __clb_row_toggled(self, cell, path):
        model = self.sorted_model.get_model()
        rpath = self.sorted_model.convert_path_to_child_path(Gtk.TreePath(path))
        model[rpath][2] = not model[rpath][2]
        self.config_save()
