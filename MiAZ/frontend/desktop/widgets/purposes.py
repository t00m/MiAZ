#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod
import json

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.widgets.widget import MiAZWidget
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView

class MiAZPurposes(MiAZWidget, Gtk.Box):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'
    current = None

    def __init__(self, app):
        super().__init__(app, __class__.__name__)
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_start(margin=12)

        # Entry and buttons for purposes operations (edit/add/remove)
        box_oper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.rename)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        box_entry.append(self.entry)
        box_oper.append(box_entry)
        box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_buttons.append(self.app.create_button('miaz-edit', '', self.rename))
        box_buttons.append(Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL))
        box_buttons.append(self.app.create_button('miaz-add', '', self.add))
        box_buttons.append(self.app.create_button('miaz-remove', '', self.remove))
        box_oper.append(box_buttons)
        self.append(box_oper)

        # Treeview for displaying
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.scrwin.set_has_frame(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.TreeStore(str)
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
        self.append(self.scrwin)

        # Check config file and create it if doesn't exist
        self.check_config_file()

        # Update view
        self.update()

    def sort_function(self, model, row1, row2, user_data):
        sort_column = 0
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    def selection_changed(self, selection):
        if selection is None:
            return
        try:
            model, treeiter = selection.get_selected()
            if model is None or treeiter is None:
                return
            name = model[treeiter][0]
            tbuf = self.entry.get_buffer()
            tbuf.set_text(name, -1)
            self.current = name.upper()
        except Exception as error:
            self.log.error(error)

    def edit_name(self, widget, path, target):
        treeiter = self.sorted_model.get_iter(path)
        name = self.sorted_model[treeiter][0]
        print(name)
        print(target)

    def __row_inserted(self, model, treepath, treeiter):
        self.treeview.set_cursor_on_cell(treepath, self.column, self.renderer, True)
        self.treeview.grab_focus()

    def row(self, model, path, itr):
        pass

    def add(self, *args):
        tbuf = self.entry.get_buffer()
        name = tbuf.get_text()
        if len(name) == 0:
            return
        treeiter = self.store.insert_with_values(None, -1, (0,), (name.upper(),))
        self.current = name.upper()
        items = []
        def row(model, path, itr):
            name = model.get(itr, 0)[0]
            items.append(name)
        self.store.foreach(row)
        with open(ENV['FILE']['PURPOSES'], 'w') as fj:
            json.dump(sorted(items), fj)
        self.update()

    def rename(self, *args):
        try:
            tbuf = self.entry.get_buffer()
            renamed = tbuf.get_text()
            if len(renamed) == 0:
                return
            tbuf.set_text(renamed.upper(), -1)
            model, treeiter = self.selection.get_selected()
            if treeiter is None:
                return
            model.remove(treeiter)
            treeiter = self.store.insert_with_values(None, -1, (0,), (renamed.upper(),))
            self.selection.select_iter(treeiter)
            items = []
            def row(model, path, itr):
                name = model.get(itr, 0)[0]
                items.append(name)
                self.current = name.upper()
            model.foreach(row)
            with open(ENV['FILE']['PURPOSES'], 'w') as fj:
                json.dump(sorted(items), fj)
            self.update()
        except Exception as error:
            self.log.error(error)

    def remove(self, *args):
        model, treeiter = self.selection.get_selected()
        if model is None or treeiter is None:
            return
        model.remove(treeiter)
        items = []
        def row(model, path, itr):
            name = model.get(itr, 0)[0]
            items.append(name)
            self.current = name.upper()
        model.foreach(row)
        with open(ENV['FILE']['PURPOSES'], 'w') as fj:
            json.dump(sorted(items), fj)
        self.update()

    def check_config_file(self):
        if not os.path.exists(ENV['FILE']['PURPOSES']):
            import shutil
            self.log.debug("Purposes config file doesn't exist.")
            default_purposes = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-purposes.json')
            shutil.copy(default_purposes, ENV['FILE']['PURPOSES'])
            self.log.debug("Purposes config file created")

    def update(self):
        self.store.clear()
        with open(ENV['FILE']['PURPOSES'], 'r') as fin:
            items = json.load(fin)
        pos = 0
        for item in items:
            node = self.store.insert_with_values(None, pos, (0,), (item,))
            pos += 1

        def row(model, path, itr):
            name = model.get(itr, 0)[0]
            if name is not None and name.upper() == self.current.upper():
                self.selection.select_iter(itr)
        self.store.foreach(row)

    def __clb_visible_function(self, model, itr, data):
        return True
