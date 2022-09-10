#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_vexpand(True)
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)
        icon = Pixbuf.new_from_file('/home/t00m/Documents/devel/github/MiAZ/MiAZ/data/icons/MiAZ.svg')
        self.store = Gtk.TreeStore(Pixbuf, str, bool)
        for i in range(0, 100):
            self.store.insert_with_values(None, i, (0, 1, 2), (icon, i, True))
            # DOC: https://docs.gtk.org/gtk4/method.TreeStore.insert_with_values.html
            # ~ insert_with_values (self, parent:Gtk.TreeIter=None, position:int, columns:list, values:list) -> iter:Gtk.TreeIter

        self.tree = Gtk.TreeView.new_with_model(self.store)

        colA = Gtk.TreeViewColumn("Icon", Gtk.CellRendererPixbuf(), pixbuf=0)
        colB = Gtk.TreeViewColumn("Document", Gtk.CellRendererText(), text=1)
        colC = Gtk.TreeViewColumn("Loaded", Gtk.CellRendererToggle(), active=2)
        colA.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        colC.set_visible(True)
        colB.set_expand(True)
        colC.set_expand(False)
        colC.set_clickable(True)
        colC.set_sort_indicator(False)
        self.tree.append_column(colA)
        self.tree.append_column(colB)
        self.tree.append_column(colC)
        self.scrwin.set_child(self.tree)
        self.append(self.scrwin)

    def load_data(self, files: list):
        for filepath in files:
            self.store.insert_with_values(None, filepath)