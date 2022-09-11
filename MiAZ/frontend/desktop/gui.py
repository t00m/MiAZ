#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Pango

from MiAZ.backend.env import ENV
from MiAZ.backend.controller import get_documents
from MiAZ.frontend.desktop.widgets.stack import MiAZStack
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace


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

        ## Stack & Stack.Switcher
        self.stack = MiAZStack()
        self.stack.set_vexpand(True)

        ## HeaderBar [[
        self.header = Gtk.HeaderBar()
        self.win.set_titlebar(self.header)
        self.header.set_title_widget(self.stack.switcher)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)
        # Create actions to handle menu actions
        self.create_action('new', self.menu_handler)
        self.create_action('about', self.menu_handler)
        self.create_action('quit', self.menu_handler)
        self.create_action('shortcuts', self.menu_handler)

        # ~ self.about_button = Gtk.Button(label="About")
        # ~ self.about_button.set_icon_name("open-menu")
        # ~ self.about_button.connect('clicked', self.show_about)
        # ~ self.header.pack_end(self.about_button)
        ## ]]

        ## Central Box [[
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mainbox.set_vexpand(True)

        docbrowser_label = Gtk.Label()
        docbrowser_label.set_text("Document Browser")
        self.stack.add_page('browser', "Browser", docbrowser_label)

        workspace = self.create_workspace()
        self.stack.add_page('workspace', "Workspace", workspace)

        self.mainbox.append(self.stack)
        self.mainbox.set_vexpand(True)
        self.win.set_child(self.mainbox)
        ## ]]
        # ]
        self.win.present()

    def create_workspace(self):
        return MiAZWorkspace(self.win)


    def create_action(self, name, callback):
        """ Add an Action and connect to a callback """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)


    def menu_handler(self, action, state):
            """ Callback for  menu actions"""
            name = action.get_name()
            print(f'active : {name}')
            if name == 'quit':
                self.close()

    def close(self):
        print("Close")

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