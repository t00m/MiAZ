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
from MiAZ.frontend.desktop.actions import MiAZActions
from MiAZ.frontend.desktop.help import show_shortcuts


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
        self.win.get_style_context().add_class(class_name='devel')
        self.icman = MiAZIconManager()
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.actions = MiAZActions(self)
        self.factory = MiAZFactory(self)
        self.build_gui()
        self.listen_to_key_events()
        self.log.debug("Executing MiAZ Desktop mode")
        self.win.present()

    def listen_to_key_events(self):
        evk = Gtk.EventControllerKey.new()
        evk.connect("key-pressed", self.key_press)
        self.win.add_controller(evk)

    def key_press(self, event, keyval, keycode, state):
        # ~ self.log.debug("%s > %s > %s > %s", event, keyval, keycode, state)
        keyname = Gdk.keyval_name(keyval)
        # ~ self.log.debug(keyname)


    def create_menu_actions(self):
        self.factory.create_action('quit', self.exit_app, ['Control_L', 'q'])

    def get_actions(self):
        return self.actions

    def get_backend(self):
        return self.backend

    def get_config(self, name: str):
        return self.backend.get_conf()[name]

    def get_factory(self):
        return self.factory

    def get_icman(self):
        return self.icman

    def get_workspace(self):
        return self.workspace

    def get_header(self):
        return self.header

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
        self.header = Adw.HeaderBar()

        boxDashboardButtons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True)
        btnDashboard = self.factory.create_button('miaz-dashboard-ok', 'Dashboard', callback=self.workspace.show_dashboard, css_classes=['flat', 'linked', 'toolbar'])
        btnReview = self.factory.create_button('miaz-dashboard-ko', 'Review', callback=self.workspace.show_review, css_classes=['flat', 'linked', 'toolbar'])
        boxDashboardButtons.append(btnDashboard)
        boxDashboardButtons.append(btnReview)
        self.header.pack_start(boxDashboardButtons)

        # ~ self.header.set_title_widget(title_widget=self.switcher)
        # ~ self.header.set_title_widget(title_widget=boxDashboardButtons)
        # ~ self.header.set_title_widget(Gtk.Label.new().set_markup('<i>Loading...</i>'))
        self.win.set_titlebar(self.header)

        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_APP_MENU, 'app-menu')
        self.header.pack_end(menu)

        # and create actions to handle menu actions
        for action, shortcut in [('settings', ['<Ctrl>s']),
                                 ('help', ['<Ctrl>h']),
                                 ('about', ['<Ctrl>b']),
                                 ('close', ['<Ctrl>q']),
                                 ('view', ['<Ctrl>v']),
                                 ('rename', ['<Ctrl>r'])
                                ]:
            self.factory.create_menu_action(action, self.menu_handler, shortcut)

    def menu_handler(self, action, state):
            """ Callback for  menu actions"""
            name = action.get_name()
            if name == 'settings':
                self.show_settings()
            elif name == 'about':
                self.show_about()
            elif name == 'close':
                self.quit()
            elif name == 'view':
                self.workspace.document_display()
            elif name == 'rename':
                self.workspace.document_rename()
            elif name == 'help':
                self.log.debug('Help!')
                show_shortcuts(self.win)

    def get_stack_page_by_name(self, name: str) -> Adw.ViewStackPage:
        widget = self.stack.get_child_by_name(name)
        return self.stack.get_page(widget)

    def show_stack_page_by_name(self, name: str = 'workspace'):
        self.stack.set_visible_child_name(name)

    def show_settings(self, *args):
        pw = MiAZPrefsWindow(self)

    def show_about(self, *args):
        about = MiAZAbaout(self).show()


    def update_title(self, displayed: int = 0, total:int = 0):
        header = self.get_header()
        title = header.get_title_widget()
        if title is not None:
            header.remove(title)
        wdgTitle = Adw.WindowTitle()
        wdgTitle.set_title('MiAZ')
        wdgTitle.set_subtitle("Displaying %d of %d documents" % (displayed, total))
        header.set_title_widget(wdgTitle)

    def exit_app(self, action, param):
        self.quit()

