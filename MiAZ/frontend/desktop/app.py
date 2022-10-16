#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend import MiAZBackend
from MiAZ.backend.util import dir_writable
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.settings import MiAZPrefsWindow
from MiAZ.frontend.desktop.widgets.about import MiAZAbaout
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.factory import MiAZFactory


class MiAZApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backend = MiAZBackend()
        self.log = get_logger("MiAZ.GUI")
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_default_size(1024, 728)
        self.win.set_icon_name('MiAZ')
        self.win.set_default_icon_name('MiAZ')
        self.icman = MiAZIconManager()
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.factory = MiAZFactory(self)
        self.build_gui()
        # ~ self.listen_to_key_events()
        self.log.debug("Executing MiAZ Desktop mode")
        self.win.present()

    def get_backend(self):
        return self.backend

    def get_config(self, name: str):
        return self.backend.get_conf()[name]

    def get_factory(self):
        return self.factory

    def get_workspace(self):
        return self.workspace

    def build_gui(self):
        ## Central Box
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mainbox.set_vexpand(True)
        self.win.set_child(self.mainbox)

        # Widgets
        ## Stack & Stack.Switcher
        self.stack = Adw.ViewStack()
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)
        self.mainbox.append(self.stack)

        # Create workspace
        self.workspace = MiAZWorkspace(self)
        self.page_workspace = self.stack.add_titled(self.workspace, 'workspace', 'MiAZ')
        self.page_workspace.set_icon_name('document-properties')
        self.page_workspace.set_needs_attention(True)
        self.page_workspace.set_badge_number(1)
        self.page_workspace.set_visible(True)
        self.show_stack_page_by_name('workspace')

        ## HeaderBar
        boxDashboardButtons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True)
        btnDashboardOK = self.factory.create_button('miaz-dashboard-ok', 'Dashboard', callback=self.workspace.on_show_dashboard, css_classes=['flat', 'linked', 'toolbar'])
        btnDashboardKO = self.factory.create_button('miaz-dashboard-ko', 'Review', callback=self.workspace.on_show_review, css_classes=['flat', 'linked', 'toolbar'])
        boxDashboardButtons.append(btnDashboardOK)
        boxDashboardButtons.append(btnDashboardKO)
        self.header = Adw.HeaderBar()
        # ~ self.header.set_title_widget(title_widget=self.switcher)
        self.header.set_title_widget(title_widget=boxDashboardButtons)
        self.win.set_titlebar(self.header)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)

        # and create actions to handle menu actions
        for action in ['settings', 'help', 'about', 'close']:
            self.factory.create_action(action, self.menu_handler)

    def menu_handler(self, action, state):
            """ Callback for  menu actions"""
            name = action.get_name()
            if name == 'settings':
                self.show_settings()
            elif name == 'about':
                self.show_about()
            elif name == 'close':
                self.quit()

    def get_stack_page_by_name(self, name: str) -> Adw.ViewStackPage:
        widget = self.stack.get_child_by_name(name)
        return self.stack.get_page(widget)

    def show_stack_page_by_name(self, name: str = 'workspace'):
        self.stack.set_visible_child_name(name)

    def show_settings(self, *args):
        pw = MiAZPrefsWindow(self)

    def show_about(self, *args):
        about = MiAZAbaout(self).show()


