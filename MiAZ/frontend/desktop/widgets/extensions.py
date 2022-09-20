#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView


class MiAZExtensions(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZExtensions'
    current = None

    def __init__(self, app):
        super().__init__(app)

    def setup_treeview(self):
        # Treeview for displaying
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.scrwin.set_has_frame(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.TreeStore(str, str)
        self.treeview.set_model(self.store)
        self.selection = self.treeview.get_selection()
        self.sig_selection_changed = self.selection.connect('changed', self.selection_changed)

        # Column: Name
        self.renderer = Gtk.CellRendererText()
        self.column = Gtk.TreeViewColumn('Name', self.renderer, text=0)
        self.column.set_visible(True)
        self.column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.column.set_expand(False)
        self.column.set_clickable(False)
        self.column.set_sort_indicator(True)
        self.column.set_sort_column_id(0)
        self.treeview.append_column(self.column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.__clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.sort_function, None)
        self.scrwin.set_child(self.treeview)

        return self.scrwin

