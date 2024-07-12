#!/usr/bin/python3
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontent/Desktop entry point


from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.pluginsystem import MiAZPluginManager, MiAZPluginType
from MiAZ.frontend.desktop.services.icm import MiAZIconManager
from MiAZ.frontend.desktop.services.factory import MiAZFactory
from MiAZ.frontend.desktop.services.actions import MiAZActions
from MiAZ.frontend.desktop.services.dialogs import MiAZDialog
from MiAZ.frontend.desktop.widgets.mainwindow import MiAZMainWindow
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings
from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.repository import MiAZRepository
from MiAZ.backend.config import MiAZConfigRepositories
from MiAZ.backend.status import MiAZStatus
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.projects import MiAZProject


class MiAZApp(Gtk.Application):
    """MiAZ Gtk Application class."""

    __gsignals__ = {
        "start-application-completed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "exit-application": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    plugins_loaded = False
    _miazobjs = {}  # MiAZ Objects
    _config = {}    # Dictionary holding configurations
    _status = MiAZStatus.BUSY

    def __init__(self, **kwargs):
        """Set up env, UI and services used by the rest of modules."""
        super().__init__(**kwargs)
        self._miazobjs['widgets'] = {}
        self._miazobjs['services'] = {}
        self._miazobjs['actions'] = {}
        self.log = self._miazobjs['services']['log'] = MiAZLog("MiAZ.App")
        self.set_service('util', MiAZUtil(self))
        self.set_service('icons', MiAZIconManager(self))
        self.set_service('factory', MiAZFactory(self))
        self.set_service('actions', MiAZActions(self))
        self.set_service('dialogs', MiAZDialog(self))
        repository = self.set_service('repo', MiAZRepository(self))
        repository.connect('repository-switched', self.switch_finish)
        self._env = None
        self.conf = None
        self.app = None

    def get_status(self):
        """Return current app status.

        Statuses defined in the class MiAZStatus (backend mod. status.)
        """
        return self._status

    def set_status(self, status: MiAZStatus):
        """
        Set current application status.

        Normal status is RUNNING.
        BUSY status is used when the UI is being updated. Because there
        are many widgets listening to config changes, it is very useful
        to avoid updating workspace view repeteadly.
        """
        self._status = status

    def get_config_dict(self):
        return self._config

    def set_env(self, ENV: dict):
        """Receive and set the environment when the app is launched.

        Once MiAZ gets the environment, it starts loading basic config.
        """
        self._env = ENV
        self._config['App'] = MiAZConfigApp(self)
        self._config['Repository'] = MiAZConfigRepositories(self)
        self.conf = self.get_config_dict()
        self.connect('activate', self._on_activate)
        GLib.set_application_name(ENV['APP']['name'])

    def get_env(self):
        """Return current environment dictionary."""
        return self._env

    def _on_activate(self, app):
        """Start application workflow.

        As soon as the the application become active, the app workflow
        is started.
        """
        self.app = app
        self._setup_ui()
        self.set_service('plugin-manager', MiAZPluginManager(self))
        self.switch_start()
        self.log.debug("Executing MiAZ Desktop mode")

    def _setup_ui(self):
        """Set up main application window."""
        ENV = self.get_env()

        # Main MiAZ Window
        window = self.add_widget('window', Gtk.ApplicationWindow(application=self))
        window.set_default_size(1280, 800)
        window.set_icon_name('com.github.t00m.MiAZ')
        window.connect('close-request', self._on_window_close_request)
        window.set_default_icon_name('com.github.t00m.MiAZ')

        # Theme
        theme = self.set_service('theme', Gtk.IconTheme.get_for_display(window.get_display()))
        theme.add_search_path(ENV['GPATH']['ICONS'])
        theme.add_search_path(ENV['GPATH']['FLAGS'])
        self.log.debug(f"MiAZ custom icons in: {ENV['GPATH']['ICONS']}")

        # Setup main window contents
        mainbox = self.add_widget('window-mainbox', MiAZMainWindow(self))
        window.set_child(mainbox)

        # FIXME: Setup menu bar
        menubar = self.get_widget('window-menu-app')
        self.set_menubar(menubar)

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
            np = 0  # Number of system plugins
            ap = 0  # system plugins activated
            for plugin in plugin_manager.plugins:
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
            np = 0  # Number of user plugins
            ap = 0  # user plugins activated
            for plugin in plugin_manager.plugins:
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

    def get_config(self, name: str):
        try:
            config = self.get_config_dict()
            return config[name]
        except KeyError:
            return None

    def switch_start(self):
        """Switch from one repository to another."""
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
            workspace = self.get_widget('workspace')
            workspace.initialize_caches()
            if not self.plugins_loaded:
                self._load_plugins()
            self.set_status(MiAZStatus.RUNNING)
            actions.show_stack_page_by_name('workspace')
            self.emit('start-application-completed')
        else:
            welcome_widget = self.get_widget('welcome')
            actions.show_stack_page_by_name('welcome')
            window = self.get_widget('window')
            window.present()
        return repo_loaded

    def switch_finish(self, *args):
        """Finish switch repository operation"""
        repository = self.get_service('repo')
        self.set_service('Projects', MiAZProject(self))
        watcher = MiAZWatcher()
        watcher.set_path(repository.docs)
        watcher.set_active(active=True)
        self.app.set_service('watcher', watcher)
        self.log.debug("Repository switch finished")

        # Setup stack pages
        mainbox = self.get_widget('window-mainbox')
        page_rename = self.get_widget('rename')
        if page_rename is None:
            mainbox._setup_page_rename()
        page_workspace = self.get_widget('workspace')
        if page_workspace is None:
            mainbox._setup_page_workspace()

    def set_service(self, name: str, service: GObject.GObject) -> GObject.GObject:
        """Add a service to internal MiAZ objects dictionary."""
        srv = self.get_service(name)
        if srv is None:
            self._miazobjs['services'][name] = service
            srv = service
            # ~ self.log.debug(f"Adding new service: {name}")
        return srv

    def get_service(self, name):
        """Return a service from the MiAZ objects dictionary."""
        try:
            return self._miazobjs['services'][name]
        except KeyError:
            return None

    def add_widget(self, name: str, widget: Gtk.Widget = None) -> Gtk.Widget or None:
        """Add widget to internal MiAZ objects dictionary."""
        self._miazobjs['widgets'][name] = widget
        return widget

    def get_widget(self, name):
        """Return a widget from the MiAZ objects dictionary."""
        try:
            return self._miazobjs['widgets'][name]
        except KeyError:
            return None

    def remove_widget(self, name: str):
        """
        Remove widget from dictionary.

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
