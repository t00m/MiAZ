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
    _('Data Management'): {
        _('Import'): _('Plugins for importing documents'),
        _('Export'): _('Plugins for exporting documents'),
        _('Backup'): _('Plugins for backing up your repository'),
        _('Restore'): _('Plugins for restoring backups'),
        _('Single update'): _('Plugins for manipulating data for a single file'),
        _('Batch update'): _('Plugins for bulk data manipulation'),
        _('Synchronisation'): _('Plugins for syncing data with cloud services or between devices'),
        _('Migration'): _('Plugins for transferring data between different platforms or systems'),
        _('Deletion'): _('Plugins for securely removing documents or data from the repository')
    },
    _('Content Organisation'): {
        _('Tagging and Classification'): _('Plugins for categorising and tagging documents'),
        _('Search and Indexing'): _('Plugins that improve search capabilities or indexing methods'),
        _('Metadata Management'): _('Plugins for adding, editing, or viewing document metadata')
    },
    _('Visualisation and Diagrams'): {
        _('Diagram Creation'): _('Plugins for creating flowcharts, mind maps, and other visual representations'),
        _('Data Visualisation'): _('Plugins that generate graphs, charts, or other visual data summaries'),
        _('Dashboard Widgets'): _('Plugins that provide a summary of key information in a dashboard format')
    },
    _('Security and Privacy'): {
        _('Encryption/Decryption'): _('Plugins that encrypt or decrypt documents'),
        _('Access Control'): _('Plugins for managing user permissions and access levels'),
        _('Audit and Logging'): _('Plugins that track changes and access history')
    },
    _('Automation and Workflow'): {
        _('Task Automation'): _('Plugins that automate repetitive tasks, like renaming files or sorting documents'),
        _('Workflow Management'): _('Plugins for creating and managing document-related workflows'),
        _('Notification Systems'): _('Plugins for notifying users of specific events or deadlines')
    },
    _('Integration and Interoperability'): {
        _('API Connectors'): _('Plugins that allow integration with third-party services (e.g., Google Drive, Dropbox, Slack)'),
        _('Third-Party Service Integration'): _('Plugins for integrating with tools like CRM, ERP, or project management systems'),
        _('Communication Tools'): _('Plugins for email, messaging, or social media integration')
    },
    _('Customisation and Personalisation'): {
        _('Themes and UI Customisation'): _('Plugins that allow users to change the application appearance'),
        _('Templates'): _('Pre-defined document templates or layout options'),
        _('Language Packs'): _('Plugins for multi-language support or localisation')
    },
    _('Analytics and Reporting'): {
        _('Usage Analytics'): _('Plugins that provide insights into how the application is used'),
        _('Document Statistics'): _('Plugins that analyse and report on document content'),
        _('Custom Reports'): _('Plugins for generating bespoke reports based on user-defined criteria')
    },
    _('Collaboration'): {
        _('Real-time Collaboration'): _('Plugins that enable multiple users to work on the same document simultaneously'),
        _('Version Control'): _('Plugins for managing document versions and changes'),
        _('Comments and Annotations'): _('Plugins for adding comments or annotations to documents')
    },
    _('Content Editing and Formatting'): {
        _('Advanced Editors'): _('Plugins that offer enhanced text, image, or video editing capabilities'),
        _('Formatting Tools'): _('Plugins for applying or automating specific formatting rules across documents'),
        _('Conversion Tools'): _('Plugins that convert documents into different formats (e.g., Word to PDF)')
    },
    _('Support and Help'): {
        _('Guides and Tutorials'): _('Plugins that provide user manuals, tutorials, or onboarding guides'),
        _('Troubleshooting Tools'): _('Plugins for diagnosing and fixing common issues within the application'),
        _('User Feedback'): _('Plugins that allow users to submit feedback or suggestions')
    },
    _('Archiving and Compliance'): {
        _('Long-Term Archiving'): _('Plugins for storing documents in long-term, secure formats'),
        _('Compliance Checkers'): _('Plugins that ensure documents meet regulatory or legal standards'),
        _('Retention Policies'): _('Plugins for setting and enforcing document retention rules')
    },
    _('Others'): {
        _('Miscelanea'): _('Plugins not fitting in another category')
    }
}

class MiAZAPI(GObject.GObject):
    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app


class MiAZPlugin(GObject.GObject):
    _started = False

    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZPlugin')
        self.util = self.app.get_service('util')

    def get_plugin_attributes(self, plugin_file):
        plugin_system = self.app.get_service('plugin-system')
        return plugin_system.get_plugin_attributes(plugin_file)

    def register(self, plugin_object):
        self.info = plugin_object.info
        self.name = self.info['Name']
        self.desc = self.info['Description']
        self.poid = f'plugin-{self.name}'
        self.app.add_widget(self.poid, plugin_object)

        # Create plugin directories for config and data
        ## Configuration directory and file
        configdir = self.get_config_dir()
        if not os.path.exists(configdir):
            os.makedirs(configdir, exist_ok=True)
        self.log.debug(f"\tConf: {configdir}")
        configfile = self.get_config_file()
        if not os.path.exists(configfile):
            self.util.json_save(configfile, {})

        # Data directory
        datadir = self.get_data_dir()
        if not os.path.exists(datadir):
            os.makedirs(datadir, exist_ok=True)
        self.log.debug(f"\tData: {datadir}")

    def set_started(self, started: bool) -> None:
        self._started = started

    def started(self):
        return self._started

    def get_app(self):
        return self.app

    def get_logger(self):
        return MiAZLog(f'Plugin.{self.name}')

    def get_name(self):
        return self.name

    def get_plugin_file(self):
        return self.plugin_file

    def get_plugin_info_dict(self):
        return self.info

    def get_plugin_info_key(self, key):
        return self.info[key]

    def get_widget_name(self):
        module = self.info['Module']
        return f'plugin-{module}'

    def get_menu_item(self, callback=None):
        factory = self.app.get_service('factory')
        name = self.get_menu_item_name()
        menuitem = factory.create_menuitem(name, self.desc, callback, None, [])
        return self.app.add_widget(f'plugin-menuitem-{self.name}', menuitem)

    def get_menu_item_name(self):
        return f'plugin-menuitem-{self.name}'

    def menu_item_loaded(self):
        name = self.get_menu_item_name()
        if self.app.get_widget(name) is None:
            return False
        return True

    def get_config_dir(self):
        repository = self.app.get_service('repo')
        return os.path.join(repository.docs, '.conf', 'plugins', self.name, 'conf')

    def get_data_dir(self):
        repository = self.app.get_service('repo')
        return os.path.join(repository.docs, '.conf', 'plugins', self.name, 'data')

    def get_data_file(self):
        data_dir = self.get_data_dir()
        return os.path.join(data_dir, f"{self.name}.json")

    def get_config_file(self):
        return os.path.join(self.get_config_dir(), f"Plugin-{self.name}.json")

    def get_config_file_default_available_data(self):
        return os.path.join(self.get_config_dir(), f"default_available_data.json")

    def get_config_data(self):
        config_file = self.get_config_file()
        try:
            config_data = self.util.json_load(config_file)
        except Exception:
            config_data = {}
            self.util.json_save(config_file, config_data)
        return config_data

    def get_config_key(self, key: str):
        config_data = self.get_config_data()
        try:
            return config_data[key]
        except:
            return None

    def set_config_data(self, config_data: {}):
        config_file = self.get_config_file()
        self.util.json_save(config_file, config_data)

    def set_config_key(self, key: str, value):
        config_file = self.get_config_file()
        config_data = self.get_config_data()
        config_data[key] = value
        self.util.json_save(config_file, config_data)
        self.log.debug(f"Plugin config for {self.name} updated: [{key}] = {value}")

    def install_menu_entry(self, menuitem = None):
        category = self.info['Category']
        subcategory = self.info['Subcategory']
        subcategory_submenu = self.app.install_plugin_menu(category, subcategory)
        if menuitem is not None:
            subcategory_submenu.append_item(menuitem)
        return subcategory_submenu


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
        sid_u = GObject.signal_lookup('plugins-updated', MiAZPluginSystem)
        if sid_u == 0:
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
        self.create_user_plugin_index()
        self.create_system_plugin_index()
        self.log.info("Plugin system initialited")
        srvrepo = self.app.get_service('repo')
        srvrepo.connect('repository-switched', self.create_user_plugin_index)

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
                plugin_name = plugin.get_name()
                user_plugins.append(plugin_name)
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
                    plugin_info[key.strip()] = _(value.strip())
        return plugin_info

    def create_user_plugin_index(self, *args):
        """Parse plugins info file and recreate index on runtime"""
        self.log.info("Creating user plugin index during runtime")
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
            self.log.info(f" - Adding user plugin {plugin_name} to plugin index")


        with open(ENV['APP']['PLUGINS']['USER_INDEX'], 'w') as fp:
            json.dump(plugin_index, fp, sort_keys=False, indent=4)
            self.log.info(f"File index-user-plugins.json generated with {len(plugin_index)} plugins")

        try:
            config = self.app.get_config_dict()
            repo_id = config['App'].get('current')
            config_plugins = self.app.get_config('Plugin')
            config_plugins.remove_all()
            config_plugins.add_available_batch(plugin_list)
            self.log.info(f"Plugins available updated successfully for repository {repo_id}")
        except AttributeError:
            self.log.warning("Skip. Plugin config not ready yet")

    def create_system_plugin_index(self, *args):
        """Parse plugins info file and recreate index on runtime"""
        self.log.info("Creating system plugin index during runtime")
        plugin_index = {}
        ENV = self.app.get_env()
        plugins_dir = ENV['GPATH']['PLUGINS']
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
            self.log.info(f" - Adding system plugin {plugin_name} to plugin index")


        with open(ENV['APP']['PLUGINS']['SYSTEM_INDEX'], 'w') as fp:
            json.dump(plugin_index, fp, sort_keys=False, indent=4)
            self.log.info(f"File index-system-plugins.json generated with {len(plugin_index)} plugins")

        # ~ try:
            # ~ config = self.app.get_config_dict()
            # ~ repo_id = config['App'].get('current')
            # ~ config_plugins = self.app.get_config('Plugin')
            # ~ config_plugins.remove_all()
            # ~ config_plugins.add_available_batch(plugin_list)
            # ~ self.log.info(f"Plugins available updated successfully for repository {repo_id}")
        # ~ except AttributeError:
            # ~ self.log.warning("Skip. Plugin config not ready yet")
