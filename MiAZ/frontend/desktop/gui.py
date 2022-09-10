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

from MiAZ.backend.env import ENV
from MiAZ.backend.controller import get_documents
from MiAZ.frontend.desktop.widgets import MiAZStack
from MiAZ.frontend.desktop.widgets import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets import MiAZMenuButton
from MiAZ.frontend.desktop.widgets import ListViewStrings
from MiAZ.frontend.desktop.widgets import ListViewListStore
from MiAZ.frontend.desktop.widgets import ColumnViewListStore


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here
        print("Firing desktop application!")

class ListElem(GObject.GObject):
    """ custom data element for a ListView model (Must be based on GObject) """

    def __init__(self, name: str):
        super(ListElem, self).__init__()
        self.name = name

    def __repr__(self):
        return f'ListElem(name: {self.name})'

class MyListView(ListViewListStore):
    """ Custom ListView """

    def __init__(self, win: Gtk.ApplicationWindow):
        # Init ListView with store model class.
        super(MyListView, self).__init__(ListElem)
        self.win = win
        self.set_valign(Gtk.Align.FILL)
        # put some data into the model
        # FIXME!!!
        docs = get_documents('.')
        for doc in docs:
            self.add(ListElem(doc))


    def factory_setup(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::setup signal callback (overloaded from parent class)

        Handles the creation widgets to put in the ListView
        """
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_margin_start(10)
        box.append(label)
        item.set_child(box)

    def factory_bind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::bind signal callback (overloaded from parent class)

        Handles adding data for the model to the widgets created in setup
        """
        # get the Gtk.Box stored in the ListItem
        box = item.get_child()
        # get the model item, connected to current ListItem
        data = item.get_item()
        # get the Gtk.Label (first item in box)
        label = box.get_first_child()
        # Update Gtk.Label with data from model item
        label.set_text(data.name)
        # Update Gtk.Switch with data from model item
        item.set_child(box)

    def factory_unbind(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::unbind signal callback (overloaded from parent class) """
        pass

    def factory_teardown(self, widget: Gtk.ListView, item: Gtk.ListItem):
        """ Gtk.SignalListItemFactory::teardown signal callback (overloaded from parent class """
        pass

    def selection_changed(self, widget, ndx: int):
        """ trigged when selecting in listview is changed"""
        print("%s - %s - %d" % (widget, type(widget), ndx))

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
        workspace = self.create_workspace()
        self.stack.add_page('workspace', "Workspace", workspace)

        docbrowser_label = Gtk.Label()
        docbrowser_label.set_text("Document Browser")
        self.stack.add_page('browser', "Browser", docbrowser_label)

        self.mainbox.append(self.stack)
        self.win.set_child(self.mainbox)
        ## ]]
        # ]
        self.win.present()

    def create_workspace(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_vexpand(True)
        listview = MyListView(self)
        sw = Gtk.ScrolledWindow()
        sw.set_child(listview)
        box.append(sw)
        return sw

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