#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib

from MiAZ.backend.env import ENV


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here
        print("Firing desktop application!")

class GUI(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        GLib.set_application_name(ENV['APP']['name'])
        self.win = MainWindow(application=app)
        self.win.set_default_size(800, 600)
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])


        # Widgets
        ## HeaderBar [
        self.header = Gtk.HeaderBar()
        self.win.set_titlebar(self.header)
        self.about_button = Gtk.Button(label="About")
        self.about_button.connect('clicked', self.show_about)
        self.header.pack_start(self.about_button)
        ## ]

        # Central Box [
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label()
        label.set_markup("<b>%s</b>" % ENV['APP']['name'])
        button = Gtk.Button(label="Hola carabola")
        button.connect("clicked", self.show_about)
        self.mainbox.append(label)
        self.mainbox.append(button)
        self.win.set_child(self.mainbox)
        ## ]
        self.win.present()


    def show_about(self, *args):
        about = Gtk.AboutDialog()
        about.set_transient_for(self.win)  # Makes the dialog always appear in from of the parent window
        about.set_modal(self)  # Makes the parent window unresponsive while dialog is showing
        about.set_authors([ENV['APP']['author']])
        about.set_copyright(ENV['APP']['copyright'])
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_website(ENV['APP']['website'])
        about.set_website_label(ENV['APP']['name'])
        about.set_version(ENV['APP']['version'])
        about.set_logo_icon_name("MiAZ")
        about.show()
        return about