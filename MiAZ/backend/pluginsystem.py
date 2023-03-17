#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: pluginsystem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: a Plugin System based on LibPeas
# Code borrowed from Orca project:
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
        self.log = get_logger('MiAZ.PluginManager')
        self.log.debug("Initializing Plugin Manager")
        self.plugin_info_list = []

        self.engine = Peas.Engine.get_default()
        for loader in ("python3", ):
            self.engine.enable_loader(loader)

        self._setup_plugins_dir()
        self._setup_extension_set()

        # Load plugins.
        for plugin in self.plugins:
            self.engine.load_plugin(plugin)
            # ~ if plugin.is_loaded():
                # ~ self.log.debug("\tPlugin %s %s (%s)",  plugin.get_name(), plugin.get_version(), plugin.get_description())
                # ~ self.log.debug("\t\tModule name: %s", plugin.get_module_name())
                # ~ self.log.debug("\t\tModule directory: %s", plugin.get_module_dir())
                # ~ self.log.debug("\t\tModule version: %s", plugin.get_version())
                # ~ self.log.debug("\t\tModule type: %s", self.get_plugin_type(plugin))

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

        # User plugins
        if os.path.exists(ENV['LPATH']['PLUGINS']):
            self.engine.add_search_path(ENV['LPATH']['PLUGINS'])
            self.log.debug("Added User plugin dir: %s", ENV['LPATH']['PLUGINS'])

    @staticmethod
    def __extension_removed_cb(unused_set, unused_plugin_info, extension):
        extension.deactivate()

    @staticmethod
    def __extension_added_cb(unused_set, unused_plugin_info, extension):
        extension.activate()