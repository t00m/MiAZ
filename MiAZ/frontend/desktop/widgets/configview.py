#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod
import json

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.widgets.widget import MiAZWidget
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd

class MiAZConfigView(MiAZWidget, Gtk.Box):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZConfigView'
    current = None
    config_local = None
    config_global = None
    config_for = None
    search_term = ''

    def __init__(self, app, config_for):
        print(config_for)
        super().__init__(app, __class__.__name__)
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.backend = app.get_backend()
        self.config_for = config_for
        self.factory = self.app.get_factory()
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_start(margin=12)

        # Entry and buttons for collection operations (edit/add/remove)
        self.box_oper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_oper.set_vexpand(False)
        box_entry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-clear')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self.on_entrysearch_delete)
        self.entry.connect('changed', self.on_entrysearch_changed)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        box_entry.append(self.entry)
        self.box_oper.append(box_entry)
        self.box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_buttons.set_hexpand(False)
        # ~ self.box_buttons.append(self.factory.create_button('miaz-edit', '', self.on_item_rename))
        # ~ self.box_buttons.append(Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL))
        self.box_buttons.append(self.factory.create_button('miaz-list-add', '', self.on_item_add, self.config_for))
        self.box_buttons.append(self.factory.create_button('miaz-list-remove', '', self.on_item_remove))
        self.box_oper.append(self.box_buttons)
        self.append(self.box_oper)

        widget = self.setup_treeview()
        self.append(widget)

        self.log.debug("Initialized")

    def on_key_released(self, widget, keyval, keycode, state):
        self.log.debug("Active window: %s", self.app.get_active_window())
        keyname = Gdk.keyval_name(keyval)
        self.log.debug("Key: %s", keyname)

    def on_entrysearch_delete(self, *args):
        self.entry.set_text("")

    def on_entrysearch_changed(self, *args):
        self.search_term = self.entry.get_text()
        self.treefilter.refilter()
        if len(self.search_term) == 0:
            self.treeview.collapse_all()
        else:
            self.treeview.expand_all()

    def setup_treeview(self):
        # Treeview for displaying
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.scrwin.set_has_frame(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.ListStore(str)
        self.selection = self.treeview.get_selection()
        self.selection.connect('changed', self.on_selection_changed)

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
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 0)
        self.sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.treeview.set_model(self.sorted_model)

        self.scrwin.set_child(self.treeview)

        return self.scrwin

    def clb_sort_function(self, model, row1, row2, sort_column=0):
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    def on_selection_changed(self, selection):
        pass

    def __row_inserted(self, model, treepath, treeiter):
        self.treeview.set_cursor_on_cell(treepath, self.column, self.renderer, True)
        self.treeview.grab_focus()

    def config_save(self, items):
        with open(self.config_local, 'w') as fj:
            json.dump(items, fj)

    # ~ def on_item_add(self, *args):
        # ~ # Add new item, save config and refresh model
        # ~ item = self.entry.get_text().upper()
        # ~ items = self.config.load()
        # ~ items.add(item.upper())
        # ~ self.config.save(items)
        # ~ self.log.debug("%s - Added: %s", self.config_for, item)
        # ~ self.entry.set_text('')
        # ~ self.entry.activate()
        # ~ self.update()

    def on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'New %s' % self.config_for, '%s name' % self.config_for.title(), '')
        boxkey2 = dialog.get_boxKey2()
        boxkey2.set_visible(False)
        etyValue1 = dialog.get_value1_widget()
        search_term = self.entry.get_text()
        etyValue1.set_text(search_term)
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            value = dialog.get_value1()
            if len(value) > 0:
                items = self.config.load()
                if not value in items:
                    items.append(value.upper())
                    self.config.save(items)
                    self.log.debug("Added: %s", value.upper())
                    self.update()
        dialog.destroy()

    def on_item_rename(self, *args):
        return

    def on_item_remove(self, *args):
        # Delete from config and refresh model
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        item = model[treeiter][0]

        if item is None:
            return
        if len(item) == 0:
            return

        self.config.remove(item)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def update(self):
        if self.config_local is None:
            return

        # Check config file and create it if doesn't exist
        self.config_check()
        self.store.clear()
        items = self.config_load()
        pos = 0
        for item in items:
            node = self.store.insert_with_values(pos, (0,), (item,))
            pos += 1

    def clb_visible_function(self, model, itr, data):
        item_name = model.get(itr, 0)[0]
        if item_name is None:
            return True
        if self.search_term is None:
            return True

        return self.search_term.upper() in item_name.upper()

    def config_set(self, config_for, config_local, config_global):
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global
