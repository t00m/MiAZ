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

class MiAZCollections(MiAZWidget, Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    __gtype_name__ = 'MiAZCollections'

    def __init__(self, app):
        super().__init__(app, __class__.__name__)
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.HORIZONTAL)
        self.app = app
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_bottom(margin=12)
        self.set_margin_start(margin=12)

        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.TreeStore(str)
        self.treeview.set_model(self.store)

        # Column: Name
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Name', renderer, text=0)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(True)
        column.set_sort_column_id(0)
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.__clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)

        # ~ self.tree.connect('row-activated', self.treeview.double_click)

        self.scrwin.set_child(self.treeview)
        self.append(self.scrwin)

        box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.VERTICAL)
        box_buttons.append(self.app.create_button('list-add', '', self.add))
        box_buttons.append(self.app.create_button('list-remove', '', self.remove))
        self.append(box_buttons)

        self.check()
        self.update()

    def add(self, *args):
        self.log.debug(args)
        node = self.store.insert_with_values(None, -1, (0,), ('',))

    def remove(self, *args):
        self.log.debug(args)

    def check(self):
        if not os.path.exists(ENV['FILE']['COLLECTIONS']):
            import shutil
            self.log.debug("Collections file doesn't exist.")
            default_collections = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-collections.json')
            shutil.copy(default_collections, ENV['FILE']['COLLECTIONS'])
            self.log.debug("Collections config file created")

        with open(ENV['FILE']['COLLECTIONS'], 'r') as fcol:
            self.collections = json.load(fcol)
            self.log.debug(self.collections)
            self.log.debug(type(self.collections))

    def update(self):
        for collection in self.collections:
            node = self.store.insert_with_values(None, -1, (0,), (collection,))

    def __clb_visible_function(self, model, itr, data):
        return True