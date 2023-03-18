#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontent/Desktop entry point
"""

import sys

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend import MiAZBackend
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepo
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.settings import MiAZAppSettings
from MiAZ.frontend.desktop.settings import MiAZRepoSettings
from MiAZ.frontend.desktop.widgets.about import MiAZAbout
from MiAZ.frontend.desktop.widgets.welcome import MiAZWelcome
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.factory import MiAZFactory
from MiAZ.frontend.desktop.actions import MiAZActions
from MiAZ.frontend.desktop.help import MiAZHelp
from MiAZ.backend.pluginsystem import MiAZPluginManager

Adw.init()

class MiAZApp(Adw.Application):
    # basic signals
    __gsignals__ = {
        "start-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "stop-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    widget_about = None
    widget_help = None
    widget_welcome = None
    widget_settings_app = None
    widget_settings_repo = None
    widget_rename = None
    widget_workspace = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget =  {}
        self.backend = MiAZBackend()
        self.conf = self.backend.conf
        self.log = get_logger("MiAZ.GUI")
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self._on_activate)

    def _on_activate(self, app):
        self.win = self.add_widget('window', Gtk.ApplicationWindow(application=self))
        self.win.set_default_size(1024, 728)
        self.win.set_icon_name('MiAZ')
        self.win.set_default_icon_name('MiAZ')
        self.icman = MiAZIconManager(self)
        self.theme = self.add_widget('theme', Gtk.IconTheme.get_for_display(self.win.get_display()))
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.actions = MiAZActions(self)
        self.factory = MiAZFactory(self)
        self._setup_gui()
        self.check_repository()
        self._setup_event_listener()
        self._setup_plugin_manager()
        self.log.debug("Plugins loaded:")
        for plugin in self.plugin_manager.plugins:
            if plugin.is_loaded():
                self.log.debug("\t[%s] %s %s (%s)",  self.plugin_manager.get_plugin_type(plugin), plugin.get_name(), plugin.get_version(), plugin.get_description())
        self.log.debug("Executing MiAZ Desktop mode")
        self.emit('start-application-completed')

    def _setup_plugin_manager(self):
        self.plugin_manager = self.add_widget('plugin-manager', MiAZPluginManager(self))

    def _setup_event_listener(self):
        evk = Gtk.EventControllerKey.new()
        self.add_widget('window-event-controller', evk)
        evk.connect("key-pressed", self._on_key_press)
        self.win.add_controller(evk)

    def _on_key_press(self, event, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            page_name = self.stack.get_visible_child_name()
            valid = self.check_repository()
            if valid:
                workspace = self.get_widget('workspace')
                workspace.update()
                self.show_stack_page_by_name('workspace')


    def get_actions(self):
        return self.actions

    def get_backend(self):
        return self.backend

    def get_config(self, name: str):
        return self.backend.conf[name]

    def get_factory(self):
        return self.factory

    def get_icman(self):
        return self.icman

    def get_workspace(self):
        return self.widget_workspace

    def get_header(self):
        return self.header

    def get_app_settings(self):
        return self.settings_app

    def _setup_stack(self):
        self.stack = Adw.ViewStack()
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)
        return self.stack

    def _setup_page_about(self):
        widget_about = self.get_widget('about')
        if widget_about is None:
            widget_about = self.add_widget('about', MiAZAbout(self))
            page_about = self.stack.add_titled(widget_about, 'about', 'MiAZ')
            page_about.set_icon_name('document-properties')

    def _setup_page_help(self):
        widget_help = self.get_widget('help')
        if widget_help is None:
            widget_help = self.add_widget('help', MiAZHelp(self))
            page_help = self.stack.add_titled(widget_help, 'help', 'MiAZ')
            page_help.set_icon_name('document-properties')
            page_help.set_visible(False)

    def _setup_page_welcome(self):
        widget_welcome = self.get_widget('welcome')
        if widget_welcome is None:
            widget_welcome = self.add_widget('welcome', MiAZWelcome(self))
            page_welcome = self.stack.add_titled(widget_welcome, 'welcome', 'MiAZ')
            page_welcome.set_icon_name('MiAZ')
            page_welcome.set_visible(True)

    def _setup_page_app_settings(self):
        if self.widget_settings_app is None:
            self.widget_settings_app = MiAZAppSettings(self)
            self.page_settings_app = self.stack.add_titled(self.widget_settings_app, 'settings_app', 'MiAZ')
            self.page_settings_app.set_icon_name('document-properties')
            self.page_settings_app.set_visible(False)

    def _setup_page_repo_settings(self):
        if self.widget_settings_repo is None:
            self.widget_settings_repo = MiAZRepoSettings(self)
            self.page_settings_repo = self.stack.add_titled(self.widget_settings_repo, 'settings_repo', 'MiAZ')
            self.page_settings_repo.set_icon_name('document-properties')
            self.page_settings_repo.set_visible(False)

    def _setup_page_workspace(self):
        widget_workspace = self.get_widget('workspace')
        if widget_workspace is None:
            widget_workspace = self.add_widget('workspace', MiAZWorkspace(self))
            page_workspace = self.stack.add_titled(widget_workspace, 'workspace', 'MiAZ')
            page_workspace.set_icon_name('document-properties')
            page_workspace.set_visible(True)
            self.show_stack_page_by_name('workspace')

    def _setup_page_rename(self):
        if self.widget_rename is None:
            self.widget_rename = MiAZRenameDialog(self)
            self.page_rename = self.stack.add_titled(self.widget_rename, 'rename', 'MiAZ')
            self.page_rename.set_icon_name('document-properties')
            self.page_rename.set_visible(False)

    def get_rename_widget(self):
        return self.get_stack_page_widget_by_name('rename')

    def _setup_headerbar_left(self):
        # Add Menu Button to the titlebar (Left Side)
        menu_headerbar = self.add_widget('menu-headerbar', Gio.Menu.new())
        section_common_in = Gio.Menu.new()
        section_common_out = Gio.Menu.new()
        section_danger = Gio.Menu.new()
        menu_headerbar.append_section(None, section_common_in)
        menu_headerbar.append_section(None, section_common_out)
        menu_headerbar.append_section(None, section_danger)
        self.add_widget('menu-headerbar-section-common-in', section_common_in)
        self.add_widget('menu-headerbar-section-common-out', section_common_out)
        self.add_widget('menu-headerbar-section-common-danger', section_danger)

        # Actions in
        menuitem = self.factory.create_menuitem('settings_app', 'Application settings', self._handle_menu, None, [])
        section_common_in.append_item(menuitem)

        # Actions out
        menuitem = self.factory.create_menuitem('help', 'Help', self._handle_menu, None, ["<Control>h", "<Control>H"])
        section_common_out.append_item(menuitem)
        menuitem = self.factory.create_menuitem('about', 'About', self._handle_menu, None, [])
        section_common_out.append_item(menuitem)

        # Actions danger
        menuitem = self.factory.create_menuitem('quit', 'Quit', self._handle_menu, None, ["<Control>q", "<Control>Q"])
        section_danger.append_item(menuitem)

        menubutton = self.factory.create_button_menu(icon_name='miaz-system-menu', menu=menu_headerbar)
        menubutton.set_always_show_arrow(False)
        self.add_widget('headerbar-menubutton-app', menubutton)
        self.header.pack_start(menubutton)

    def _setup_headerbar_right(self):
        pass

    def _setup_headerbar_center(self):
        pass

    def _setup_gui(self):
        # Widgets
        ## HeaderBar
        self.header = self.add_widget('headerbar', Adw.HeaderBar())

        ## Central Box
        self.mainbox = self.factory.create_box_vertical(vexpand=True)
        self.win.set_child(self.mainbox)

        ## Stack & Stack.Switcher
        stack = self.add_widget('stack', self._setup_stack())
        self.mainbox.append(stack)

        # Setup headerbar
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()
        self.win.set_titlebar(self.header)

        # Create system pages
        self._setup_page_about()
        self._setup_page_welcome()
        self._setup_page_help()
        self._setup_page_app_settings()

    def check_repository(self):
        repo = self.backend.repo_config()
        try:
            dir_repo = repo['dir_docs']
            self.log.debug("Repo? '%s'", dir_repo)
            if self.backend.repo_validate(dir_repo):
                self.backend.repo_load(dir_repo)
                self._setup_page_workspace()
                self._setup_page_rename()
                self._setup_page_repo_settings()
                valid = True
            else:
                valid = False
        except KeyError as error:
            self.log.debug("No repository active in the configuration")
            self.show_stack_page_by_name('welcome')
            valid = False
        self.win.present()
        return valid

    def _handle_menu(self, action, *args):
        name = action.props.name
        if name == 'settings_app':
            self.show_stack_page_by_name('settings_app')
        elif name == 'about':
            self.show_stack_page_by_name('about')
        elif name == 'close':
            self.quit()
        elif name == 'view':
            self.workspace.document_display()
        elif name == 'rename':
            self.workspace.document_rename()
        elif name == 'help':
            self.show_stack_page_by_name('help')
        elif name == 'quit':
            self.exit_app()

    def get_stack_page_by_name(self, name: str) -> Adw.ViewStackPage:
        widget = self.stack.get_child_by_name(name)
        return self.stack.get_page(widget)

    def get_stack_page_widget_by_name(self, name:str) -> Gtk.Widget:
        return self.stack.get_child_by_name(name)

    def show_stack_page_by_name(self, name: str = 'workspace'):
        self.stack.set_visible_child_name(name)

    def exit_app(self, *args):
        self.quit()

    def add_widget(self, name: str, widget: Gtk.Widget) -> Gtk.Widget:
        if name not in self._widget:
            self._widget[name] = widget
            return widget
        else:
            self.log.error("A widget with name '%s' already exists", name)

    def get_widget(self, name):
        try:
            return self._widget[name]
        except KeyError:
            return None

    def get_widgets(self):
        return self._widget


