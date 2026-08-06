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
import shutil
import zipfile
import inspect
import importlib.util
from gettext import gettext as _, ngettext

import gi
gi.require_version('Peas', '2')
from gi.repository import GObject, Peas

from MiAZ.backend.log import MiAZLog


def format_load_failure_toast(count: int) -> str:
    """Summary toast text for `count` plugins that failed to load."""
    return ngettext(
        '{n} plugin failed to load. See Settings > Plugins.',
        '{n} plugins failed to load. See Settings > Plugins.',
        count).format(n=count)


def format_load_failure_banner(failures: dict) -> str:
    """One line naming each failed plugin and its reason, joined by '; '.

    `failures` is the dict returned by MiAZPluginSystem.get_load_failures():
    {module_name: {'name': <plugin name>, 'reason': <error text>}}.
    """
    parts = []
    for entry in failures.values():
        parts.append(_('{name} failed to load: {reason}').format(
            name=entry['name'], reason=entry['reason']))
    return '; '.join(parts)


class MiAZExtension(GObject.GObject):
    """Base class for all MiAZ plugins.

    Inherits from GObject.GObject only: no Peas.ExtensionBase, no ExtensionSet.
    Plugin instances are managed manually after engine.load_plugin() by
    scanning sys.modules for a MiAZExtension subclass.
    """
    __gtype_name__ = 'MiAZExtension'
    object = GObject.Property(type=GObject.GObject)

    def do_activate(self):
        pass

    def do_deactivate(self):
        pass

plugin_info_template = {
        _('Module'):        '',
        _('Name'):          '',
        _('Loader'):        '',
        _('Description'):   '',
        _('Authors'):       '',
        _('Copyright'):     '',
        _('Website'):       '',
        _('Help'):          '',
        _('Version'):       '',
        _('Category'):      '',
        _('Subcategory'):   ''
    }

plugin_categories = {
    _('Data Management'): {
        _('Import'): _('Plugins for importing documents'),
        _('Export'): _('Plugins for exporting documents'),
        _('Backup'): _('Plugins for backing up your repository'),
        _('Restore'): _('Plugins for restoring backups'),
        _('Single mode'): _('Plugins for manipulating data for a single document'),
        _('Batch mode'): _('Plugins for bulk data manipulation'),
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
        _('Dashboard Widgets'): _('Plugins that provide a summary of key information in a dashboard format'),
        _('Document Viewers'): _('Plugins for displaying documents in their native formats')
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
    _('ETL and Data Processing'): {
        _('Data Extraction'): _('Plugins for extracting data from various sources (APIs, databases, files)'),
        _('Data Transformation'): _('Plugins for cleaning, enriching, or reformatting extracted data'),
        _('Data Loading'): _('Plugins for importing processed data into target systems or repositories'),
        _('Workflow Automation'): _('Plugins for orchestrating multi-step ETL processes'),
        _('Data Quality'): _('Plugins for validating, deduplicating, or ensuring data consistency')
    },
    _('Artificial Intelligence'): {
        _('Text Analysis'): _('Plugins for NLP tasks like summarization, sentiment analysis, or entity recognition'),
        _('Document AI'): _('Plugins for intelligent document processing (e.g., OCR, form recognition)'),
        _('Predictive Analytics'): _('Plugins for forecasting or pattern detection in data'),
        _('Recommendation Systems'): _('Plugins for suggesting relevant content or actions based on user behavior'),
        _('AI Assistants'): _('Plugins with chatbot-like interactions or automated task assistance'),
        _('Model Integration'): _('Plugins for connecting to external AI models (e.g., OpenAI, Hugging Face)')
    },
    _('Others'): {
        _('Miscelanea'): _('Plugins not fitting in another category')
    }
}

# Shown for a plugin that ships no icon of its own, so every plugin has one.
PLUGIN_DEFAULT_ICON = 'io.github.t00m.MiAZ-res-plugins'


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
        # Filled in by register(). Defaulted here so anything reading them
        # early (an icon lookup, a log line) finds an empty value, not an
        # AttributeError.
        self.info = {}
        self.name = ''

    def get_plugin_attributes(self, plugin_file):
        plugin_system = self.app.get_service('plugin-system')
        return plugin_system.get_plugin_attributes(plugin_file)

    def register(self, plugin_object, info):
        self.info = info
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
        return os.path.join(self.get_config_dir(), "default_available_data.json")

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
        except Exception:
            return None

    def set_config_data(self, config_data: {}):
        config_file = self.get_config_file()
        self.util.json_save(config_file, config_data)

    def set_config_key(self, key: str, value):
        config_file = self.get_config_file()
        config_data = self.get_config_data()
        config_data[key] = value
        self.util.json_save(config_file, config_data)
        # Log the key name only, never the value: plugin config can hold secrets.
        self.log.debug(f"Plugin config for {self.name} updated: key '{key}' set")

    def get_source_dir(self):
        """Directory the plugin was loaded from, or None.

        A plugin folder is named after the plugin Name (MiAZProjectMgt) while
        its Module is the python module inside it (projmgt), and the two match
        only sometimes. Looking for the Module alone therefore found nothing
        for most bundled plugins, which is why their icons never showed up, so
        both names are tried, system directory first.
        """
        ENV = self.app.get_env()
        names = [self.info.get('Name'), self.info.get('Module'), self.name]
        for base_dir in (ENV['GPATH']['PLUGINS'], ENV['LPATH']['PLUGINS']):
            for name in names:
                if not name:
                    continue
                candidate = os.path.join(base_dir, name)
                if os.path.isdir(candidate):
                    return candidate
        return None

    def get_icon_path(self):
        source_dir = self.get_source_dir()
        if source_dir is None:
            return None
        for ext in ('svg', 'png'):
            path = os.path.join(source_dir, f'icon.{ext}')
            if os.path.exists(path):
                return path
        return None

    def get_icon_name(self):
        """Themed icon name for this plugin. Never empty.

        A plugin ships its icon as icon.svg or icon.png next to its module.
        Widgets take icon names rather than paths, so the file is exported once
        into the user icon directory under a name unique to this plugin. A
        plugin without an icon file, or whose icon cannot be exported, gets the
        generic MiAZ plugin icon: every plugin has an icon to show.
        """
        icon_path = self.get_icon_path()
        if icon_path:
            icons = self.app.get_service('icons')
            if icons is not None:
                module = self.info.get('Module', self.name)
                name = icons.register_file_icon(f"miaz-plugin-{module.lower()}", icon_path)
                if name:
                    return name
        return PLUGIN_DEFAULT_ICON

    def install_menu_entry(self, menuitem = None):
        category = self.info['Category']
        subcategory = self.info['Subcategory']
        subcategory_submenu = self.app.install_plugin_menu(category, subcategory)
        if menuitem is not None:
            subcategory_submenu.append_item(menuitem)
            # Register the item under its canonical key so other layers (the UI)
            # can reuse it without the plugin system knowing about any widget.
            self.app.add_widget(self.get_menu_item_name(), menuitem)
        return subcategory_submenu

    def add_workspace_page(self, widget, name, title, icon_name=None):
        workspace = self.app.get_widget('workspace')
        if workspace is not None:
            workspace.add_stack_page(widget, name, title, icon_name)

    def register_document_tab(self, name, title, factory, icon_name=None, weight=100):
        """Contribute a tab to the single-document rename dialog.

        `factory` is called with the app once per dialog and must return a
        Gtk.Widget answering set_document(doc_id) and apply(old_id, new_id).
        See the plugin contract in AGENTS.md.

        Without an explicit icon_name the tab wears the plugin's own icon, so a
        plugin gets a recognisable tab without doing anything about it.
        """
        tabs = self.app.get_service('document-tabs')
        if tabs is None:
            return
        tabs.register(owner=self.get_name(), name=name, title=title,
                      factory=factory, icon_name=icon_name or self.get_icon_name(),
                      weight=weight)

    def unregister_document_tabs(self):
        tabs = self.app.get_service('document-tabs')
        if tabs is not None:
            tabs.unregister_all(owner=self.get_name())


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
        for loader in ("python", ):
            self.engine.enable_loader(loader)

        self._extension_instances = {}
        self._load_failures = {}
        self._setup_plugins_dir()
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
            plugin_res = os.path.join(ENV['LPATH']['PLUGINS'], 'resources', module)
            if os.path.exists(plugin_res):
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

    def _direct_import_plugin(self, plugin: Peas.PluginInfo) -> bool:
        """Import a Python plugin directly when libpeas Python loader is unavailable.

        Fedora (and possibly other distros) ships libpeas 2.x without the Python loader
        RPM, so engine.load_plugin() silently fails. This method uses importlib to load
        the .py file by searching the plugin directories (plugin.get_data_dir() in
        libpeas 2.x returns a synthetic path based on module name, not the real path).
        """
        module_name = plugin.get_module_name()
        if module_name in sys.modules:
            return True
        ENV = self.app.get_env()
        module_file = None
        for search_dir in (ENV['GPATH']['PLUGINS'], ENV['LPATH']['PLUGINS']):
            matches = glob.glob(os.path.join(search_dir, '**', f'{module_name}.py'), recursive=True)
            if matches:
                module_file = matches[0]
                break
        if module_file is None:
            self.log.error(f"Python module '{module_name}.py' not found in plugin directories")
            return False
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self.log.debug(f"Direct-imported plugin module '{module_name}' from {module_file}")
            return True
        except Exception as error:
            self.log.error(f"Direct import of '{module_name}' failed: {error}")
            sys.modules.pop(module_name, None)
            self._load_failures[module_name] = {
                'name': plugin.get_name(), 'reason': str(error)}
            return False

    def is_plugin_loaded(self, plugin: Peas.PluginInfo) -> bool:
        """True if the plugin is active: via libpeas or our direct-import fallback."""
        return plugin.get_module_name() in self._extension_instances or plugin.is_loaded()

    def get_load_failures(self) -> dict:
        """Copy of the current load failures: {module_name: {'name', 'reason'}}."""
        return dict(self._load_failures)

    def get_load_error(self, module_name: str):
        entry = self._load_failures.get(module_name)
        return entry['reason'] if entry else None

    def load_plugin(self, plugin: Peas.PluginInfo) -> bool:
        if self.is_plugin_loaded(plugin):
            return True
        pname = plugin.get_name()
        pvers = plugin.get_version()
        try:
            self.engine.load_plugin(plugin)

            if not plugin.is_loaded():
                # libpeas Python loader may not be installed on the host; try direct import
                if not self._direct_import_plugin(plugin):
                    self.log.error(f"Plugin {pname} v{pvers} couldn't be loaded")
                    return False

            self._activate_plugin_instance(plugin)
            self._load_failures.pop(plugin.get_module_name(), None)
            self.log.info(f"Plugin {pname} v{pvers} loaded")
            self._install_plugin_requirements(plugin)
            self.emit('plugins-updated')
            return True
        except Exception as error:
            # do_activate() may raise to veto its own activation (e.g. a plugin
            # whose required external tools are not installed). Clean up the
            # half-loaded engine state so the plugin does not read back as
            # loaded, and report failure to the caller.
            self.log.error(f"Plugin {pname} v{pvers} couldn't be loaded: {error}")
            self._load_failures[plugin.get_module_name()] = {
                'name': pname, 'reason': str(error)}
            try:
                if plugin.is_loaded():
                    self.engine.unload_plugin(plugin)
            except Exception as cleanup_error:
                self.log.debug(f"Cleanup after failed load of {pname}: {cleanup_error}")
            return False

    def _install_plugin_requirements(self, plugin: Peas.PluginInfo):
        """Install a plugin's external libraries when the feature is enabled.

        Only acts when the external-libraries venv already exists; if the user
        never enabled it, nothing happens here and the AI error dialog offers to
        enable it at first use. Already-satisfied plugins install nothing.
        """
        try:
            venv = self.app.get_service('venv')
            if venv is None or not venv.exists():
                return
            pdir = plugin.get_module_dir()
            missing = venv.missing(venv.requirements_for([pdir])) if pdir else []
            if not missing:
                return
            self.app.get_service('extlibs').install(
                self.app.get_widget('window'), requirements=missing)
        except Exception as error:
            self.log.warning(f"Could not install plugin requirements: {error}")

    def unload_plugin(self, plugin: Peas.PluginInfo):
        pname = plugin.get_name()
        pvers = plugin.get_version()
        try:
            self._deactivate_plugin_instance(plugin)
            self.engine.unload_plugin(plugin)
            self._remove_plugin_www(plugin)
            self._remove_plugin_document_tabs(plugin)
            self.log.info(f"Plugin {pname} v{pvers} unloaded")
            self.emit('plugins-updated')
        except Exception as error:
            self.log.error(error)

    def _remove_plugin_www(self, plugin: Peas.PluginInfo):
        """Remove a plugin's published web directory when it is unloaded.

        Plugins that publish to the MiAZ Browser write to
        LPATH/WWW/<plugin directory basename> (the convention the bundled
        MiAZInsights follows through its PLUGIN_DIR_NAME).
        Removing it here, centrally, means disabling or uninstalling any such
        plugin (bundled or user-space) drops its content from the Browser,
        without each plugin having to clean up after itself. A plugin that
        publishes under a different name than its folder is not covered here and
        must clean up in its own do_deactivate.
        """
        try:
            module_dir = plugin.get_module_dir()
            if not module_dir:
                return
            name = os.path.basename(module_dir)
            ENV = self.app.get_env()
            www = os.path.join(ENV['LPATH']['WWW'], name)
            if os.path.isdir(www):
                shutil.rmtree(www)
                self.log.debug(f"Removed web content for plugin '{name}': {www}")
        except Exception as error:
            self.log.warning(f"Could not remove web content for plugin: {error}")

    def _remove_plugin_document_tabs(self, plugin: Peas.PluginInfo):
        """Drop the rename-dialog tabs of a plugin when it is unloaded.

        Plugins are expected to call unregister_document_tabs() in their
        do_deactivate; doing it here too means one that forgets cannot leave a
        tab whose factory no longer exists.
        """
        tabs = self.app.get_service('document-tabs')
        if tabs is None:
            return
        try:
            tabs.unregister_all(owner=plugin.get_name())
        except Exception as error:
            self.log.warning(f"Could not remove document tabs for plugin: {error}")

    def get_engine(self):
        return self.engine

    @property
    def plugins(self):
        """Gets the engine's plugin list (libpeas 2.x: Engine is a Gio.ListModel)"""
        return list(self.engine)

    def get_extension(self, module_name: str):
        """Gets the active extension instance for the given module name."""
        return self._extension_instances.get(module_name)

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

    def _activate_plugin_instance(self, plugin: Peas.PluginInfo):
        """Instantiate and activate the plugin class found in sys.modules."""
        module_name = plugin.get_module_name()
        module = sys.modules.get(module_name)
        if module is None:
            self.log.error(f"Module '{module_name}' not in sys.modules after load")
            return None
        for _name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, MiAZExtension) and cls is not MiAZExtension:
                instance = cls()
                instance.props.object = MiAZAPI(self.app)
                try:
                    instance.do_activate()
                except Exception as error:
                    # A plugin may raise from do_activate() to refuse activation
                    # (e.g. missing external tools). Propagate so load_plugin
                    # cleans up and reports the failure; do not register it.
                    self.log.warning(f"Plugin '{module_name}' vetoed its activation: {error}")
                    raise
                self._extension_instances[module_name] = instance
                self.log.debug(f"Activated plugin class '{_name}' for module '{module_name}'")
                return instance
        self.log.error(f"No MiAZExtension subclass found in module '{module_name}'")
        return None

    def _deactivate_plugin_instance(self, plugin: Peas.PluginInfo):
        """Deactivate and remove the plugin instance."""
        module_name = plugin.get_module_name()
        instance = self._extension_instances.pop(module_name, None)
        if instance is not None:
            try:
                instance.do_deactivate()
            except Exception as error:
                self.log.error(f"Error deactivating '{module_name}': {error}")

    def _setup_plugins_dir(self):
        """Set System and User plugins directories"""
        # System plugins
        # Mandatory set of plugins for every repository
        ENV = self.app.get_env()
        if os.path.exists(ENV['GPATH']['PLUGINS']):
            self.engine.add_search_path(ENV['GPATH']['PLUGINS'])
            self.log.debug(f"Added System plugin dir: {ENV['GPATH']['PLUGINS']}")
        else:
            self.log.warning("System plugins directory does not exist:")
            self.log.warning(f"{ENV['GPATH']['PLUGINS']}")
            self.log.warning("Continuing without system plugins")

        # User plugins
        # All user space plugins are available for all repositories
        # However, each repository can use none, any or all of them
        if not os.path.exists(ENV['LPATH']['PLUGINS']):
            os.makedirs(ENV['LPATH']['PLUGINS'], exist_ok=True)
        self.engine.add_search_path(ENV['LPATH']['PLUGINS'])
        self.log.debug(f"Added user plugins dir: {ENV['LPATH']['PLUGINS']}")

    def get_plugin_attributes(self, plugin_file: str):
        """Get plugin attributes from `plugin_module`.plugin file"""
        plugin_info = {}
        with open(plugin_file, 'r', encoding='utf-8') as file:
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

    def create_plugin_index(self, *args):
        """Scan both bundled and user plugin directories and write a unified index."""
        self.log.info("Creating plugin index during runtime")
        self._load_failures = {}
        plugin_index = {}
        plugin_list = []
        ENV = self.app.get_env()
        for plugins_dir in (ENV['GPATH']['PLUGINS'], ENV['LPATH']['PLUGINS']):
            module_files = glob.glob(os.path.join(plugins_dir, '*', '*.py'), recursive=False)
            for module_file in module_files:
                plugin_info = self.util.extract_variable_from_python_module(module_file, 'plugin_info')
                if plugin_info is not None:
                    plugin_name = plugin_info['Name']
                    plugin_desc = plugin_info['Description']
                    plugin_index[plugin_name] = plugin_info
                    plugin_list.append((plugin_name, plugin_desc))
                    self.log.info(f" - Adding plugin {plugin_name} to plugin index")

        with open(ENV['APP']['PLUGINS']['INDEX'], 'w', encoding='utf-8') as fp:
            json.dump(plugin_index, fp, sort_keys=False, indent=4)
            self.log.info(f"File index-plugins.json generated with {len(plugin_index)} plugins")

        try:
            config = self.app.get_config_dict()
            repo_id = config['App'].get('current')
            config_plugins = self.app.get_config('Plugin')
            config_plugins.add_available_batch(plugin_list)
            old_keys = set(config_plugins.load_available().keys()) - {p[0] for p in plugin_list}
            for key in old_keys:
                config_plugins.remove_available(key)
            self.log.info(f"Plugins available updated successfully for repository {repo_id}")
        except AttributeError:
            self.log.warning("Skip. Plugin config not ready yet")
