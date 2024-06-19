#!/usr/bin/python3

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
from MiAZ.backend.status import MiAZStatus


class MiAZApp(Gtk.Application):
    __gsignals__ = {
        "start-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "exit-application":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    plugins_loaded = False
    _miazobjs = {}  # MiAZ Objects
    _config = {}    # Dictionary holding configurations
    _status = MiAZStatus.BUSY

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._miazobjs['widgets'] = {}
        self._miazobjs['services'] = {}
        self._miazobjs['actions'] = {}
        self.log = self._miazobjs['services']['log'] = MiAZLog("MiAZ.App")
        self.add_service('icons', MiAZIconManager(self))
        self.add_service('factory', MiAZFactory(self))
        self.add_service('actions', MiAZActions(self))
        self._env = None
        self.conf = None
        self.app = None
        self.plugin_manager = None

    def get_status(self):
        return self._status

    def set_status(self, status: MiAZStatus):
        self._status = status

    def get_config_dict(self):
        return self._config

    def set_env(self, ENV: dict):
        self._env = ENV
        self.log.debug("Starting MiAZ")
        self.add_service('util', MiAZUtil(self))
        self._config['App'] = MiAZConfigApp(self)
        self._config['Repository'] = MiAZConfigRepositories(self)
        self.conf = self.get_config_dict()
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self._on_activate)

    def get_env(self):
        return self._env

    def _on_activate(self, app):
        self.app = app
        self.add_service('repo', MiAZRepository(self))
        self._setup_ui()
        menubar = self.get_widget('window-menu-app')
        self.set_menubar(menubar)
        self._setup_plugin_manager()
        self.switch()
        self.log.debug("Executing MiAZ Desktop mode")

    def _setup_ui(self):
        """
        """
        ENV = self.get_env()

        # Main MiAZ Window
        window = self.add_widget('window', Gtk.ApplicationWindow(application=self))
        window.set_default_size(1280, 800)
        window.set_icon_name('MiAZ')
        window.connect('close-request', self._on_window_close_request)
        window.set_default_icon_name('MiAZ')

        # Theme
        theme = self.add_service('theme', Gtk.IconTheme.get_for_display(window.get_display()))
        theme.add_search_path(ENV['GPATH']['ICONS'])
        theme.add_search_path(ENV['GPATH']['FLAGS'])
        self.log.debug(f"MiAZ custom icons in: {ENV['GPATH']['ICONS']}")

        # Setup main window contents
        mainbox = self.add_widget('window-mainbox', MiAZMainWindow(self))
        window.set_child(mainbox)

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
            self.log.debug(f"System plugins loaded: {ap}/{np}")

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
            self.log.debug(f"User plugins loaded for this repoitory: {ap}/{np}")

    def _setup_plugin_manager(self):
        self.plugin_manager = self.add_service('plugin-manager', MiAZPluginManager(self))

    def get_config(self, name: str):
        try:
            config = self.get_config_dict()
            return config[name]
        except KeyError:
            return None

    def switch(self):
        self.log.debug("Repository switch requested")
        actions = self.get_service('actions')
        repository = self.get_service('repo')
        try:
            self.set_status(MiAZStatus.BUSY)
            appconf = self.get_config('App')
            repo_loaded = False
            if repository.validate(repository.docs):
                repository.load(repository.docs)
                repo_loaded = True
        except Exception:
            repo_loaded = False

        repo_id = appconf.get('current')
        self.log.debug(f"Repository '{repo_id}' loaded? {repo_loaded}")

        if repo_loaded:
            self.log.debug(f"Repo Working directory: '{repository.docs}")
            repo_settings = self.get_widget('settings-repo')
            if repo_settings is None:
                repo_settings = self.add_widget('settings-repo', MiAZRepoSettings(self))
                repo_settings.update()
            if self.get_widget('rename') is None:
                self._setup_page_rename()
            workspace = self._setup_page_workspace()
            workspace.initialize_caches()
            if not self.plugins_loaded:
                self._load_plugins()
            self.set_status(MiAZStatus.RUNNING)
            actions.show_stack_page_by_name('workspace')
            self.emit('start-application-completed')
        else:
            self.log.debug(f"Error loading repo {repo_id} of type {type(repo_id)}")
            if repo_id is None:
                welcome_widget = self.get_widget('welcome')
                if welcome_widget is None:
                    self._setup_page_welcome()
                actions.show_stack_page_by_name('welcome')
                window = self.get_widget('window')
                window.present()
        return repo_loaded

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
        return widget_workspace

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
            self.log.debug(f"Adding new service: {name}")
        return srv

    def get_service(self, name):
        try:
            return self._miazobjs['services'][name]
        except KeyError:
            return None

    def add_widget(self, name: str, widget) -> Gtk.Widget or None:
        wdg = self.get_widget(name)
        if wdg is not None:
            self.log.debug(f"Widget '{name}' will be overwritten")
        wdg = self._miazobjs['widgets'][name] = widget
        return wdg

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
            self.log.error(f"Widget '{name}' doesn't exists")
        return deleted

    def get_logger(self):
        return self.log
