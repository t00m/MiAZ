#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions

class MiAZExtensions(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZExtensions'

    def __init__(self, app):
        self.config = MiAZConfigSettingsExtensions()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)
        self.box_buttons.set_visible(False)

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: icon, type, extension
        self.store = Gtk.TreeStore(Pixbuf, str, str)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # Extension Type Icon
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn('Type', renderer, pixbuf=0)
        renderer.set_alignment(0.0, 0.5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        column.set_expand(False)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(1)
        column.set_sort_order(Gtk.SortType.ASCENDING)
        self.treeview.append_column(column)

        # Section
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Section', renderer, markup=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(1)
        self.treeview.append_column(column)

        # Extension
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Extension', renderer, markup=2)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(2)
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 1)
        self.sorted_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.treeview.set_model(self.sorted_model)

        # ~ self.treeview.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.treeview)
        return self.scrwin

    def update(self):
        extensions = self.config.load_global()
        sections = {}
        for ext in extensions:
            esections = extensions[ext]
            for section in esections:
                try:
                    parent = sections[section]
                except KeyError:
                    icon = self.app.icman.get_pixbuf_by_name('miaz-mime-%s' % section, 24)
                    parent = self.store.insert_with_values(None, -1, (0, 1,), (icon, section,))
                    sections[section] = parent
                self.store.insert_with_values(parent, -1, (2,), (ext,))

    def clb_visible_function(self, model, itr, data):
        item_name = model.get(itr, 2)[0]
        if item_name is None:
            return True
        if self.search_term is None:
            return True

        match = self.search_term.upper() in item_name.upper()
        if match:
            return True
        else:
            return False
