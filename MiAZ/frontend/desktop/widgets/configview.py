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

class MiAZConfigView(MiAZWidget, Gtk.Box):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZConfigView'
    current = None
    config_local = None
    config_global = None
    config_for = None
    search_term = ''

    def __init__(self, app):
        super().__init__(app, __class__.__name__)
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_start(margin=12)

        # Entry and buttons for collection operations (edit/add/remove)
        self.box_oper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-delete')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self.on_entrysearch_delete)
        self.entry.connect('changed', self.on_entrysearch_changed)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        box_entry.append(self.entry)
        self.box_oper.append(box_entry)
        self.box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_buttons.append(self.app.create_button('miaz-edit', '', self.on_item_rename))
        self.box_buttons.append(Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL))
        self.box_buttons.append(self.app.create_button('miaz-add', '', self.on_item_add))
        self.box_buttons.append(self.app.create_button('miaz-remove', '', self.on_item_remove))
        self.box_oper.append(self.box_buttons)
        self.append(self.box_oper)

        widget = self.setup_treeview()
        self.append(widget)

        # ~ # InfoBar
        # FIXME: Low priority. User mesasges
        # ~ self.infobar = Gtk.InfoBar()
        # ~ self.infobar.set_revealed(True)
        # ~ self.infobar.set_show_close_button(False)
        # ~ self.infobar.set_message_type(Gtk.MessageType.INFO)
        # ~ self.infobar.connect('response', self.infobar_response)
        # ~ self.append(self.infobar)
        # ~ self.infobar_message()

    def on_entrysearch_delete(self, *args):
        self.entry.set_text("")


    def on_entrysearch_changed(self, *args):
        self.search_term = self.entry.get_text()
        self.treefilter.refilter()

    def infobar_message(self, text=''):
        return
        # FIXME: retrieve widget and update it
        if len(text) > 0:
            message_label = Gtk.Label()
            message_label.set_markup(text)
            self.infobar.add_child(message_label)

    def infobar_response(self, infobar, response):
        if response == Gtk.ResponseType.CLOSE:
            infobar.set_revealed(False)

    def setup_treeview(self):
        # Treeview for displaying
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.scrwin.set_has_frame(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.ListStore(str)
        self.selection = self.treeview.get_selection()
        self.sig_selection_changed = self.selection.connect('changed', self.on_selection_changed)

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
        if selection is None:
            return
        try:
            model, treeiter = selection.get_selected()
            name = model[treeiter][0]
            tbuf = self.entry.get_buffer()
            tbuf.set_text(name, -1)
            self.current = name.upper()
        except Exception as error:
            pass

    def __row_inserted(self, model, treepath, treeiter):
        self.treeview.set_cursor_on_cell(treepath, self.column, self.renderer, True)
        self.treeview.grab_focus()

    def row(self, model, path, itr):
        pass

    def config_save(self, items):
        with open(self.config_local, 'w') as fj:
            json.dump(items, fj)

    def on_item_add(self, *args):
        # Add new item, save config and refresh model
        item = self.entry.get_text().upper()
        items = self.config_load()
        items.add(item.upper())
        self.config_save(list(items))
        self.log.debug("Added %s to %s", item, self.config_for)
        self.entry.set_text('')
        self.entry.activate()
        self.update()
        self.infobar.set_message_type(Gtk.MessageType.INFO)
        self.infobar_message("Added new entry: %s" % item)

    def on_item_rename(self, *args):
        return

    def on_item_remove(self, *args):
        # Delete from config and refresh model
        item = self.entry.get_text()
        items = self.config_load()
        try:
            items.remove(item)
            self.log.debug("Removed %s from %s", item, self.config_for)
            self.config_save(list(items))
            self.update()
            self.entry.set_text('')
            self.entry.activate()
        except KeyError as error:
            self.infobar.set_message_type(Gtk.MessageType.ERROR)
            self.infobar_message("This entry doesn't exist. Nothing deleted.")
            return

    # ~ def config_check(self):
        # ~ if not os.path.exists(self.config_local):
            # ~ import shutil
            # ~ self.log.debug("Local config file for %s doesn't exist." % self.config_for)
            # ~ try:
                # ~ shutil.copy(self.config_global, self.config_local)
                # ~ self.log.debug("Local config file for %s created from global config" % self.config_for)
            # ~ except FileNotFoundError:
                # ~ self.log.warning("Global config file for %s not found" % self.config_for)
                # ~ self.config_save([])
                # ~ self.log.debug("Local config file for %s created empty" % self.config_for)

    # ~ def config_load(self):
        # ~ with open(self.config_local, 'r') as fin:
            # ~ items = json.load(fin)
        # ~ return items

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

        match = self.search_term.upper() in item_name.upper()
        if match:
            return True
        else:
            return False

    def config_set(self, config_for, config_local, config_global):
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global
