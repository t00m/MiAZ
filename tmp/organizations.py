#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.backend.config import MiAZConfigSettingsOrganizations

class MiAZOrganizations(MiAZConfigView):
    """Class for managing Organizations from Settings"""
    __gtype_name__ = 'MiAZOrganizations'

    def __init__(self, app):
        self.config = MiAZConfigSettingsOrganizations()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: flag icon, code, name, checkbox
        self.store = Gtk.ListStore(str, str)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # Initials
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Initials', renderer, text=0)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(0)
        self.treeview.append_column(column)

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
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 1)
        self.sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
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

    def selection_changed(self, selection):
        if selection is None:
            return
        try:
            model, treeiter = selection.get_selected()
            code = model[treeiter][0]
            name = model[treeiter][0]
            tbuf = self.entry.get_buffer()
            tbuf.set_text("%s, %s" % (code, name), -1)
        except Exception as error:
            pass

    def double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        key = self.sorted_model[treeiter][0]
        value = self.sorted_model[treeiter][1]
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Modify person or entity', 'Initials', 'Full name')
        dialog.set_value1(key.upper())
        dialog.set_value2(value)
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def update(self):
        self.store.clear()
        items = self.config.load()
        for code in items:
            fullname = items[code]
            self.store.insert_with_values(-1, (0, 1), (code, fullname))

    def on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new person or entity', 'Initials', 'Full name')
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                items = self.config.load()
                items[key.upper()] = value
                self.config.save(items)
                self.update()
                # ~ self.emit('updated')
        dialog.destroy()
