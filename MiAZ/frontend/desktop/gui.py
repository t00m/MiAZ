#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Pango

from MiAZ.backend.env import ENV
from MiAZ.backend.config.settings import MiAZConfigApp
from MiAZ.backend.controller import get_documents
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.stack import MiAZStack
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.docbrowser import MiAZDocBrowser
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.settings import MiAZSettings, PreferencesWindow
from MiAZ.frontend.desktop.icons import MiAZIconManager

Gtk.init()
Adw.init()

class GUI(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log = get_logger("MiAZ.GUI")
        self.log.debug("Executing MiAZ Desktop mode")
        GLib.set_application_name(ENV['APP']['name'])
        self.config = MiAZConfigApp()
        self.connect('activate', self.on_activate)
        self.icman = MiAZIconManager()

    def on_activate(self, app):
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_default_size(1024, 728)
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.win.set_icon_name('MiAZ')
        self.build_gui()
        self.win.present()

    def build_gui(self):
        # Widgets
        ## Stack & Stack.Switcher
        self.stack = MiAZStack()
        self.stack.set_vexpand(True)

        ## HeaderBar [[
        self.header = Adw.HeaderBar()
        box = Gtk.Box(spacing = 3, orientation="horizontal")
        button = self.create_button('miaz-ok', 'Browser', self.show_browser)
        box.append(button)
        button = self.create_button('miaz-remove', 'Workspace', self.show_workspace)
        box.append(button)
        self.header.set_title_widget(box)
        self.win.set_titlebar(self.header)

        # Add Refresh button to the titlebar (Left side)
        # ~ button = Gtk.Button.new_from_icon_name('view-refresh')
        # ~ self.header.pack_start(button)
        # ~ button.connect('clicked', self.refresh_workspace)

        # Add Search button to the titlebar (Left side)
        button = Gtk.Button.new_from_icon_name('miaz-search')
        self.header.pack_start(button)
        button.connect('clicked', self.show_searchbar)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)

        # Create actions to handle menu actions
        self.create_action('settings', self.menu_handler)
        self.create_action('help', self.menu_handler)
        self.create_action('about', self.menu_handler)
        self.create_action('close', self.menu_handler)
        ## ]]

        ## Central Box [[
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mainbox.set_vexpand(True)

        self.docbrowser = self.create_docbrowser()
        self.stack.add_page('browser', "Browser", self.docbrowser)

        self.workspace = self.create_workspace()
        self.stack.add_page('workspace', "Workspace", self.workspace)

        self.settings = self.create_settings()
        self.stack.add_page('settings', "Settings", self.settings)

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
        self.win.add_controller(self.controller)

        self.mainbox.append(self.box_header)

        self.mainbox.append(self.stack)
        self.mainbox.set_vexpand(True)
        self.win.set_child(self.mainbox)
        ## ]]
        # ]

    def on_key_released(self, widget, keyval, keycode, state):
        # ~ self.log.debug("Active window: %s", self.gui.get_active_window())
        keyname = Gdk.keyval_name(keyval)
        self.log.debug("Key: %s", keyname)
        if Gdk.ModifierType.CONTROL_MASK & state and keyname == 'f':
            if self.searchbar.get_search_mode():
                self.searchbar.set_search_mode(False)
            else:
                self.searchbar.set_search_mode(True)
        stack = self.stack.get_visible_child_name()
        if stack == 'workspace':
            self.workspace.filter_view()

    def nop(self, *args):
        stack = self.stack.get_visible_child_name()
        if stack == 'workspace':
            self.workspace.filter_view()

    def refresh_workspace(self, *args):
        self.workspace.refresh_view()

    def show_settings(self, *args):
        pw = PreferencesWindow(self)
        # ~ self.stack.set_visible_child_name('settings')

    def show_browser(self, *args):
        self.stack.set_visible_child_name('browser')

    def show_workspace(self, *args):
        self.stack.set_visible_child_name('workspace')

    def show_searchbar(self, *args):
        self.searchbar.set_search_mode(True)

    def open_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            gfile = self.filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.log.info(dirpath)
                self.config.set('source', dirpath)
                dialog.destroy()
                self.workspace.refresh_view()
        else:
            dialog.destroy()

    def create_dialog(self, parent, title, widget, width=400, height=500):
        dialog = Gtk.Dialog()
        dlgHeader = Gtk.HeaderBar()
        dialog.set_titlebar(dlgHeader)
        dialog.set_modal(True)
        dialog.set_title(title)
        if width != -1 and height != -1:
            dialog.set_size_request(width, height)
        dialog.set_transient_for(parent)
        contents = dialog.get_content_area()
        contents.append(widget)
        return dialog

    # ~ def create_button(self, icon_name, title, callback, width=48, height=48):
        # ~ hbox = Gtk.Box(spacing = 3, orientation=Gtk.Orientation.HORIZONTAL)
        # ~ if len(icon_name) != 0:
            # ~ # FIXME: icon name might not exist at all
            # ~ pixbuf = self.icman.get_pixbuf_by_path(icon_name, width, height)
            # ~ icon = Gtk.Image.new_from_pixbuf(pixbuf)
            # ~ hbox.append(icon)
        # ~ label = Gtk.Label()
        # ~ label.set_markup(title)
        # ~ hbox.append(label)
        # ~ button = Gtk.Button()
        # ~ button.set_child(hbox)
        # ~ button.set_hexpand(True)
        # ~ button.set_vexpand(True)
        # ~ button.set_has_frame(True)
        # ~ button.connect('clicked', callback)
        # ~ return button

    def create_switch_button(self, icon_name, title, callback):
        button = Gtk.Switch()
        button.connect('activate', callback)
        return button

    def create_button(self, icon_name, title, callback, width=32, height=32, css_classes=['flat']):
        if len(icon_name.strip()) == 0:
            button = Gtk.Button(css_classes=css_classes)
            button.set_label(title)
        else:
            button = Gtk.Button(
                css_classes=css_classes,
                child=Adw.ButtonContent(
                    label=title,
                    icon_name=icon_name
                    )
                )
        button.connect('clicked', callback)
        return button

    def create_action(self, name, callback):
        """ Add an Action and connect to a callback """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

    def create_docbrowser(self):
        return MiAZDocBrowser(self)

    def create_workspace(self):
        return MiAZWorkspace(self)

    def create_settings(self):
        return MiAZSettings(self)

    def menu_handler(self, action, state):
            """ Callback for  menu actions"""
            name = action.get_name()
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
        about.set_transient_for(self.win)
        about.set_modal(self)
        about.set_authors([ENV['APP']['author']])
        about.set_copyright(ENV['APP']['copyright'])
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_website(ENV['APP']['website'])
        about.set_website_label(ENV['APP']['name'])
        about.set_version(ENV['APP']['version'])
        about.set_logo_icon_name("MiAZ")
        about.show()
        return about
