#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod

import gi
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions as Ext


class MiAZDocBrowser(Gtk.Box):
    """ MiAZ Doc Browser Widget"""

    def __init__(self, gui):
        super(MiAZDocBrowser, self).__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZDocBrowser')
        self.gui = gui
        self.config = self.gui.config
        self.set_margin_top(margin=6)
        self.set_margin_end(margin=6)
        self.set_margin_bottom(margin=6)
        self.set_margin_start(margin=6)
        self.set_vexpand(True)

        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        self.box_header = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        # https://gist.github.com/Afacanc38/76ce9b3260307bea64ebf3506b485147
        boxSearchBar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        self.ent_sb.connect('changed', self.nop)
        self.searchbar = Gtk.SearchBar(halign = Gtk.Align.FILL, hexpand = True, valign = Gtk.Align.START, show_close_button = True)
        self.searchbar.connect_entry (self.ent_sb)
        boxSearchBar.append(self.ent_sb)
        self.searchbar.set_child (boxSearchBar)
        self.searchbar.set_key_capture_widget(self.ent_sb)
        self.box_header.append(self.searchbar)

        self.controller = Gtk.EventControllerKey()
        self.controller.connect('key-released', self.on_key_released)
        self.gui.win.add_controller(self.controller)

        self.append(self.box_header)
        # ~ self.append(toolbar)

        self.flowbox = Gtk.FlowBox.new()
        self.flowbox.set_margin_top(margin=24)
        self.flowbox.set_margin_end(margin=12)
        self.flowbox.set_margin_bottom(margin=24)
        self.flowbox.set_margin_start(margin=12)
        self.flowbox.set_valign(align=Gtk.Align.START)
        self.flowbox.set_max_children_per_line(n_children=1)
        self.flowbox.set_selection_mode(mode=Gtk.SelectionMode.NONE)
        self.scrwin.set_child(child=self.flowbox)

        self.append(self.scrwin)

        # Filename format: {timestamp}-{country}-{lang}-{collection}-{organization}-{purpose}-{who}.{extension}

    def on_key_released(self, widget, keyval, keycode, state):
        # ~ self.log.debug("Active window: %s", self.gui.get_active_window())
        keyname = Gdk.keyval_name(keyval)
        # ~ self.log.debug("Key: %s", keyname)
        if Gdk.ModifierType.CONTROL_MASK & state and keyname == 'f':
            if self.searchbar.get_search_mode():
                self.searchbar.set_search_mode(False)
            else:
                self.searchbar.set_search_mode(True)

    def nop(self, *args):
        self.log.debug(args)

    def update(self):
        self.flowbox = Gtk.FlowBox.new()
