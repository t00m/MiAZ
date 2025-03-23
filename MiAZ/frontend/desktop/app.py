#!/usr/bin/python3
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontent/Desktop entry point

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gtk


from MiAZ.backend.log import MiAZLog
from MiAZ.backend.pluginsystem import MiAZPluginManager, MiAZPluginType
from MiAZ.frontend.desktop.services.icm import MiAZIconManager
from MiAZ.frontend.desktop.services.factory import MiAZFactory
from MiAZ.frontend.desktop.services.actions import MiAZActions
from MiAZ.frontend.desktop.services.dialogs import MiAZDialog
from MiAZ.frontend.desktop.services.workflow import MiAZWorkflow
from MiAZ.frontend.desktop.widgets.mainwindow import MiAZMainWindow

from MiAZ.backend.util import MiAZUtil
from MiAZ.backend.config import MiAZConfigApp
from MiAZ.backend.repository import MiAZRepository
from MiAZ.backend.config import MiAZConfigRepositories
from MiAZ.backend.status import MiAZStatus



class MiAZApp(Adw.Application):
    """MiAZ Gtk Application class."""

    __gsignals__ = {
        "start-application-completed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "exit-application": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    _plugins_loaded = False
    _miazobjs = {}  # MiAZ Objects
    _config = {}    # Dictionary holding configurations
    _status = MiAZStatus.BUSY

    def __init__(self, **kwargs):
        """Set up env, UI and services used by the rest of modules."""
        application_id = kwargs['application_id']
        Adw.Application.__init__(self, application_id=application_id)
        # ~ super().__init__(**kwargs)
        self._miazobjs['widgets'] = {}
        self._miazobjs['services'] = {}
        self._miazobjs['actions'] = {}
        self.log = MiAZLog("MiAZ.App")
        self.set_service('util', MiAZUtil(self))
        self.set_service('icons', MiAZIconManager(self))
        self.set_service('factory', MiAZFactory(self))
        self.set_service('actions', MiAZActions(self))
        self.set_service('dialogs', MiAZDialog(self))
        workflow = self.set_service('workflow', MiAZWorkflow(self))
        repository = self.set_service('repo', MiAZRepository(self))
        repository.connect('repository-switched', workflow.switch_finish)
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

        RUNNING: Normal status. Do update the workspace view.
        BUSY: Used to avoid updating the workspace view.
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
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self._on_activate)

    def get_env(self):
        """Return current environment dictionary."""
        return self._env

    def _on_activate(self, app):
        """Start application workflow.

        As soon as the the application become active, the app workflow
        is started.
        """
        self.app = app
        workflow = self.get_service('workflow')
        self.set_service('plugin-manager', MiAZPluginManager(self))
        self._setup_ui()
        workflow.switch_start()
        self.log.debug("Executing MiAZ Desktop mode")

    def _setup_ui(self):
        """Set up main application window."""
        ENV = self.get_env()

        # Main MiAZ Window
        window = self.add_widget('window', Adw.ApplicationWindow(application=self))
        window.set_default_size(1280, 800)
        window.set_icon_name('io.github.t00m.MiAZ')
        window.connect('close-request', self._on_window_close_request)
        window.set_default_icon_name('io.github.t00m.MiAZ')

        # Theme
        theme = self.set_service('theme', Gtk.IconTheme.get_for_display(window.get_display()))
        theme.add_search_path(ENV['GPATH']['ICONS'])
        self.log.debug(f"Add ENV['GPATH']['ICONS'] ({ENV['GPATH']['ICONS']}) to the theme search path")
        theme.add_search_path(ENV['GPATH']['FLAGS'])
        self.log.debug(f"Add ENV['GPATH']['FLAGS'] ({ENV['GPATH']['FLAGS']}) to the theme search path")
        self.log.debug(f"MiAZ custom icons in: {ENV['GPATH']['ICONS']}")

        # Setup main window contents
        mainbox = self.add_widget('window-mainbox', MiAZMainWindow(self))
        window.set_content(mainbox)

        # FIXME: Setup menu bar
        menubar = self.get_widget('window-menu-app')
        self.set_menubar(menubar)

    def _on_window_close_request(self, *args):
        self.log.debug("Close application requested")
        actions = self.get_service('actions')
        actions.exit_app()

    def _finish_configuration(self, *args):
        self.log.debug("Finish loading app")

    def get_plugins_loaded(self):
        return self._plugins_loaded

    def set_plugins_loaded(self, loaded=True):
        return self._plugins_loaded

    def load_plugins(self):
        workspace = self.get_widget('workspace')
        workspace_loaded = workspace is not None

        # Load System Plugins
        if workspace_loaded and not self.get_plugins_loaded():
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
            self.set_plugins_loaded(True)
            self.log.info(f"System plugins loaded: {ap}/{np}")

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
            self.log.info(f"User plugins loaded for this repository: {ap}/{np}")

    def get_config(self, name: str):
        try:
            config = self.get_config_dict()
            return config[name]
        except KeyError:
            return None

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

    def find_widget_by_name(self, parent, name):
        # Start with the first child
        child = parent.get_first_child()


        # Iterate through all children
        while child is not None:
            # Check if the current child has the desired name
            if child.get_name() == name:
                return child

            # Recursively search in the child's children (if it's a container)
            result = self.find_widget_by_name(child, name)
            if result is not None:
                return result

            # Move to the next sibling
            child = child.get_next_sibling()

        # If no matching widget is found, return None
        return None


    def exit(self, *args):
        # Signal handler for CONTROL-C
        self.log.warning("CONTROL-C detected! Exiting gracefully...")
        actions = self.get_service('actions')
        actions.exit_app()  # Quit the GTK main loop
        return True  # Return True to stop further propagation
