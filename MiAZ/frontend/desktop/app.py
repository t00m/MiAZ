#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontent/Desktop entry point
"""

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.pluginsystem import MiAZPluginManager, MiAZPluginType
from MiAZ.frontend.desktop.services.icm import MiAZIconManager
from MiAZ.frontend.desktop.services.factory import MiAZFactory
from MiAZ.frontend.desktop.services.actions import MiAZActions
from MiAZ.frontend.desktop.widgets.mainwindow import MiAZMainWindow
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings
from MiAZ.frontend.desktop.widgets.welcome import MiAZWelcome
from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.repository import MiAZRepository
from MiAZ.backend.config import MiAZConfigRepositories

class MiAZApp(Gtk.Application):
    __gsignals__ = {
        "start-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "exit-application":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    plugins_loaded = False
    _miazobjs = {}  # MiAZ Objects
    _config = {}    # Dictionary holding configurations

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._miazobjs['widgets'] = {}
        self._miazobjs['services'] = {}
        self.log = self._miazobjs['services']['log'] = MiAZLog("MiAZ.App")
        self._env = None
        self.conf = None
        self.app = None
        self.plugin_manager = None
        # ~ self.log = self.add_service('log', MiAZLog("MiAZ.App"))

    def get_config_dict(self):
        return self._config

    def set_env(self, ENV: dict):
        self._env = ENV
        # ~ self.log = self.add_service('log', MiAZLog("MiAZ.App"))
        self.log.debug("Starting MiAZ")
        self.add_service('util', MiAZUtil(self))
        self._config['App'] = MiAZConfigApp(self)
        self._config['Repository'] = MiAZConfigRepositories(self)
        # ~ self.add_service('repo', MiAZRepository(self))
        # ~ self.add_service('icons', MiAZIconManager(self))
        self.conf = self.get_config_dict()
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self._on_activate)

    def get_env(self):
        return self._env

    def _on_activate(self, app):
        self.app = app
        self.add_service('repo', MiAZRepository(self))
        self.add_service('icons', MiAZIconManager(self))
        self.add_service('factory', MiAZFactory(self))
        self.add_service('actions', MiAZActions(self))
        self._setup_ui()
        self._setup_plugin_manager()
        self.log.debug("Executing MiAZ Desktop mode")
        self.check_repository()
        # ~ repository = self.get_service('repo')

    def _setup_ui(self):
        window = self.add_widget('window', Gtk.ApplicationWindow(application=self))
        window.set_default_size(1280, 800)
        window.set_icon_name('MiAZ')
        window.connect('close-request', self._on_window_close_request)
        window.set_default_icon_name('MiAZ')
        mainbox = self.add_widget('window-mainbox', MiAZMainWindow(self))
        window.set_child(mainbox)
        self._setup_page_welcome()
        # ~ self._setup_page_workspace()

    def _on_window_close_request(self, *args):
        self.log.debug("Close application requested")
        actions = self.get_service('actions')
        actions.exit_app()

    def _finish_configuration(self, *args):
        self.log.debug("Finish loading app")

    def _load_plugins(self):
        workspace = self.get_widget('workspace')
        workspace_loaded = workspace is not None

        # Load System Plugins
        if workspace_loaded and not self.plugins_loaded:
            self.log.debug("Loading system plugins...")
            plugin_manager = self.get_service('plugin-manager')
            np = 0 # Number of system plugins
            ap = 0   # system plugins activated
            for plugin in self.plugin_manager.plugins:
                try:
                    ptype = plugin_manager.get_plugin_type(plugin)
                    if ptype == MiAZPluginType.SYSTEM:
                        if not plugin.is_loaded():
                            plugin_manager.load_plugin(plugin)
                            ap += 1
                except Exception as error:
                    self.log.error(error)
                if ptype == MiAZPluginType.SYSTEM:
                    np += 1
            self.plugins_loaded = True
            self.log.debug("System plugins loaded: %d/%d", ap, np)

            # Load User Plugins
            self.log.debug("Loading user plugins for this repository...")
            conf = self.get_config_dict()
            plugins = conf['Plugin']
            np = 0 # Number of user plugins
            ap = 0   # user plugins activated
            for plugin in self.plugin_manager.plugins:
                try:
                    ptype = plugin_manager.get_plugin_type(plugin)
                    if ptype == MiAZPluginType.USER:
                        pid = plugin.get_module_name()
                        if plugins.exists_used(pid):
                            if not plugin.is_loaded():
                                plugin_manager.load_plugin(plugin)
                                ap += 1
                except Exception as error:
                    self.log.error(error)
                if ptype == MiAZPluginType.USER:
                    np += 1
            self.log.debug("User plugins loaded for this repoitory: %d/%d", ap, np)

    def _setup_plugin_manager(self):
        self.plugin_manager = self.add_service('plugin-manager', MiAZPluginManager(self))


    def get_config(self, name: str):
        try:
            config = self.get_config_dict()
            return config[name]
        except KeyError:
            return None

    def check_repository(self):
        try:
            repository = self.get_service('repo')
            # ~ self.log.debug("Using repo '%s'", repository.docs)
            try:
                if repository.validate(repository.docs):
                    repository.load(repository.docs)

                    # Workspace and Rename widgets can be only loaded
                    # after opening the Repository
                    # FIXME: check this workflow
                    self.log.debug("Setting up workspace")
                    if self.get_widget('workspace') is None:
                        self._setup_page_workspace()
                        workspace = self.get_widget('workspace')
                        workspace.initialize_caches()
                        if not self.plugins_loaded:
                            self._load_plugins()
                    if self.get_widget('rename') is None:
                        self._setup_page_rename()
                    repo_settings = self.get_widget('settings-repo')
                    if repo_settings is None:
                        repo_settings = self.add_widget('settings-repo', MiAZRepoSettings(self))
                    repo_settings.update()
                    actions = self.get_service('actions')
                    actions.show_stack_page_by_name('workspace')
                    valid = True
                    self.emit('start-application-completed')
                else:
                    valid = False
            except Exception:
                self.log.error("Default repository configuration not available")
                valid = False
        except KeyError:
            self.log.debug("No repository active in the configuration")
            actions = self.get_service('actions')
            actions.show_stack_page_by_name('welcome')
            valid = False
        window = self.get_widget('window')
        if window is not None:
            window.present()
        return valid

    def _setup_page_welcome(self):
        stack = self.get_widget('stack')
        widget_welcome = self.get_widget('welcome')
        if widget_welcome is None:
            widget_welcome = self.add_widget('welcome', MiAZWelcome(self))
            page_welcome = stack.add_titled(widget_welcome, 'welcome', 'MiAZ')
            page_welcome.set_icon_name('MiAZ')
            page_welcome.set_visible(True)

    def _setup_page_workspace(self):
        stack = self.get_widget('stack')
        widget_workspace = self.get_widget('workspace')
        if widget_workspace is None:
            widget_workspace = self.add_widget('workspace', MiAZWorkspace(self))
            page_workspace = stack.add_titled(widget_workspace, 'workspace', 'MiAZ')
            page_workspace.set_icon_name('document-properties')
            page_workspace.set_visible(True)
            actions = self.get_service('actions')
            actions.show_stack_page_by_name('workspace')

    def _setup_page_rename(self):
        stack = self.get_widget('stack')
        widget_rename = self.get_widget('rename')
        if widget_rename is None:
            widget_rename = self.add_widget('rename', MiAZRenameDialog(self))
            page_rename = stack.add_titled(widget_rename, 'rename', 'MiAZ')
            page_rename.set_icon_name('document-properties')
            page_rename.set_visible(False)

    def add_service(self, name: str, service: GObject.GObject) -> GObject.GObject:
        srv = self.get_service(name)
        if srv is None:
            self._miazobjs['services'][name] = service
            srv = service
            self.log.debug("Adding new service: %s", name)
        return srv


        # ~ print(self._miazobjs['services'])
        # ~ self._miazobjs['services'][name] = service
        # ~ if name in list(self._miazobjs['services'].keys()):
            # ~ self.log.error("A service with name '%s' already exists. It has been replaced", name)
            # ~ print("A service with name '%s' already exists. It has been replaced" % name)
        # ~ return service

    def get_service(self, name):
        try:
            return self._miazobjs['services'][name]
        except KeyError:
            return None

    def add_widget(self, name: str, widget) -> Gtk.Widget or None:
        wdg = self.get_widget(name)
        if wdg is not None:
            self.log.debug("Widget '%s' will be overwritten", name)
        wdg = self._miazobjs['widgets'][name] = widget

        return wdg


        # Add widget, but do not overwrite
        # ~ if name in self._miazobjs['widgets']:
            # ~ self.log.warning("A widget with name '%s' already exists. Overwriten", name)
        # ~ self._miazobjs['widgets'][name] = widget
        # ~ return widget

    # ~ def set_widget(self, name: str, widget):
        # ~ # Overwrite existing widget
        # ~ self._miazobjs['widgets'][name] = widget
        # ~ return widget

    def get_widget(self, name):
        try:
            return self._miazobjs['widgets'][name]
        except KeyError:
            return None

    def remove_widget(self, name: str):
        """
        Remove widget name from dictionary.
        They widget is not destroyed. It must be done by the developer.
        This method is mostly useful during plugins unloading.
        """
        deleted = False
        try:
            del self._miazobjs['widgets'][name]
            deleted = True
        except KeyError:
            self.log.error("Widget '%s' doesn't exists", name)
        return deleted

    def get_logger(self):
        return self.log
