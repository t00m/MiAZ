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
import glob
import json
import zipfile
from enum import IntEnum
from gettext import gettext as _

import gi
gi.require_version('Peas', '1.0')
from gi.repository import GObject, Peas

from MiAZ.backend.log import MiAZLog

plugin_categories = {
    "Data Management": {
        "Import": "Plugins for importing documents",
        "Export": "Plugins for exporting documents",
        "Backup": "Plugins for backing up your repository",
        "Restore": "Tools for restoring backups",
        "Single update": "Tool for manipulating data for a single file",
        "Batch update": "Tools for bulk data manipulation",
        "Synchronisation": "Plugins for syncing data with cloud services or between devices",
        "Migration": "For transferring data between different platforms or systems",
        "Deletion": "Tools for securely removing documents or data from the repository"
    },
    "Content Organisation": {
        "Tagging and Classification": "Tools for categorising and tagging documents",
        "Search and Indexing": "Plugins that improve search capabilities or indexing methods",
        "Metadata Management": "For adding, editing, or viewing document metadata"
    },
    "Visualisation and Diagrams": {
        "Diagram Creation": "Tools for creating flowcharts, mind maps, and other visual representations",
        "Data Visualisation": "Plugins that generate graphs, charts, or other visual data summaries",
        "Dashboard Widgets": "Add-ons that provide a summary of key information in a dashboard format"
    },
    "Security and Privacy": {
        "Encryption/Decryption": "Plugins that encrypt or decrypt documents",
        "Access Control": "Tools for managing user permissions and access levels",
        "Audit and Logging": "Plugins that track changes and access history"
    },
    "Automation and Workflow": {
        "Task Automation": "Plugins that automate repetitive tasks, like renaming files or sorting documents",
        "Workflow Management": "For creating and managing document-related workflows",
        "Notification Systems": "Tools that notify users of specific events or deadlines"
    },
    "Integration and Interoperability": {
        "API Connectors": "Plugins that allow integration with third-party services (e.g., Google Drive, Dropbox, Slack)",
        "Third-Party Service Integration": "For integrating with tools like CRM, ERP, or project management systems",
        "Communication Tools": "Plugins for email, messaging, or social media integration"
    },
    "Customisation and Personalisation": {
        "Themes and UI Customisation": "Plugins that allow users to change the application's appearance",
        "Templates": "Pre-defined document templates or layout options",
        "Language Packs": "Plugins for multi-language support or localisation"
    },
    "Analytics and Reporting": {
        "Usage Analytics": "Tools that provide insights into how the application is used",
        "Document Statistics": "Plugins that analyse and report on document content",
        "Custom Reports": "For generating bespoke reports based on user-defined criteria"
    },
    "Collaboration": {
        "Real-time Collaboration": "Plugins that enable multiple users to work on the same document simultaneously",
        "Version Control": "Tools for managing document versions and changes",
        "Comments and Annotations": "Plugins for adding comments or annotations to documents"
    },
    "Content Editing and Formatting": {
        "Advanced Editors": "Plugins that offer enhanced text, image, or video editing capabilities",
        "Formatting Tools": "For applying or automating specific formatting rules across documents",
        "Conversion Tools": "Plugins that convert documents into different formats (e.g., Word to PDF)"
    },
    "Support and Help": {
        "Guides and Tutorials": "Plugins that provide user manuals, tutorials, or onboarding guides",
        "Troubleshooting Tools": "For diagnosing and fixing common issues within the application",
        "User Feedback": "Tools that allow users to submit feedback or suggestions"
    },
    "Archiving and Compliance": {
        "Long-Term Archiving": "Plugins for storing documents in long-term, secure formats",
        "Compliance Checkers": "Tools that ensure documents meet regulatory or legal standards",
        "Retention Policies": "Plugins for setting and enforcing document retention rules"
    },
    "Others": {
        "Miscelanea": "Plugins not fitting in another category"
    }
}

class MiAZAPI(GObject.GObject):
    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app

    def get_plugin_attributes(self, plugin_file):
        plugin_system = self.app.get_service('plugin-system')
        return plugin_system.get_plugin_attributes(plugin_file)



class MiAZPluginType(IntEnum):
    """Types of plugins depending on their directory location"""

    SYSTEM = 1
    USER = 2

    def __str__(self):
        if self.value == MiAZPluginType.USER:
            return _("user")
        elif self.value == MiAZPluginType.SYSTEM:
            return _("system")


class MiAZPluginSystem(GObject.GObject):
    def __init__(self, app):
        super().__init__()
        GObject.signal_new('plugins-updated',
                            MiAZPluginSystem,
                            GObject.SignalFlags.RUN_LAST, None, ())
        self.log = MiAZLog('MiAZ.PluginSystem')
        self.app = app
        self.util = self.app.get_service('util')
        self.log.debug("Initializing Plugin Manager")
        self.plugin_info_list = []

        self.engine = Peas.Engine.get_default()
        for loader in ("python3", ):
            self.engine.enable_loader(loader)

        self._setup_plugins_dir()
        self._setup_extension_set()
        self.create_plugin_index()
        self.log.info("Plugin system initialited")
        srvrepo = self.app.get_service('repo')
        srvrepo.connect('repository-switched', self.create_plugin_index)

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
        try:
            ptype = self.get_plugin_type(plugin)
            pname = plugin.get_name()
            pvers = plugin.get_version()
            self.engine.load_plugin(plugin)

            if plugin.is_loaded():
                self.log.info(f"{str(ptype).title()} Plugin {pname} v{pvers} ({ptype}) loaded")
                return True
            else:
                self.log.error(f"Plugin {pname} v{pvers} ({ptype}) couldn't be loaded")
                return False
        except AttributeError as error:
            self.log.error(f"Plugin {pname} v{pvers} ({ptype}) couldn't be loaded")
            self.log.error(f"Reason: {error}")
            return False
        except Exception as error:
            self.log.error(error)
            self.log.error(f"Plugin {pname} v{pvers} ({ptype}) couldn't be loaded")
            self.log.error(f"Reason: {error}")
            return False
        self.emit('plugins-updated')

    def unload_plugin(self, plugin: Peas.PluginInfo):
        try:
            ptype = self.get_plugin_type(plugin)
            pname = plugin.get_name()
            pvers = plugin.get_version()
            self.engine.unload_plugin(plugin)
            self.log.info(f"Plugin  {pname} v{pvers} ({ptype}) unloaded")
            self.emit('plugins-updated')
        except Exception as error:
            self.log.error(error)

    def get_engine(self):
        return self.engine

    @property
    def plugins(self):
        """Gets the engine's plugin list"""
        return self.engine.get_plugin_list()

    def get_user_plugins(self):
        self.rescan_plugins()
        user_plugins = []
        for plugin in self.plugins:
            ptype = self.get_plugin_type(plugin)
            if ptype == MiAZPluginType.USER:
                plugin_id = plugin.get_name()
                user_plugins.append(plugin_id)
        return user_plugins


    def get_plugin_type(self, plugin_info):
        """Gets the PluginType for the specified Peas.PluginInfo"""
        ENV = self.app.get_env()
        PLUGIN_DIR = os.path.dirname(plugin_info.get_data_dir())
        plugin_name = plugin_info.get_name()
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

    def get_plugin_attributes(self, plugin_file: str):
        """Get plugin attributes from `plugin_module`.plugin file"""
        plugin_info = {}
        with open(plugin_file, 'r') as file:
            # Skip the first line (assuming it's [Plugin])
            next(file)

            for line in file:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue

                # Split each line at the first '=' character
                if '=' in line:
                    key, value = line.split('=', 1)
                    plugin_info[key.strip()] = value.strip()
        return plugin_info

    def create_plugin_index(self, *args):
        """Parse plugins info file and recreate index on runtime"""
        self.log.info("Creating plugin index during runtime")
        plugin_index = {}
        ENV = self.app.get_env()
        plugins_dir = ENV['LPATH']['PLUGINS']
        plugin_files = glob.glob(os.path.join(plugins_dir, '*', '*.plugin'))
        if not plugin_files:
            self.log.warning(f"No .plugin files found in {plugins_dir}")

        plugin_list = []
        for plugin_file in plugin_files:
            plugin_info = self.get_plugin_attributes(plugin_file)
            plugin_name = plugin_info['Name']
            plugin_desc = plugin_info['Description']
            plugin_index[plugin_name] = plugin_info
            plugin_list.append((plugin_name, plugin_desc))
            self.log.info(f" - Adding plugin {plugin_name} to plugin index")


        with open(ENV['APP']['PLUGINS']['LOCAL_INDEX'], 'w') as fp:
            json.dump(plugin_index, fp, sort_keys=False, indent=4)
            self.log.info(f"File index-plugins.json generated with {len(plugin_index)} plugins")

        try:
            config = self.app.get_config_dict()
            repo_id = config['App'].get('current')
            config_plugins = self.app.get_config('Plugin')
            config_plugins.remove_all()
            config_plugins.add_available_batch(plugin_list)
            self.log.info(f"Plugins available updated successfully for repository {repo_id}")
        except AttributeError:
            self.log.warning("Skip. Plugin config not ready yet")
