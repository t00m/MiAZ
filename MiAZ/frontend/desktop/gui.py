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
from MiAZ.backend.util import dir_writable
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.docbrowser import MiAZDocBrowser
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.settings import MiAZPrefsWindow
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistant
from MiAZ.frontend.desktop.icons import MiAZIconManager

Gtk.init()
Adw.init()

class GUI(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backend = MiAZBackend()
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
        Gtk.Window.set_default_icon_name('MiAZ')
        self.build_gui()
        self.check_basic_settings()
        self.log.debug("Executing MiAZ Desktop mode")
        # ~ self.win.present()

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

        ## Stack & Stack.Switcher
        self.stack = Adw.ViewStack()
        # ~ self.stack.set_transition_type(transition=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        # ~ self.stack.set_transition_duration(duration=300)
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)

        ## HeaderBar [[
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(title_widget=self.switcher)
        self.win.set_titlebar(self.header)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)

        # Create actions to handle menu actions
        self.create_action('settings', self.menu_handler)
        self.create_action('help', self.menu_handler)
        self.create_action('about', self.menu_handler)
        self.create_action('close', self.menu_handler)
        ## ]]

        # ~ # https://gist.github.com/Afacanc38/76ce9b3260307bea64ebf3506b485147

        self.docbrowser = self.create_docbrowser()
        # ~ self.docbrowser.connect('show', self.on_browser_show)
        self.page_browser = self.stack.add_titled(self.docbrowser, 'browser', 'Browser')
        self.docbrowser.connect('map', self.docbrowser.doesnt_need_attention)
        self.page_browser.set_icon_name('view-grid')
        # ~ self.page_browser.connect('show', self.on_browser_show)

        self.workspace = self.create_workspace()
        self.page_workspace = self.stack.add_titled(self.workspace, 'workspace', 'Workspace')
        self.page_workspace.set_icon_name('document-properties')
        self.page_workspace.set_needs_attention(True)
        self.page_workspace.set_badge_number(1)

        status_page = Adw.StatusPage.new()
        status_page.set_description(description='A personal document organizer')
        status_page.set_icon_name(icon_name='MiAZ-extra-big')
        status_page.set_title(title='MiAZ')
        button = self.create_button('edit-clear', 'Test', self.noop)
        status_page.set_child(button)
        self.page_status = self.stack.add_titled(status_page, 'welcome', 'Welcome')

        self.mainbox.append(self.stack)
        self.mainbox.set_vexpand(True)
        self.win.set_child(self.mainbox)

    def on_browser_show(self, *args):
        self.log.debug(args)

    def check_basic_settings(self):
        config = self.get_config('app')
        source = dir_writable(config.get('source'))
        target = dir_writable(config.get('target'))

        if source and target:
            self.log.debug("Source and Target exist")
            self.page_browser.set_visible(True)
            self.page_workspace.set_visible(True)
            self.page_status.set_visible(False)
            if self.page_workspace.get_needs_attention():
                self.show_workspace()
            else:
                self.show_browser()
            self.win.show()
        else:
            self.log.debug("Launching assistant")
            # ~ self.hide()
            # ~ self.win.hide()
            assistant = MiAZAssistant(self)
            assistant.set_transient_for(self.win)
            assistant.set_modal(True)
            assistant.show()
            self.page_browser.set_visible(False)
            self.page_workspace.set_visible(False)
            self.page_status.set_visible(True)
            self.show_welcome()


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

    def noop(self, *args):
        self.log.debug(args)
        # ~ stack = self.stack.get_visible_child_name()
        # ~ if stack == 'workspace':
            # ~ self.workspace.filter_view()

    def refresh_workspace(self, *args):
        self.workspace.refresh_view()

    def show_settings(self, *args):
        pw = MiAZPrefsWindow(self)

    def show_welcome(self, *args):
        self.stack.set_visible_child_name('welcome')

    def show_browser(self, *args):
        self.stack.set_visible_child_name('browser')

    def show_workspace(self, *args):
        self.log.debug("Refreshing workspace")
        self.stack.set_visible_child_name('workspace')

    def show_searchbar(self, *args):
        self.searchbar.set_search_mode(True)

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

    def create_switch_button(self, icon_name, title, callback):
        button = Gtk.Switch()
        button.connect('activate', callback)
        return button

    def create_button(self, icon_name, title, callback=None, width=32, height=32, css_classes=['flat'], data=None):
        if len(icon_name.strip()) == 0:
            button = Gtk.Button(css_classes=css_classes)
            button.set_label(title)
            button.set_valign(Gtk.Align.CENTER)
        else:
            button = Gtk.Button(
                css_classes=css_classes,
                child=Adw.ButtonContent(
                    label=title,
                    icon_name=icon_name
                    )
                )
        # ~ button.get_style_context().add_class(class_name='success')
        button.set_has_frame(True)
        if callback is None:
            button.connect('clicked', self.noop, data)
        else:
            button.connect('clicked', callback, data)
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
