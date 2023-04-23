#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontent/Desktop entry point
"""

import sys
from gettext import gettext as _

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
from MiAZ.frontend.desktop.widgets.statusbar import MiAZStatusbar
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.factory import MiAZFactory
from MiAZ.frontend.desktop.actions import MiAZActions
from MiAZ.frontend.desktop.help import MiAZHelp
from MiAZ.backend.pluginsystem import MiAZPluginManager

Adw.init()

class MiAZApp(Adw.Application):
    __gsignals__ = {
        "start-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "stop-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    plugins_loaded = False
    _miazobjs = {} # MiAZ Objects

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log = get_logger("MiAZ.GUI")
        self._miazobjs['widgets'] = {}
        self._miazobjs['services'] = {}
        self.backend = self.add_service('backend', MiAZBackend())
        self.add_service('util', self.backend.util)
        self.add_service('stats', self.backend.stats)
        self.add_service('icons', MiAZIconManager(self))
        self.conf = self.backend.conf
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self._on_activate)

    def _on_activate(self, app):
        self.win = self.add_widget('window', Gtk.ApplicationWindow(application=self))
        self.win.set_default_size(1024, 728)
        self.win.set_icon_name('MiAZ')
        self.win.set_default_icon_name('MiAZ')
        self.icman = self.add_service('icman', MiAZIconManager(self))
        self.theme = self.add_service('theme', Gtk.IconTheme.get_for_display(self.win.get_display()))
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.factory = self.add_service('factory', MiAZFactory(self))
        self.actions = self.add_service('actions', MiAZActions(self))
        self._setup_gui()
        self._setup_event_listener()
        self._setup_plugin_manager()
        self.log.debug("Executing MiAZ Desktop mode")
        self.check_repository()
        self.backend.connect('repository-switched', self._update_repo_settings)

    def _update_repo_settings(self, *args):
        self.log.debug("Repo switched. Configuration switched")
        widget_settings_repo = self.get_widget('settings-repo')
        # ~ label_repo = self.get_widget('label_repo')
        if widget_settings_repo is not None:
            self.stack.remove(widget_settings_repo)
            self.remove_widget('settings-repo')
            self._setup_page_repo_settings()
        repo_active = self.conf['App'].get('current')

        # ~ label_repo.set_markup(' [<b>%s</b>] ' % repo_active.replace('_', ' '))

    def _finish_configuration(self, *args):
        self.log.debug("Finish loading app")

    def load_plugins(self):
        workspace = self.get_widget('workspace')
        workspace_loaded = workspace is not None
        if workspace_loaded and not self.plugins_loaded:
            self.log.debug("Loading plugins...")
            plugin_manager = self.get_widget('plugin-manager')
            n = 0
            a = 0
            for plugin in self.plugin_manager.plugins:
                try:
                    plugin_manager.load_plugin(plugin)
                    a += 1
                except Exception as error:
                    self.log.error(error)
                n += 1
            self.plugins_loaded = True
            self.log.debug("Plugins loaded: %d/%d", a, n)

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
            self.show_workspace()

    def get_config(self, name: str):
        return self.backend.conf[name]

    def _setup_stack(self):
        self.stack = self.add_widget('stack', Adw.ViewStack())
        self.switcher = self.add_widget('switcher', Adw.ViewSwitcher())
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
        widget_settings_app = self.get_widget('settings-app')
        if widget_settings_app is None:
            widget_settings_app = self.add_widget('settings-app', MiAZAppSettings(self))
            page_settings_app = self.stack.add_titled(widget_settings_app, 'settings_app', 'MiAZ')
            page_settings_app.set_icon_name('document-properties')
            page_settings_app.set_visible(False)

    def _setup_page_repo_settings(self):
        widget_settings_repo = self.get_widget('settings-repo')
        if widget_settings_repo is None:
            widget_settings_repo = self.add_widget('settings-repo', MiAZRepoSettings(self))
            page_settings_repo = self.stack.add_titled(widget_settings_repo, 'settings_repo', 'MiAZ')
            page_settings_repo.set_icon_name('document-properties')
            page_settings_repo.set_visible(False)

    def _setup_page_workspace(self):
        widget_workspace = self.get_widget('workspace')
        if widget_workspace is None:
            widget_workspace = self.add_widget('workspace', MiAZWorkspace(self))
            page_workspace = self.stack.add_titled(widget_workspace, 'workspace', 'MiAZ')
            page_workspace.set_icon_name('document-properties')
            page_workspace.set_visible(True)
            self.show_stack_page_by_name('workspace')

    def _setup_page_rename(self):
        widget_rename = self.get_widget('rename')
        if widget_rename is None:
            widget_rename = self.add_widget('rename', MiAZRenameDialog(self))
            page_rename = self.stack.add_titled(widget_rename, 'rename', 'MiAZ')
            page_rename.set_icon_name('document-properties')
            page_rename.set_visible(False)

    def _setup_menu_app(self):
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
        menuitem = self.factory.create_menuitem('settings_app', _('Application settings'), self._handle_menu, None, [])
        section_common_in.append_item(menuitem)

        # Actions out
        menuitem = self.factory.create_menuitem('help', _('Help'), self._handle_menu, None, ["<Control>h", "<Control>H"])
        section_common_out.append_item(menuitem)
        menuitem = self.factory.create_menuitem('about', _('About'), self._handle_menu, None, [])
        section_common_out.append_item(menuitem)

        # Actions danger
        menuitem = self.factory.create_menuitem('quit', _('Quit'), self._handle_menu, None, ["<Control>q", "<Control>Q"])
        section_danger.append_item(menuitem)

        menubutton = self.factory.create_button_menu(icon_name='miaz-system-menu', menu=menu_headerbar)
        menubutton.set_always_show_arrow(False)
        self.add_widget('app-menu-system', menubutton)
        # ~ self.header.pack_start(menubutton)

    def show_workspace(self, *args):
        self.show_stack_page_by_name('workspace')
        button = self.get_widget('app-header-button-back')
        button.set_visible(False)

    def _setup_headerbar_left(self):
        headerbar = self.get_widget('headerbar')
        btnmenu = self.get_widget('app-menu-system')
        headerbar.pack_start(btnmenu)

    def _setup_headerbar_right(self):
        pass
        # ~ label_repo = self.add_widget('label_repo', Gtk.Label())
        # ~ repo_active = self.conf['App'].get('current')
        # ~ label_repo.set_markup(' [<b>%s</b>] ' % repo_active.replace('_', ' '))
        # ~ self.header.pack_end(label_repo)

    def _setup_headerbar_center(self):
        pass

    def _setup_gui(self):
        # Widgets
        ## HeaderBar
        headerbar = self.add_widget('headerbar', Adw.HeaderBar())
        self.win.set_titlebar(headerbar)

        ## Central Box
        self.mainbox = self.factory.create_box_vertical(vexpand=True)
        self.win.set_child(self.mainbox)

        ## Stack & Stack.Switcher
        stack = self._setup_stack()
        self.mainbox.append(stack)

        # Setup system menu
        self._setup_menu_app()

        # Setup headerbar
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()

        # Create system pages
        self._setup_page_about()
        self._setup_page_welcome()
        self._setup_page_help()
        self._setup_page_app_settings()

        # Statusbar
        statusbar = self.add_widget('statusbar', MiAZStatusbar(self))
        self.mainbox.append(statusbar)

    def check_repository(self):
        repo = self.backend.repo_config()
        try:
            dir_repo = repo['dir_docs']
            self.log.debug("Repo? '%s'", dir_repo)
            if self.backend.repo_validate(dir_repo):
                self.backend.repo_load(dir_repo)
                if self.get_widget('workspace') is None:
                    self._setup_page_workspace()
                    if not self.plugins_loaded:
                        self.load_plugins()
                if self.get_widget('rename') is None:
                    self._setup_page_rename()
                if self.get_widget('settings-repo') is None:
                    self._setup_page_repo_settings()
                self.show_stack_page_by_name('workspace')
                valid = True
                statusbar = self.get_widget('statusbar')
                name = self.conf['App'].get('current')
                statusbar.repo(name)
                statusbar.message("Repository loaded")
                self.emit('start-application-completed')
            else:
                valid = False
        except KeyError as error:
            self.log.debug("No repository active in the configuration")
            self.show_stack_page_by_name('welcome')
            valid = False
        window = self.get_widget('window')
        if window is not None:
            window.present()
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
        button = self.get_widget('app-header-button-back')
        if name not in ['welcome', 'workspace']:
            button.set_visible(True)
        else:
            button.set_visible(False)


    def exit_app(self, *args):
        self.emit("stop-application-completed")
        self.quit()

    def add_service(self, name: str, service) -> Gtk.Widget:
        if name not in self._miazobjs['services']:
            self._miazobjs['services'][name] = service
            return service
        else:
            self.log.error("A service with name '%s' already exists", name)

    def add_widget(self, name: str, widget):
        # Add widget, but do not overwrite
        if name not in self._miazobjs['widgets']:
            self._miazobjs['widgets'][name] = widget
            return widget
        else:
            self.log.error("A widget with name '%s' already exists", name)

    def set_widget(self, name: str, widget):
        # Overwrite existing widget
        if name in self._miazobjs['widgets']:
            self._miazobjs['widgets'][name] = widget
            return widget
        else:
            self.log.error("A widget with name '%s' doesn't exists", name)

    def get_widget(self, name):
        try:
            return self._miazobjs['widgets'][name]
        except KeyError:
            return None

    def get_service(self, name):
        try:
            return self._miazobjs['services'][name]
        except KeyError:
            return None

    def get_widgets(self):
        return self._miazobjs['widgets']

    def remove_widget(self, name: str):
        deleted = False
        try:
            del(self._miazobjs['widgets'][name])
            deleted = True
        except KeyError:
            self.log.error("Widget '%s' doesn't exists", name)
        return deleted

