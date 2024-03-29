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
from enum import IntEnum

import gi
gi.require_version('Peas', '1.0')
from gi.repository import GObject, Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger


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

    def get_dir(self):
        """Returns the directory where this type of plugins can be found."""
        if self.value == MiAZPluginType.USER:
            return ENV['LPATH']['PLUGINS']

        elif self.value == MiAZPluginType.SYSTEM:
            return ENV['GPATH']['PLUGINS']


class MiAZPluginManager:
    def __init__(self, app):
        self.app = app
        self.backend = self.app.get_service('backend')
        self.log = get_logger('MiAZ.PluginManager')
        self.log.debug("Initializing Plugin Manager")
        self.plugin_info_list = []

        self.engine = Peas.Engine.get_default()
        for loader in ("python3", ):
            self.engine.enable_loader(loader)

        self._setup_plugins_dir()
        self._setup_extension_set()

    def load_plugin(self, plugin: Peas.PluginInfo):
        self.engine.load_plugin(plugin)
        if plugin.is_loaded():
            self.log.debug("Plugin %s loaded", plugin.get_name())

    def unload_plugin(self, plugin: Peas.PluginInfo):
        self.engine.unload_plugin(plugin)


    def get_engine(self):
        return self.engine

    @property
    def plugins(self):
        """Gets the engine's plugin list."""
        return self.engine.get_plugin_list()

    @classmethod
    def get_plugin_type(cls, plugin_info):
        """Gets the PluginType for the specified Peas.PluginInfo."""
        paths = [plugin_info.get_data_dir(), ENV['GPATH']['PLUGINS']]
        if os.path.commonprefix(paths) == ENV['GPATH']['PLUGINS']:
            return MiAZPluginType.SYSTEM
        return MiAZPluginType.USER

    def get_extension(self, module_name):
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

    def get_plugin_info(self, module_name):
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
        if os.path.exists(ENV['GPATH']['PLUGINS']):
            self.engine.add_search_path(ENV['GPATH']['PLUGINS'])
            self.log.debug("Added System plugin dir: %s", ENV['GPATH']['PLUGINS'])

        # User plugins for a specific repo
        self.add_repo_plugins_dir()

    def add_repo_plugins_dir(self):
        try:
            repo = self.backend.repo_config()
            dir_conf = repo['dir_conf']
            dir_plugins = os.path.join(dir_conf, 'plugins')
            dir_plugins_available = os.path.join(dir_plugins, 'available')
            dir_plugins_used = os.path.join(dir_plugins, 'used')
            os.makedirs(dir_plugins, exist_ok=True)
            os.makedirs(dir_plugins_available, exist_ok=True)
            os.makedirs(dir_plugins_used, exist_ok=True)
            self.engine.add_search_path(dir_plugins_used)
            self.log.debug("Added User plugin dir: %s", dir_plugins_used)
        except KeyError:
            self.log.warning("There isn't any repo loaded right now!")


    @staticmethod
    def __extension_removed_cb(unused_set, unused_plugin_info, extension):
        extension.deactivate()

    @staticmethod
    def __extension_added_cb(unused_set, unused_plugin_info, extension):
        extension.activate()