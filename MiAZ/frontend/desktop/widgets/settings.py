#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import gi
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.config import load_config
from MiAZ.backend.config import save_config


class MiAZSettings(Gtk.Dialog):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, win):
        super(MiAZSettings, self).__init__()
        self.set_default_size(480, 600)
        # ~ self.set_title('Settings')
        self.win = win
        self.log = win.log
        self.set_transient_for(self.win)
        self.set_modal(self)
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_bottom(margin=12)
        self.set_margin_start(margin=12)
        self.log.debug("MiAZSettings")
        # ~ self.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        self.connect("response", self.open_response)

        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)
        label = Gtk.Label()
        label.set_markup('<b>Settings</b>')
        self.header.set_title_widget(label)

        # Add Refresh button to the titlebar (Left side)
        button = Gtk.Button.new_from_icon_name('view-refresh')
        self.header.pack_start(button)
        # ~ button.connect('clicked', self.gui.refresh_workspace)

        contents = self.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_vexpand(True)
        scrwin = Gtk.ScrolledWindow.new()
        scrwin.set_vexpand(True)
        box.append(child=scrwin)
        # ~ flowbox = Gtk.FlowBox.new()
        # ~ flowbox.set_margin_top(margin=12)
        # ~ flowbox.set_margin_end(margin=12)
        # ~ flowbox.set_margin_bottom(margin=12)
        # ~ flowbox.set_margin_start(margin=12)
        # ~ flowbox.set_valign(align=Gtk.Align.START)
        # ~ flowbox.set_max_children_per_line(n_children=5)
        # ~ flowbox.set_selection_mode(mode=Gtk.SelectionMode.NONE)
        # ~ scrwin.set_child(child=flowbox)
        contents.append(box)

        # ~ for n in range(100):
            # ~ button = Gtk.Button.new_with_label(label=f'Botão {n}')
            # ~ flowbox.insert(widget=button, position=n)

        # ~ self.filechooser = Gtk.FileChooserWidget()
        # ~ self.filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        # ~ contents.append(self.filechooser)

    def open_response(self, *args):
        self.log.debug("Settings Response")
