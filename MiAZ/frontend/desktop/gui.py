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

from MiAZ.backend import MiAZBackend
from MiAZ.backend.controller import get_documents
from MiAZ.backend.log import get_logger
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
        self.backend = MiAZBackend()
        self.config = self.backend.get_conf()
        self.log = get_logger("MiAZ.GUI")
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_default_size(1024, 728)
        self.icman = MiAZIconManager()
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.win.set_icon_name('MiAZ')
        self.build_gui()
        self.backend.check_sources()
        self.log.debug("Executing MiAZ Desktop mode")
        self.win.present()

    def get_backend(self):
        return self.backend

    def get_config(self, name: str):
        config = self.backend.get_conf()
        return config[name]

    def build_gui(self):
        ## Central Box [[
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mainbox.set_vexpand(True)

        # Widgets

        # ~ status_page = Adw.StatusPage.new()
        # ~ status_page.set_description(description='A personal document organizer')
        # ~ status_page.set_icon_name(icon_name='MiAZ-extra-big')
        # ~ status_page.set_title(title='MiAZ')
        # ~ self.mainbox.append(child=status_page)

        ## Stack & Stack.Switcher
        self.stack = Adw.ViewStack()
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)

        # ~ self.stack.set_transition_type(transition=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        # ~ self.stack.set_transition_duration(duration=1000)
        # ~ self.stack.set_visible(False)

        ## HeaderBar [[
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(title_widget=self.switcher)
        self.win.set_titlebar(self.header)

        # Add Search button to the titlebar (Left side)
        # ~ button = Gtk.Button.new_from_icon_name('miaz-search')
        # ~ self.header.pack_start(button)
        # ~ button.connect('clicked', self.show_searchbar)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)

        # Create actions to handle menu actions
        self.create_action('settings', self.menu_handler)
        self.create_action('help', self.menu_handler)
        self.create_action('about', self.menu_handler)
        self.create_action('close', self.menu_handler)
        ## ]]



        # ~ self.box_header = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        # ~ # https://gist.github.com/Afacanc38/76ce9b3260307bea64ebf3506b485147
        # ~ boxSearchBar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # ~ self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        # ~ self.ent_sb.connect('changed', self.nop)
        # ~ self.searchbar = Gtk.SearchBar(halign = Gtk.Align.FILL, hexpand = True, valign = Gtk.Align.START, show_close_button = True)
        # ~ self.searchbar.connect_entry (self.ent_sb)
        # ~ boxSearchBar.append(self.ent_sb)
        # ~ self.searchbar.set_child (boxSearchBar)
        # ~ self.searchbar.set_key_capture_widget(self.ent_sb)
        # ~ self.box_header.append(self.searchbar)
        # ~ self.controller = Gtk.EventControllerKey()
        # ~ self.controller.connect('key-released', self.on_key_released)
        # ~ self.win.add_controller(self.controller)
        # ~ self.mainbox.append(self.box_header)

        self.docbrowser = self.create_docbrowser()
        page = self.stack.add_titled(self.docbrowser, 'browser', 'Browser')
        # ~ page = self.stack.get_page(self.docbrowser)
        page.set_icon_name('view-grid')


        self.workspace = self.create_workspace()
        page = self.stack.add_titled(self.workspace, 'workspace', 'Workspace')
        page.set_icon_name('document-properties')
        page.set_needs_attention(True)
        page.set_badge_number(1)

        self.mainbox.append(self.stack)
        self.mainbox.set_vexpand(True)
        self.win.set_child(self.mainbox)
        ## ]]
        # ]

    def get_stack_page_by_name(self, name: str) -> Adw.ViewStackPage:
        widget = self.stack.get_child_by_name(name)
        return self.stack.get_page(widget)

    def on_key_released(self, widget, keyval, keycode, state):
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
        elif stack == 'browser':
            self.docbrowser.filter_view()

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
        self.log.debug("Refreshing workspace")
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
        # ~ button.get_style_context().add_class(class_name='success')
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

    def get_searchbar_entry(self):
        return self.ent_sb
