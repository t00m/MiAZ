"""
# File: plugins.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: the frontend-neutral half of the plugin system

LibPeas 2 has no GTK dependency, so discovery, loading and activation never
needed a display. What tied MiAZ's plugin system to the desktop was where the
code lived: pluginsystem.py imported Gtk at module scope and used it in one
method, out of fourteen hundred lines.

This module holds the half that belongs to no frontend: the extension base
class, the plugin metadata, the category vocabulary, the operation descriptors
and the engine. The desktop keeps everything about placement (menus, sidebars,
pages, settings groups) and subclasses MiAZPluginCore for the rest.

Nothing here may import Gtk, Adw or Gdk.
tests/test_plugin_core.py fails if that changes.
"""

import glob
import importlib.util
import inspect
import os
import sys

import gi
gi.require_version('Peas', '2')
from gi.repository import GObject, Peas  # noqa: E402

from MiAZ.backend.log import MiAZLog  # noqa: E402


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


class MiAZAPI(GObject.GObject):
    """What a plugin instance is handed as `self.object`."""

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app


def N_(text: str) -> str:
    """Mark a string for extraction without translating it here.

    The category names below have to stay English: they are compared against
    what a .plugin file declares, and a .plugin file is never translated. But
    they still have to reach po/, because both display sites translate the
    value they read at runtime, `_(category)` in configview and `_(subcategory)`
    in app.install_plugin_menu, and gettext only finds a msgid that was
    extracted from source. This dict is where they are extracted from.
    """
    return text


# The vocabulary every plugin picks its Category and Subcategory from.
# Names are one word on purpose: both are menu labels. The workspace plugins
# section shows one submenu per category, and each of those shows one submenu
# per subcategory, so a plugin's actions sit two levels down at Category >
# Subcategory > action.
plugin_categories = {
    N_('Documents'): {
        N_('Import'): 'Bring documents into the repository',
        N_('Export'): 'Take documents out of the repository',
        N_('Annotation'): 'Write and read text alongside a document',
        N_('Contacts'): 'Keep details about senders and recipients',
        N_('Periodicity'): 'Say how often a document comes back',
        N_('Projects'): 'Group documents into projects',
        N_('Search'): 'Find documents',
        N_('Assistants'): 'Ask a model about a document'
    },
    N_('Repository'): {
        N_('Health'): 'Check the repository and repair it',
        N_('History'): 'Step back and forward through changes',
        N_('Stats'): 'Measure the whole repository'
    },
    N_('Interface'): {
        N_('Behavior'): 'Change how the window reacts',
        N_('Display'): 'Change what the window shows',
        N_('Accessibility'): 'Change how text is drawn'
    },
    N_('Help'): {
        N_('Examples'): 'Show how a plugin is written'
    }
}


def validate_category(category: str, subcategory: str):
    """Why this pair is not in the vocabulary, or None when it is.

    Nothing used to check this, and three plugins drifted onto a subcategory
    ('User Interface') that the vocabulary never defined. They kept their
    translated menu label only because an unrelated file happened to contain
    the same literal. A warning at registration is what catches the next one.
    """
    if category not in plugin_categories:
        return f"unknown category '{category}'"
    if subcategory not in plugin_categories[category]:
        return f"unknown subcategory '{subcategory}' for category '{category}'"
    return None


# Shown for a plugin that ships no icon of its own, so every plugin has one.
PLUGIN_DEFAULT_ICON = 'io.github.t00m.MiAZ-res-plugins'


def plugin_config_dir(repo_docs: str, name: str) -> str:
    """Where a plugin keeps its settings for one repository.

    Defined here rather than only on the desktop helper because the command
    line needs the same answer: a note written by `miaz ocr` that lands
    somewhere the window does not look is worse than no note.
    """
    return os.path.join(repo_docs, '.conf', 'plugins', name, 'conf')


def plugin_data_dir(repo_docs: str, name: str) -> str:
    """Where a plugin keeps its data for one repository."""
    return os.path.join(repo_docs, '.conf', 'plugins', name, 'data')


def plugin_version(info, app_version: str) -> str:
    """The version to show for a plugin.

    A bundled plugin ships with MiAZ and declares no version of its own, so it
    takes the application's. Writing it into the plugin instead meant the same
    number in forty-two files, kept in step by hand: nine of the twenty-one
    had drifted from themselves by the time anything checked.

    An out-of-tree plugin is released on its own schedule and says so. Its
    Version is used as it stands.

    `info` is a Peas.PluginInfo or the dict get_plugin_attributes parses out of
    a .plugin file, which is the same question asked of a different shape.
    """
    if isinstance(info, dict):
        declared = info.get('Version')
    else:
        declared = info.get_version()
    return declared or app_version


def normalise_menu_entries(entries) -> list:
    """The declared menu entries as (id, label, shortcuts) triples.

    An entry is written as ('doc', _('Create a new note'), ['<Ctrl>N']), and
    the shortcuts may be left out when there are none, which is the common
    case. Anything shorter than a pair is not an entry and is dropped.
    """
    normalised = []
    for entry in entries or []:
        if len(entry) < 2:
            continue
        entry_id, label = entry[0], entry[1]
        shortcuts = list(entry[2]) if len(entry) > 2 and entry[2] else []
        normalised.append((entry_id, label, shortcuts))
    return normalised


def get_plugin_attributes(plugin_file: str) -> dict:
    """Read a .plugin file into a dict. No engine, no import, no toolkit."""
    from gettext import gettext as _
    attributes = {}
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
                attributes[key.strip()] = _(value.strip())
    return attributes


# Operations
#
# An operation is one thing a plugin can do, declared as plain data next to the
# menu entries it already declares. Each frontend renders the same declaration
# its own way: the command line as an argparse subcommand, the desktop as a
# menu entry and a settings row.
#
# The declaration has to survive SafeDictExtractor (backend/util.py), which
# AST-parses plugin_info out of the module without importing it. That parser
# accepts literals, tuples, lists, dicts and _() calls, and raises on anything
# else, so the handler is named by string rather than referenced. The string
# names a module-level callable in the plugin's own module.

# What a declared parameter type is called, and what argparse should use.
PARAM_TYPES = {'str': str, 'int': int, 'float': float}


class MiAZParam:
    """One parameter of an operation.

    Three shapes, which between them cover what the plugins actually need:

    - positional: a document id, required, no flag
    - value: --language spa, optional, with a default
    - flag: --force, present or absent
    """

    def __init__(self, name, help='', default=None, flag=False,
                 positional=False, choices=None, type='str', multiple=False):
        self.name = name
        self.help = help
        self.default = default
        self.flag = flag
        self.positional = positional
        self.choices = list(choices) if choices else None
        self.type = type
        self.multiple = multiple

    @classmethod
    def from_dict(cls, data):
        return cls(name=data['name'],
                   help=data.get('help', ''),
                   default=data.get('default'),
                   flag=bool(data.get('flag', False)),
                   positional=bool(data.get('positional', False)),
                   choices=data.get('choices'),
                   type=data.get('type', 'str'),
                   multiple=bool(data.get('multiple', False)))

    def add_to(self, parser):
        """Add this parameter to an argparse parser."""
        if self.positional:
            # A menu entry acts on the selection, which is usually more than
            # one document, so a command has to be able to name more than one.
            # '+' rather than '*': no document named is a mistake, not a
            # request to process the whole repository.
            parser.add_argument(self.name, help=self.help or None,
                                choices=self.choices,
                                nargs='+' if self.multiple else None,
                                type=PARAM_TYPES.get(self.type, str))
            return

        if self.flag:
            # store_true rather than a default of None: a flag is a yes or a
            # no, and a handler reading args.force should never get None.
            parser.add_argument(f'--{self.name}', action='store_true',
                                help=self.help or None)
            return

        parser.add_argument(f'--{self.name}', default=self.default,
                            help=self.help or None, choices=self.choices,
                            type=PARAM_TYPES.get(self.type, str))


class MiAZOperation:
    """One thing a plugin can do, and how to reach it.

    `owner` is the plugin's module name, which is what the loader needs to
    import the one module that owns this operation and nothing else.
    `run` names a module-level callable in that module.
    """

    def __init__(self, name, owner, run, help='', params=None):
        self.name = name
        self.owner = owner
        self.run = run
        self.help = help
        self.params = list(params or [])

    @classmethod
    def from_dict(cls, data, owner):
        return cls(name=data['name'],
                   owner=owner,
                   run=data['run'],
                   help=data.get('help', ''),
                   params=[MiAZParam.from_dict(param)
                           for param in data.get('params', [])])

    def add_arguments(self, parser):
        for param in self.params:
            param.add_to(parser)

    def resolve(self, module):
        """The callable this operation names, or None when the plugin lies.

        A missing handler is the plugin's bug, not the caller's, so it reads
        back as None and the caller reports which plugin and which name.
        """
        return getattr(module, self.run, None)


# The .plugin key that declares one command, mirroring MenuEntry-<id>.
COMMAND_PREFIX = 'Command-'


def discover_commands(search_paths) -> dict:
    """Every command declared by a plugin on disk, without importing any.

    Returns {command name: {'help', 'module', 'plugin_name', 'plugin_file'}}.

    Reads only the .plugin files. That is the whole reason the command names
    live there rather than in plugin_info: `miaz search` pays for this on every
    run and gets nothing back from it, and the two costs are not close.
    Reading 21 .plugin files takes about 1.3 ms; AST-parsing the 21 modules for
    their plugin_info takes about 89 ms.

    The parameter schema stays in plugin_info, where it can be structured, and
    is read only once the user asks for that command, which needs the module
    imported anyway.

    A directory that does not exist contributes nothing. A fresh install that
    has never opened the window has no user plugin directory yet, and that is
    not a reason for a search to fail.
    """
    commands = {}
    for search_path in search_paths or []:
        if not search_path or not os.path.isdir(search_path):
            continue
        for plugin_file in sorted(glob.glob(os.path.join(search_path, '*', '*.plugin'))):
            try:
                attributes = _read_command_keys(plugin_file)
            except (OSError, UnicodeDecodeError) as error:
                # A malformed .plugin file is one broken plugin, not a broken
                # command line. Every other plugin still has to be reachable.
                MiAZLog('MiAZ.Plugins').warning(
                    f"Cannot read {plugin_file}: {error}")
                continue
            module = attributes.get('Module')
            if not module:
                continue
            for name, help_text in attributes.get('commands', {}).items():
                commands[name] = {'help': help_text,
                                  'module': module,
                                  'plugin_name': attributes.get('Name', module),
                                  'plugin_file': plugin_file}
    return commands


def _read_command_keys(plugin_file: str) -> dict:
    """The three things discovery needs out of a .plugin file, and no more.

    get_plugin_attributes translates every value it reads, which is right for
    the settings dialog and wasteful here: it turns 21 files into some 200
    gettext lookups to keep two of them, and `miaz search` pays that on every
    run. Only the command help is translated, because only it is displayed.
    """
    from gettext import gettext as _
    found = {'commands': {}}
    with open(plugin_file, 'r', encoding='utf-8') as handler:
        for line in handler:
            line = line.strip()
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key, value = key.strip(), value.strip()
            if key in ('Module', 'Name'):
                found[key] = value
            elif key.startswith(COMMAND_PREFIX):
                name = key[len(COMMAND_PREFIX):].strip()
                if name:
                    found['commands'][name] = _(value)
    return found


def parse_operations(plugin_info: dict, owner: str) -> list:
    """The operations a plugin declares, as descriptors.

    A declaration missing a name or a handler names nothing that can be run.
    Dropping it here beats failing later from inside argparse with a message
    that says nothing about which plugin is at fault.
    """
    operations = []
    for entry in plugin_info.get('Operations') or []:
        if not isinstance(entry, dict):
            continue
        if not entry.get('name') or not entry.get('run'):
            continue
        operations.append(MiAZOperation.from_dict(entry, owner))
    return operations


class MiAZPluginCore(GObject.GObject):
    """Discovery, loading and activation. No frontend of any kind.

    The desktop subclasses this and adds everything about placement. The
    console frontend uses it as it stands.

    `search_paths` are the directories holding plugin directories. They are
    passed in rather than read out of ENV so this is testable against a
    temporary directory, and so the console frontend can decide for itself
    which paths it wants.
    """
    __gtype_name__ = 'MiAZPluginCore'

    def __init__(self, search_paths=None, log_name='MiAZ.PluginCore'):
        super().__init__()
        self.log = MiAZLog(log_name)
        self.engine = Peas.Engine.get_default()
        for loader in ('python', ):
            self.engine.enable_loader(loader)
        self._extension_instances = {}
        self._load_failures = {}
        self._search_paths = []
        for path in search_paths or []:
            self.add_search_path(path)

    def add_search_path(self, path):
        """Register a directory of plugin directories with the engine."""
        if not os.path.exists(path):
            # Normal, not a fault: the per-user plugin directory is only there
            # once a plugin has been installed into it. It was a warning, and
            # `miaz --help` prints the commands plugins contribute, so anybody
            # who never installed one got that line above their help.
            self.log.debug(f"Plugin directory does not exist: {path}")
            return False
        if path in self._search_paths:
            return True
        self.engine.add_search_path(path)
        self._search_paths.append(path)
        self.log.debug(f"Added plugin dir: {path}")
        return True

    def get_search_paths(self) -> list:
        return list(self._search_paths)

    @property
    def plugins(self):
        """The engine's plugin list (libpeas 2.x: Engine is a Gio.ListModel)"""
        return list(self.engine)

    def get_plugin_info(self, module_name: str):
        """The Peas.PluginInfo for a module name, or None."""
        for plugin in self.plugins:
            if plugin.get_module_name() == module_name:
                return plugin
        return None

    def get_extension(self, module_name: str):
        """The active extension instance for the given module name."""
        return self._extension_instances.get(module_name)

    def get_load_failures(self) -> dict:
        """Copy of the current load failures: {module_name: {'name', 'reason'}}."""
        return dict(self._load_failures)

    def get_load_error(self, module_name: str):
        entry = self._load_failures.get(module_name)
        return entry['reason'] if entry else None

    def is_plugin_loaded(self, plugin) -> bool:
        """True if the plugin is active: via libpeas or the direct-import fallback."""
        return plugin.get_module_name() in self._extension_instances or plugin.is_loaded()

    def import_module(self, module_name: str):
        """Import one plugin module by name, without activating anything.

        This is what a frontend that only wants a plugin's operations needs: no
        engine load, no extension instance, no do_activate() reaching for
        widgets that are not there.
        """
        if module_name in sys.modules:
            return sys.modules[module_name]
        module_file = self.find_module_file(module_name)
        if module_file is None:
            self.log.error(f"Python module '{module_name}.py' not found in "
                           "plugin directories")
            return None
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except Exception as error:
            self.log.error(f"Import of '{module_name}' failed: {error}")
            sys.modules.pop(module_name, None)
            self._load_failures[module_name] = {
                'name': module_name, 'reason': str(error)}
            return None

    def find_module_file(self, module_name: str):
        """Where a plugin module lives, searching the registered paths.

        plugin.get_data_dir() in libpeas 2.x returns a synthetic path based on
        the module name rather than the real one, so the directories are
        searched instead.
        """
        for search_dir in self._search_paths:
            matches = glob.glob(os.path.join(search_dir, '**', f'{module_name}.py'),
                                recursive=True)
            if matches:
                return matches[0]
        return None

    def _direct_import_plugin(self, plugin) -> bool:
        """Import a Python plugin directly when the libpeas Python loader is
        unavailable.

        Fedora (and possibly other distros) ships libpeas 2.x without the
        Python loader RPM, so engine.load_plugin() silently fails.
        """
        module_name = plugin.get_module_name()
        if module_name in sys.modules:
            return True
        module = self.import_module(module_name)
        if module is None:
            return False
        self._load_failures[module_name] = {
            'name': plugin.get_name(), 'reason': ''}
        self._load_failures.pop(module_name, None)
        self.log.debug(f"Direct-imported plugin module '{module_name}'")
        return True

    def make_api(self):
        """What a plugin instance is handed as `self.object`.

        Overridden by a frontend that has an application to hand over. The core
        has none, which is why this is a method and not a constructor argument.
        """
        return MiAZAPI(None)

    def load_plugin(self, plugin) -> bool:
        if self.is_plugin_loaded(plugin):
            return True
        pname = plugin.get_name()
        try:
            self.engine.load_plugin(plugin)
            if not plugin.is_loaded():
                if not self._direct_import_plugin(plugin):
                    self.log.error(f"Plugin {pname} couldn't be loaded")
                    return False
            self._activate_plugin_instance(plugin)
            self._load_failures.pop(plugin.get_module_name(), None)
            return True
        except Exception as error:
            # do_activate() may raise to veto its own activation (e.g. a plugin
            # whose required external tools are not installed). Clean up the
            # half-loaded engine state so the plugin does not read back as
            # loaded, and report failure to the caller.
            self.log.error(f"Plugin {pname} couldn't be loaded: {error}")
            self._load_failures[plugin.get_module_name()] = {
                'name': pname, 'reason': str(error)}
            try:
                if plugin.is_loaded():
                    self.engine.unload_plugin(plugin)
            except Exception as cleanup_error:
                self.log.debug(f"Cleanup after failed load of {pname}: {cleanup_error}")
            return False

    def _activate_plugin_instance(self, plugin):
        """Instantiate and activate the plugin class found in sys.modules."""
        module_name = plugin.get_module_name()
        module = sys.modules.get(module_name)
        if module is None:
            self.log.error(f"Module '{module_name}' not in sys.modules after load")
            return None
        for _name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, MiAZExtension) and cls is not MiAZExtension:
                instance = cls()
                instance.props.object = self.make_api()
                try:
                    instance.do_activate()
                except Exception as error:
                    # A plugin may raise from do_activate() to refuse activation
                    # (e.g. missing external tools). Propagate so load_plugin
                    # cleans up and reports the failure; do not register it.
                    self.log.warning(f"Plugin '{module_name}' vetoed its "
                                     f"activation: {error}")
                    raise
                self._extension_instances[module_name] = instance
                self.log.debug(f"Activated plugin class '{_name}' for module "
                               f"'{module_name}'")
                return instance
        self.log.error(f"No MiAZExtension subclass found in module '{module_name}'")
        return None

    def _deactivate_plugin_instance(self, plugin):
        """Deactivate and remove the plugin instance."""
        module_name = plugin.get_module_name()
        instance = self._extension_instances.pop(module_name, None)
        if instance is not None:
            # Refuse contributions from here on, before the teardown rather
            # than after it: a worker finishing mid-unload is exactly the case
            # this guards against.
            helper = getattr(instance, 'plugin', None)
            if helper is not None and hasattr(helper, 'set_active'):
                helper.set_active(False)
            try:
                instance.do_deactivate()
            except Exception as error:
                self.log.error(f"Error deactivating '{module_name}': {error}")
