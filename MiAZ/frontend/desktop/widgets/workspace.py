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
from MiAZ.backend.util import get_file_mimetype

class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, win):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.set_vexpand(True)
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)
        # Model: document icon, current filename, suggested filename (if needed), accept suggestion
        self.store = Gtk.TreeStore(Pixbuf, bool, str, str)
        # ~ for i in range(0, 1000):
            # ~ self.store.insert_with_values(None, i, (0, 1, 2, 3), (icon, i, i, False))
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
        from MiAZ.backend.controller import get_documents
        documents = get_documents('/home/t00m/Documents/drive/Documents')
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        print(dir(self.theme))
        icons = {}

        for filepath in documents:
            mimetype = get_file_mimetype(filepath)
            try:
                gicon = icons[mimetype]
            except:
                gicon = Gio.content_type_get_icon(mimetype)
                paintable = self.theme.lookup_by_gicon(gicon, 64, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.FORCE_REGULAR)
                gfile = paintable.get_file()
                path = gfile.get_path()
                icon = Pixbuf.new_from_file_at_size(path, 48, 48)
                icons[mimetype] = icon

            document = os.path.basename(filepath)
            self.store.insert_with_values(None, -1, (0, 1, 2, 3), (icon, False, document, document))