#!/usr/bin/python3

"""
# File: pluginsystem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: a Plugin System based on LibPeas
# Code borrowed and adapted from Orca project:
# https://github.com/chrys87/orca-plugin/blob/plugin_system/src/orca/plugin_system_manager.py
"""

import os
import sys
import zipfile
from enum import IntEnum
from gettext import gettext as _

import gi
gi.require_version('Peas', '1.0')
from gi.repository import GObject, Peas

from MiAZ.backend.log import MiAZLog


class MiAZAPI(GObject.GObject):
    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app


class MiAZPluginType(IntEnum):
    """Types of plugins depending on their directory location."""

    SYSTEM = 1
    USER = 2

    def __str__(self):
        if self.value == MiAZPluginType.USER:
            return _("User Plugin")
        elif self.value == MiAZPluginType.SYSTEM:
            return _("System Plugin")


class MiAZPluginManager(GObject.GObject):
    def __init__(self, app):
        super().__init__()
        GObject.signal_new('plugins-updated',
                            MiAZPluginManager,
                            GObject.SignalFlags.RUN_LAST, None, ())
        self.log = MiAZLog('MiAZ.PluginManager')
        self.app = app
        self.util = self.app.get_service('util')
        self.log.trace("Initializing Plugin Manager")
        self.plugin_info_list = []

        self.engine = Peas.Engine.get_default()
        for loader in ("python3", ):
            self.engine.enable_loader(loader)

        self._setup_plugins_dir()
        self._setup_extension_set()

    def import_plugin(self, plugin_path):
        """
        Import plugin in the user space.
        "A plugin zip file is valid if:
        - Contains at least 2 files
          - Their names are identical
          - Extensions are .plugin and .py
          - Their names are the same than the plugin name
        - Optionally, a directory named resources
          - with a subdirectory with the same name as the plugin

        Eg.:
        hello.zip
        ├── hello.plugin
        ├── hello.py
        └── resources
            └── hello
                └── css
                    └── noprint.css
        """
        utils = self.app.get_service('util')
        valid = False
        azip = zipfile.ZipFile(plugin_path)
        plugin_name, plugin_ext = utils.filename_details(plugin_path)
        plugin_code = f"{plugin_name}.py"
        plugin_meta = f"{plugin_name}.plugin"
        plugin_code_exist = plugin_code in azip.namelist()
        plugin_meta_exist = plugin_meta in azip.namelist()
        if plugin_code_exist and plugin_meta_exist:
             valid = True

        if valid:
            ENV = self.app.get_env()
            azip.extractall(ENV['LPATH']['PLUGINS'])
            self.engine.rescan_plugins()
            config = self.app.get_config('Plugin')
            config.add_available(key=plugin_name)
            plugin_fname = os.path.basename(plugin_path)
            self.log.debug(f"Plugin '{plugin_fname}' added to '{ENV['LPATH']['PLUGINS']}'")
        # ~ self.emit('plugins-updated')
        return valid

    def remove_plugin(self, plugin: Peas.PluginInfo):
        """Remove plugin for user space plugins"""
        config = self.app.get_config('Plugin')
        module = plugin.get_module_name()
        if not config.exists_used(module):
            self.log.debug(f"Plugin '{module}' is not being used and will be deleted")
            utils = self.app.get_service('util')
            ENV = self.app.get_env()
            self.unload_plugin(plugin)
            plugin_head = os.path.join(ENV['LPATH']['PLUGINS'], f'{module}.plugin')
            plugin_body = os.path.join(ENV['LPATH']['PLUGINS'], f'{module}.py')
            os.unlink(plugin_head)
            os.unlink(plugin_body)
            plugin_res = os.path.join(ENV['LPATH']['PLUGRES'], module)
            utils.directory_remove(plugin_res)
            config.remove_available(key=module)
            return True
        else:
            self.log.warning(f"Plugin {module} can't be deleted because it is still in use")
            return False

    def rescan_plugins(self):
        try:
            self.engine.rescan_plugins()
            self.emit('plugins-updated')
        except TypeError:
            # Plugin system not initialized yet
            pass

    def load_plugin(self, plugin: Peas.PluginInfo) -> bool:
        ptype = self.get_plugin_type(plugin)
        pname = plugin.get_name()
        pvers = plugin.get_version()
        # ~ pinfo = self.get_plugin_info(plugin)
        try:
            self.engine.load_plugin(plugin)

            if plugin.is_loaded():
                self.log.info(f"Plugin {pname} v{pvers} ({ptype}) loaded")
                return True
            else:
                self.log.error(f"Plugin {pname} v{pvers} ({ptype}) couldn't be loaded")
                return False
        except Exception as error:
            self.log.error(error)
            self.log.error("Plugin {pname} v{pvers} ({ptype}) couldn't be loaded")
            return False

    def unload_plugin(self, plugin: Peas.PluginInfo):
        try:
            ptype = self.get_plugin_type(plugin)
            pname = plugin.get_name()
            pvers = plugin.get_version()
            self.engine.unload_plugin(plugin)
            self.log.info(f"Plugin  {pname} v{pvers} ({ptype}) unloaded")
        except Exception as error:
            self.log.error(error)

    def get_engine(self):
        return self.engine

    @property
    def plugins(self):
        """Gets the engine's plugin list."""
        return self.engine.get_plugin_list()

    def get_plugin_type(self, plugin_info):
        """Gets the PluginType for the specified Peas.PluginInfo."""
        ENV = self.app.get_env()
        PLUGIN_DIR = os.path.dirname(plugin_info.get_data_dir())
        is_plugin_user_dir = PLUGIN_DIR == ENV['LPATH']['PLUGINS']
        if is_plugin_user_dir:
            return MiAZPluginType.USER
        else:
            return MiAZPluginType.SYSTEM

    def get_extension(self, module_name: str):
        """Gets the extension identified by the specified name.
        Args:
            module_name (str): The name of the extension.
        Returns:
            The extension if exists. Otherwise, `None`.
        """
        plugin = self.get_plugin_info(module_name)
        if not plugin:
            return None

        return self.extension_set.get_extension(plugin)

    def get_plugin_info(self, module_name: str):
        """Gets the plugin info for the specified plugin name.
        Args:
            module_name (str): The name from the .plugin file of the module.
        Returns:
            Peas.PluginInfo: The plugin info if it exists. Otherwise, `None`.
        """
        for plugin in self.plugins:
            if plugin.get_module_name() == module_name:
                return plugin
        return None

    def _setup_extension_set(self):
        plugin_iface = MiAZAPI(self.app)

        self.extension_set = Peas.ExtensionSet.new(self.engine,
                                                   Peas.Activatable,
                                                   ["object"],
                                                   [plugin_iface])
        self.extension_set.connect("extension-removed",
                                   self.__extension_removed_cb)

        self.extension_set.connect("extension-added",
                                   self.__extension_added_cb)

    def _setup_plugins_dir(self):
        """Set System and User plugins directories"""
        # System plugins
        # Mandatory set of plugins for every repository
        ENV = self.app.get_env()
        if os.path.exists(ENV['GPATH']['PLUGINS']):
            self.engine.add_search_path(ENV['GPATH']['PLUGINS'])
            self.log.debug(f"Added System plugin dir: {ENV['GPATH']['PLUGINS']}")
        else:
            self.log.error("System plugins directory doesn not exist!")
            self.log.error(f"{ENV['GPATH']['PLUGINS']}")
            self.log.error("Make sure the installation is correct")
            self.log.error("MiAZ will exit now!")
            sys.exit()

        # User plugins
        # All user space plugins are available for all repositories
        # However, each repository can use none, any or all of them
        if not os.path.exists(ENV['LPATH']['PLUGINS']):
            os.makedirs(ENV['LPATH']['PLUGINS'], exist_ok=True)
        self.engine.add_search_path(ENV['LPATH']['PLUGINS'])
        self.log.debug(f"Added user plugins dir: {ENV['LPATH']['PLUGINS']}")

    @staticmethod
    def __extension_removed_cb(unused_set, unused_plugin_info, extension):
        extension.deactivate()

    @staticmethod
    def __extension_added_cb(unused_set, unused_plugin_info, extension):
        extension.activate()
