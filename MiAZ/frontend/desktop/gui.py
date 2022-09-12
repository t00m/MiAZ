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
from MiAZ.backend.config import load_config
from MiAZ.backend.config import save_config
from MiAZ.backend.controller import get_documents
from MiAZ.frontend.desktop.widgets.stack import MiAZStack
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.icons import MiAZIconManager


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here
        # ~ print("Firing desktop application!")


class GUI(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)
        # ~ print("GUI.__init__")

    def on_activate(self, app):
        GLib.set_application_name(ENV['APP']['name'])
        self.win = MainWindow(application=app)
        self.win.set_default_size(1024, 728)
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.icman = MiAZIconManager(self.win)


        # Widgets

        ## Stack & Stack.Switcher
        self.stack = MiAZStack()
        self.stack.set_vexpand(True)

        ## HeaderBar [[
        self.header = Gtk.HeaderBar()
        self.win.set_titlebar(self.header)
        self.header.set_title_widget(self.stack.switcher)

        # Add Refresh button to the titlebar (Left side)
        # ~ icon_refresh = self.icman.get_pixbuf_by_name('refresh-view', 24)
        button = Gtk.Button.new_from_icon_name('view-refresh')
        self.header.pack_start(button)
        button.connect('clicked', self.refresh_workspace)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)
        # Create actions to handle menu actions
        self.create_action('settings', self.menu_handler)
        self.create_action('help', self.menu_handler)
        self.create_action('about', self.menu_handler)
        self.create_action('close', self.menu_handler)

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

        self.workspace = self.create_workspace()
        self.stack.add_page('workspace', "Workspace", self.workspace)

        self.mainbox.append(self.stack)
        self.mainbox.set_vexpand(True)
        self.win.set_child(self.mainbox)
        ## ]]
        # ]

        self.win.present()
        # ~ print("GUI.on_activate")

    def refresh_workspace(self, *args):
        print("Refresh Workspace view")
        self.workspace.refresh_view()

    def show_settings(self, *args):
        settings = Gtk.Dialog()
        settings.set_transient_for(self.win)
        settings.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        settings.connect("response", self.open_response)
        contents = settings.get_content_area()
        self.filechooser = Gtk.FileChooserWidget()
        self.filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        contents.append(self.filechooser)
        settings.show()

    def open_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            gfile = self.filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                print(dirpath)  # Here you could handle opening or saving the file
                config = load_config()
                if config is None:
                    config = {}
                config['source'] = dirpath
                save_config(config)
                dialog.destroy()
                self.workspace.refresh_view()
        else:
            dialog.destroy()

    def create_workspace(self):
        return MiAZWorkspace(self.win)


    def create_action(self, name, callback):
        """ Add an Action and connect to a callback """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        # ~ print("%s > %s > %s" % (action, name, callback))
        self.add_action(action)


    def menu_handler(self, action, state):
            """ Callback for  menu actions"""
            name = action.get_name()
            print(f'active : {name}')
            if name == 'settings':
                self.show_settings()
            elif name == 'about':
                self.show_about()
            elif name == 'close':
                self.close()

    def close(self):
        self.quit()

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