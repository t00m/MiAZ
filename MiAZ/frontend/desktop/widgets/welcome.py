#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: about.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Welcome widget
"""

import gi
from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.env import ENV


class MiAZWelcome(Gtk.Box):
    """
    About class
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.factory = self.app.get_factory()
        centerbox = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
        centerbox.set_vexpand(True)
        centerbox.set_hexpand(True)
        self.append(centerbox)

        vbox = self.factory.create_box_vertical(hexpand=True, vexpand=False)
        centerbox.set_center_widget(vbox)

        label = Gtk.Label.new('Welcome')
        label.get_style_context().add_class(class_name='title-1')
        vbox.append(label)
        label = Gtk.Label()
        label.set_markup("No repository has been found.\nPlease, open the <i>Application Settings</i> to create a new one.")
        vbox.append(label)



