#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime

import humanize

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

class MiAZSelector(Gtk.Box):
    def __init__(self, app):
        super(MiAZSelector, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        boxMain = self.app.factory.create_box_horizontal(hexpand=True, vexpand=True)
        boxLeft = self.app.factory.create_box_vertical(hexpand=True, vexpand=True)
        boxRight = self.app.factory.create_box_vertical(hexpand=True, vexpand=True)
        boxMain.append(boxLeft)
        boxMain.append(boxRight)
        boxCenter = Gtk.CenterBox()
        self.title = Gtk.Label()
        boxCenter.set_center_widget(self.title)
        self.append(boxCenter)
        self.append(boxMain)

        # Available
        title = Gtk.Label()
        title.set_markup("<b>Available</b>")
        available = self.app.factory.create_box_vertical(hexpand=True, vexpand=True)
        boxLeft.append(title)
        boxLeft.append(available)

        # Selected
        title = Gtk.Label()
        title.set_markup("<b>Selected</b>")
        selected = self.app.factory.create_box_vertical(hexpand=True, vexpand=True)
        boxLeft.append(title)
        boxLeft.append(selected)



    def set_title(self, label:str = 'Selector'):
        self.title.set_markup(label)
