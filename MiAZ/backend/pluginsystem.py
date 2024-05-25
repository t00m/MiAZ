#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: pluginsystem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: a Plugin System based on LibPeas
# Code borrowed and adapted from from Orca project:
# https://github.com/chrys87/orca-plugin/blob/plugin_system/src/orca/plugin_system_manager.py
# Adapted for MiAZ
"""

import os
import zipfile
from enum import IntEnum

import gi
gi.require_version('Peas', '1.0')
from gi.repository import GObject, Peas

from MiAZ.backend.log import get_logger


class MiAZAPI(GObject.GObject):
    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app


class MiAZPluginType(IntEnum):
    """Types of plugins depending on their directory location."""

    SYSTEM = 1
    USER = 2

    # ~ def __str__(self):
        # ~ if self.value == MiAZPluginType.USER:
            # ~ return _("User Plugin")
        # ~ elif self.value == MiAZPluginType.SYSTEM:
            # ~ return _("System Plugin")


class MiAZPluginManager(GObject.GObject):
    def __init__(self, app):
        super().__init__()
        GObject.signal_new('plugins-updated',
                            MiAZPluginManager,
                            GObject.SignalFlags.RUN_LAST, None, () )
        self.log = get_logger('MiAZ.PluginManager')
        self.app = app
        self.backend = self.app.get_service('backend')
        self.util = self.app.get_service('util')
        self.log.debug("Initializing Plugin Manager")
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
        - Contains only 2 files
        - Their names are identical
        - Extensions are .plugin and .py
        """
        valid = False
        azip = zipfile.ZipFile(plugin_path)
        files = azip.namelist()
        if len(files) == 2:
            fn1_name, fn1_ext = self.util.filename_details(files[0])
            fn2_name, fn2_ext = self.util.filename_details(files[1])
            if fn1_name == fn2_name:
                if fn1_ext == 'py' and fn2_ext == 'plugin':
                    valid = True
                elif fn1_ext == 'plugin' and fn2_ext == 'py':
                    valid = True
            if valid:
                ENV = self.app.get_env()
                azip.extractall(ENV['LPATH']['PLUGINS'])
                self.engine.rescan_plugins()
                config = self.app.get_config('Plugin')
                config.add_available(key=fn1_name)
                self.log.debug("Plugin '%s' added to '%s'", os.path.basename(plugin_path), ENV['LPATH']['PLUGINS'])
        # ~ self.emit('plugins-updated')
        return valid

    def remove_plugin(self, plugin: Peas.PluginInfo):
        """Remove plugin for user space plugins"""
        # FIXME: Make sure the plugin is deleted and unloaded
        ENV = self.app.get_env()
        module = plugin.get_module_name()
        self.unload_plugin(plugin)
        plugin_head = os.path.join(ENV['LPATH']['PLUGINS'], '%s.plugin' % module)
        plugin_body = os.path.join(ENV['LPATH']['PLUGINS'], '%s.py' % module)
        os.unlink(plugin_head)
        os.unlink(plugin_body)
        config = self.app.get_config('Plugin')
        config.remove_available(key=module)
        # ~ self.emit('plugins-updated')
        return True

    def rescan_plugins(self):
        try:
            self.engine.rescan_plugins()
            self.emit('plugins-updated')
        except TypeError:
            # Plugin system not initialized yet
            pass

    def load_plugin(self, plugin: Peas.PluginInfo) -> bool:
        ptype = self.get_plugin_type(plugin)
        pinfo = self.get_plugin_info(plugin)
        try:
            self.engine.load_plugin(plugin)
            if plugin.is_loaded():
                # ~ self.log.debug("Plugin %s (%s) loaded", plugin.get_name(), ptype)
                return True
            else:
                self.log.error("Plugin %s (%s) couldn't be loaded", plugin.get_name(), ptype)
                return False
        except Exception as error:
            self.log.error(error)
            self.log.error("Plugin %s (%s) couldn't be loaded", plugin.get_name(), ptype)
            return False

    def unload_plugin(self, plugin: Peas.PluginInfo):
        try:
            self.engine.unload_plugin(plugin)
            self.log.debug("Plugin unloaded")
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
        # System plugins
        # Mandatory set of plugins for every repository
        ENV = self.app.get_env()
        if os.path.exists(ENV['GPATH']['PLUGINS']):
            self.engine.add_search_path(ENV['GPATH']['PLUGINS'])
            self.log.debug("Added System plugin dir: %s", ENV['GPATH']['PLUGINS'])

        # GLobal user plugins
        # All user space plugins are available for all repositories
        # However, each repository can use none, any or all of them
        self.add_user_plugins_dir()

    def add_user_plugins_dir(self):
        ENV = self.app.get_env()
        os.makedirs(ENV['LPATH']['PLUGINS'], exist_ok=True)
        self.engine.add_search_path(ENV['LPATH']['PLUGINS'])
        self.log.debug("Added user plugins dir: %s", ENV['LPATH']['PLUGINS'])


    @staticmethod
    def __extension_removed_cb(unused_set, unused_plugin_info, extension):
        extension.deactivate()

    @staticmethod
    def __extension_added_cb(unused_set, unused_plugin_info, extension):
        extension.activate()
