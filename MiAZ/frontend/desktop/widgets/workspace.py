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

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.icons import MiAZIconManager


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, win):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.set_vexpand(True)
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)
        self.icman = MiAZIconManager(win)
        # Model: document icon, current filename, suggested filename (if needed), accept suggestion
        self.store = Gtk.TreeStore(Pixbuf, bool, str, str)
        # DOC: https://docs.gtk.org/gtk4/method.TreeStore.insert_with_values.html
        # ~ insert_with_values (self, parent:Gtk.TreeIter=None, position:int, columns:list, values:list) -> iter:Gtk.TreeIter

        self.tree = Gtk.TreeView.new_with_model(self.store)
        self.tree.set_can_focus(True)
        self.tree.set_enable_tree_lines(True)
        self.tree.set_headers_visible(True)
        self.tree.set_enable_search(True)
        self.tree.set_hover_selection(False)
        self.tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        self.load_data()

        colA = Gtk.TreeViewColumn("", Gtk.CellRendererPixbuf(), pixbuf=0)
        colB = Gtk.TreeViewColumn("Accept change", Gtk.CellRendererToggle(), active=1)
        colC = Gtk.TreeViewColumn("Current filename", Gtk.CellRendererText(), text=2)
        colD = Gtk.TreeViewColumn("Suggested filename", Gtk.CellRendererText(), text=3)

        colB.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        colC.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        colC.set_visible(True)
        colB.set_expand(False)
        colC.set_expand(False)
        colC.set_clickable(True)
        colC.set_sort_indicator(False)
        self.tree.append_column(colA)
        self.tree.append_column(colB)
        self.tree.append_column(colC)
        self.tree.append_column(colD)
        self.scrwin.set_child(self.tree)
        self.append(self.scrwin)

    def load_data(self):
        import os
        from MiAZ.backend.controller import get_documents, valid_filename
        documents = get_documents('/home/t00m/Documents/drive/Documents')
        icon = Pixbuf.new_from_file(ENV['FILE']['APPICON'])
        INVALID = self.store.insert_with_values(None, -1, (0, 1, 2, 3), (icon, False, "File name not valid", ""))
        VALID = self.store.insert_with_values(None, -1, (0, 1, 2, 3), (icon, False, "File name valid", ""))
        for filepath in documents:
            document = os.path.basename(filepath)
            icon = self.icman.get_pixbuf_mimetype_from_file(filepath)
            valid, reasons = valid_filename(document)
            if not valid:
                self.store.insert_with_values(INVALID, -1, (0, 1, 2, 3), (icon, False, document, document))
            else:
                self.store.insert_with_values(VALID, -1, (0, 1, 2, 3), (icon, False, document, ""))