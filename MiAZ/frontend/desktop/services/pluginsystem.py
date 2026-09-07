
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
gi.require_version('Gtk', '4.0')
from gi.repository import GObject, Gtk, Peas

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
        _('Subcategory'):   '',
        _('MenuEntries'):   []
    }


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


class MiAZAPI(GObject.GObject):
    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app


class PluginMenuRegistry:
    """What each plugin contributed to the shared menus.

    The workspace menu is thrown away and rebuilt whenever plugins change. To
    get the entries back, the rebuild used to reset every plugin's started flag
    and call its startup() again, which meant a plugin's setup ran once per
    load or unload of any other plugin: extra gestures on the column view,
    extra background scans, extra handlers. One of those extra gestures is what
    made a right click crash after the plugin was disabled.

    Recording the contributions means the rebuild replays data. startup() runs
    once per activation, which is what a plugin author expects it to do.
    """

    def __init__(self):
        self._entries = {}

    def record(self, owner: str, category: str, subcategory: str,
               kind: str, payload):
        """Remember one contribution. The same one twice is still one."""
        entries = self._entries.setdefault(owner, [])
        entry = (category, subcategory, kind, payload)
        if entry not in entries:
            entries.append(entry)

    def entries(self, owner: str) -> list:
        return list(self._entries.get(owner, []))

    def forget(self, owner: str):
        self._entries.pop(owner, None)

    def replay(self, owner: str, app):
        """Put this plugin's entries back into the menus as they are now.

        Gio.Menu copies a menu item when it is appended and references a
        submenu, so replaying the recorded objects into fresh menus is safe
        and keeps a live submenu (the scanner sources, say) connected.
        """
        for category, subcategory, kind, payload in self.entries(owner):
            submenu = app.install_plugin_menu(category, subcategory)
            if submenu is None:
                continue
            if kind == 'item':
                submenu.append_item(payload)
            elif kind == 'submenu':
                title, menu = payload
                submenu.append_submenu(title, menu)


class PluginSettingsRegistry:
    """Which settings group each plugin offers, and how to build it.

    A builder, not a group. Building AutoScan's group runs SANE and building
    the OCR one shells out to tesseract, so nothing is built until the
    Settings tab is actually looked at. Recording the callable also means a
    plugin enabled while the dialog is closed still shows its settings the
    next time it opens, which a signal emitted on dialog open cannot do.
    """

    def __init__(self):
        self._entries = []
        self._views = []

    def add(self, owner: str, category: str, builder):
        """Remember one builder. The same one twice is still one."""
        entry = (category, owner, builder)
        if entry not in self._entries:
            self._entries.append(entry)

    def builders(self) -> list:
        """Every builder as (category, owner, builder), in display order.

        Sorted here rather than at the point of display, so the groups sit in
        the same order whatever order the plugins happened to load in.
        """
        return sorted(self._entries, key=lambda entry: (entry[0], entry[1]))

    def add_view(self, owner: str, name: str, title: str, icon_name: str,
                 factory):
        """Remember one metadata view. The same one twice is still one."""
        entry = (owner, name, title, icon_name, factory)
        if entry not in self._views:
            self._views.append(entry)

    def views(self) -> list:
        """Every plugin metadata view, alphabetically by title."""
        return sorted(self._views, key=lambda entry: entry[2])

    def forget(self, owner: str):
        self._entries = [entry for entry in self._entries if entry[1] != owner]
        self._views = [entry for entry in self._views if entry[0] != owner]


class PluginPageRegistry:
    """Which workspace pages each plugin contributed.

    The loader builds a fresh plugin instance on every activation, so a plugin
    cannot remember across a disable/enable cycle what it added last time. This
    can, which is what lets unload_plugin take the pages away and lets plugins
    stop hiding a page and re-adopting it by name on the way back.
    """

    def __init__(self):
        self._pages = {}

    def add(self, owner: str, name: str):
        """Record a page. Recording it twice still means one page."""
        names = self._pages.setdefault(owner, [])
        if name not in names:
            names.append(name)

    def names(self, owner: str) -> list:
        """The pages this plugin currently has in the workspace."""
        return list(self._pages.get(owner, []))

    def pop_all(self, owner: str) -> list:
        """The pages of this plugin, forgetting them as they are handed over."""
        return self._pages.pop(owner, [])


class PluginViewRegistry:
    """Which workspace views belong to which plugin.

    A view is removed when its plugin is unloaded, the same deal pages get:
    the name has to be free again, or the plugin cannot register on the way
    back in.
    """

    def __init__(self):
        self._views = {}

    def add(self, owner: str, name: str):
        """Record a view. Recording it twice still means one view."""
        names = self._views.setdefault(owner, [])
        if name not in names:
            names.append(name)

    def names(self, owner: str) -> list:
        return list(self._views.get(owner, []))

    def pop_all(self, owner: str) -> list:
        return self._views.pop(owner, [])


class PluginWidgetRegistry:
    """How to take back the widgets a plugin put into a shared container.

    The sidebar and the headerbar are boxes every plugin appends to. Detaching
    a widget again takes several steps (drop it from the box, from the size
    group, from the dropdown list, from the widget registry), and each plugin
    was writing its own version of them. Recording an undo step at the moment of
    the contribution keeps the two halves together and lets unload_plugin run
    them, so a plugin that forgets cannot leave a widget behind.
    """

    def __init__(self):
        self._undo = {}
        self.log = MiAZLog('MiAZ.PluginWidgets')

    def add(self, owner: str, undo):
        """Record one step that undoes one contribution."""
        self._undo.setdefault(owner, []).append(undo)

    def count(self, owner: str) -> int:
        return len(self._undo.get(owner, []))

    def undo_all(self, owner: str):
        """Run every step of this plugin, most recent first.

        A step that raises is logged and skipped: one widget that is already
        detached must not leave the rest of them attached.
        """
        for undo in reversed(self._undo.pop(owner, [])):
            try:
                undo()
            except Exception as error:
                self.log.warning(f"Could not undo a contribution of '{owner}': {error}")


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
        # Contributions are accepted from here until the plugin is unloaded.
        # A background job that finishes later (the scanner probe builds its
        # menu when the device answers) must not add UI for a plugin that is
        # already gone: the entry would sit there doing nothing until the next
        # menu rebuild dropped it.
        self._active = True
        self.info = info
        self.name = self.info['Name']
        self.desc = self.info['Description']
        self.poid = f'plugin-{self.name}'
        self.app.add_widget(self.poid, plugin_object)

        problem = validate_category(self.info.get('Category', ''),
                                    self.info.get('Subcategory', ''))
        if problem is not None:
            self.log.warning(f"Plugin {self.name}: {problem}. Its menu entry "
                             "will not be translated.")

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
        """One menu item for a plugin declaring no entries.

        Bundled plugins declare their entries and go through
        install_menu_entries. This is what an out of tree plugin written
        against the older API still calls, so it keeps working; it uses the
        first declared label when there is one, and the plugin description
        when there is not, which is a sentence about the plugin rather than
        a label saying what a click will do.
        """
        factory = self.app.get_service('factory')
        name = self.get_menu_item_name()
        entries = self.get_menu_entries()
        if entries:
            label = entries[0][1]
        else:
            label = self.desc
            self.log.warning(f"Plugin {self.name} declares no MenuEntries, so "
                             "its description is used as the menu label")
        menuitem = factory.create_menuitem(name, label, callback, None, [])
        return self.app.add_widget(name, menuitem)

    def get_menu_entries(self) -> list:
        """What the definition says this plugin's menu entries are."""
        return normalise_menu_entries(self.info.get('MenuEntries', []))

    def get_menu_entry_label(self, entry_id: str):
        """The declared label of one entry, or None when it is not declared.

        For the plugin that has to build its own Gio.MenuItem, the scanner
        with its submenu of sources, and still wants the label written where
        every other label is.
        """
        for declared_id, label, _shortcuts in self.get_menu_entries():
            if declared_id == entry_id:
                return label
        return None

    def get_menu_item_name(self, entry_id: str = None):
        """The action name of one entry, which is also its widget key.

        Without an id this is the plugin's canonical key, the one the
        headerbar Add menu mirrors for an Import plugin.
        """
        if entry_id is None:
            return f'plugin-menuitem-{self.name}'
        return f'plugin-menuitem-{self.name}-{entry_id}'

    def install_menu_entries(self, callbacks: dict) -> dict:
        """Build the entries the definition declares, and install them.

        The definition owns what the entries are: which ones, in what order,
        under what label and on what shortcut. This says what each one does,
        keyed by the id the definition gave it. Returns {id: Gio.MenuItem}
        for a plugin that has to reach one of its own items later.

        A declared id with no callback, or a callback for an id nothing
        declares, is an author mistake. Both are logged and skipped: a plugin
        short of one entry is easier to diagnose than one that fails to load.
        """
        if not self.is_active():
            return {}
        factory = self.app.get_service('factory')
        entries = self.get_menu_entries()
        declared = [entry_id for entry_id, _label, _shortcuts in entries]
        for entry_id in callbacks:
            if entry_id not in declared:
                self.log.warning(f"Plugin {self.name}: '{entry_id}' has a "
                                 "callback but no entry in the definition")
        items = {}
        for entry_id, label, shortcuts in entries:
            callback = callbacks.get(entry_id)
            if callback is None:
                self.log.warning(f"Plugin {self.name}: menu entry "
                                 f"'{entry_id}' does nothing, so it is left out")
                continue
            name = self.get_menu_item_name(entry_id)
            menuitem = factory.create_menuitem(name, label, callback, None,
                                               shortcuts)
            self.install_menu_entry(menuitem, name=name)
            items[entry_id] = menuitem
        # The Add menu mirrors one item per Import plugin, and reads it under
        # the canonical key, so the first entry answers to both names.
        if items:
            self.app.add_widget(self.get_menu_item_name(),
                                next(iter(items.values())))
        return items

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

    def is_active(self) -> bool:
        """Whether this plugin may still contribute to the interface."""
        return getattr(self, '_active', True)

    def set_active(self, active: bool):
        self._active = active

    def install_menu_entry(self, menuitem = None, category = None,
                           subcategory = None, name = None):
        """Add one item to a menu, and remember it for the next rebuild.

        Most plugins reach this through install_menu_entries, which builds the
        items the definition declares. It is still the way in for an item the
        definition cannot describe, the scanner's submenu of sources.

        With no category the plugin's own one is used, which is what almost
        every caller wants. A plugin whose action belongs somewhere else
        passes the pair explicitly, rather than reaching for
        app.install_plugin_menu and leaving the entry unrecorded: those were
        the entries a menu rebuild used to drop.

        `name` is the widget key the item answers to, and defaults to the
        plugin's canonical one. A plugin with several entries gives each its
        own, so its items do not overwrite each other.
        """
        if not self.is_active():
            return None
        explicit = category is not None or subcategory is not None
        category = category or self.info['Category']
        subcategory = subcategory or self.info['Subcategory']
        if explicit:
            # The plugin's own pair was already checked at registration; this
            # is the other one, the pair a plugin names to file an action
            # somewhere else.
            problem = validate_category(category, subcategory)
            if problem is not None:
                self.log.warning(f"Plugin {self.name} menu entry: {problem}")
        subcategory_submenu = self.app.install_plugin_menu(category, subcategory)
        if menuitem is not None:
            subcategory_submenu.append_item(menuitem)
            # Register the item under its key so other layers (the UI) can
            # reuse it without the plugin system knowing about any widget.
            self.app.add_widget(name or self.get_menu_item_name(), menuitem)
            # And record it, so a menu rebuild can put it back without running
            # this plugin's startup() again.
            self._menu_registry().record(self.name, category, subcategory,
                                         'item', menuitem)
        return subcategory_submenu

    def install_menu_submenu(self, title: str, menu):
        """Add a submenu of this plugin's own items to its menu entry.

        The plugins that offer several actions (assign, unassign, manage) build
        a Gio.Menu and hang it under their entry. Going through here records it
        like a single item does, so a menu rebuild restores it without calling
        startup() again.
        """
        if not self.is_active():
            return None
        category = self.info['Category']
        subcategory = self.info['Subcategory']
        subcategory_submenu = self.app.install_plugin_menu(category, subcategory)
        subcategory_submenu.append_submenu(title, menu)
        self._menu_registry().record(self.name, category, subcategory,
                                     'submenu', (title, menu))
        return subcategory_submenu

    def install_settings_group(self, builder) -> bool:
        """Offer this plugin's settings to the Repository Settings dialog.

        `builder` is called with no arguments and returns an
        Adw.PreferencesGroup. It is held rather than called: building a group
        can be slow (AutoScan asks SANE what devices exist) and the dialog
        must open without paying for it. The group is filed under the
        heading this plugin's Category names.

        Returns whether it was recorded, which is False for a plugin already
        on its way out.
        """
        if not self.is_active():
            return False
        self._settings_registry().add(self.name, self.info['Category'], builder)
        return True

    def install_metadata_view(self, name, title, icon_name, factory) -> bool:
        """Add one repository vocabulary to the Metadata tab.

        For a plugin that owns a vocabulary rather than a preference: the
        periodicities, the projects. `factory` is called with no arguments
        and returns the widget. Unlike a settings builder, it is not held for
        later: the Metadata tab calls every registered factory while the
        dialog is being built, since the dialog is constructed fresh each
        time it opens and a vocabulary view is cheap to create.
        """
        if not self.is_active():
            return False
        self._settings_registry().add_view(self.name, name, title, icon_name,
                                           factory)
        return True

    def _settings_registry(self):
        return self.app.get_service('plugin-system').settings

    def _menu_registry(self):
        return self.app.get_service('plugin-system').menus

    def add_workspace_page(self, widget, name, title, icon_name=None):
        """Add a page to the workspace stack, owned by this plugin.

        The plugin system removes it when the plugin is unloaded, so there is
        nothing to clean up in do_deactivate and nothing to re-adopt on the way
        back. A plugin that would rather manage the stack itself still can:
        workspace.get_stack() hands over the real Adw.ViewStack.
        """
        if not self.is_active():
            return
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return
        workspace.add_stack_page(widget, name, title, icon_name)
        system = self.app.get_service('plugin-system')
        if system is not None:
            system.pages.add(self.get_name(), name)

    def add_workspace_view(self, widget, name, icon_name, label):
        """Add a view to the documents toolbar, owned by this plugin.

        The plugin system removes it when the plugin is unloaded, so there is
        nothing to undo in do_deactivate and the name is free again next time.
        """
        if not self.is_active():
            return
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return
        workspace.add_view(name, icon_name, label, widget)
        system = self.app.get_service('plugin-system')
        if system is not None:
            system.views.add(self.get_name(), name)

    def _widget_registry(self):
        system = self.app.get_service('plugin-system')
        return None if system is None else system.widgets

    def _register_widget_key(self, widget_key, widget):
        """Register a widget under a key and arrange for the key to go too.

        Detaching a widget but leaving its key registered is a trap: the plugin
        looks the key up on its next activation, finds the old widget, decides
        it has nothing to do, and never re-attaches anything.
        """
        if widget_key is None:
            return
        self.app.add_widget(widget_key, widget)
        registry = self._widget_registry()
        if registry is not None:
            registry.add(self.get_name(), lambda: self.app.remove_widget(widget_key))

    def add_sidebar_widget(self, widget, widget_key: str = None):
        """Put a widget in the sidebar's plugin section, owned by this plugin.

        The plugin system detaches it on unload, so there is nothing to remove
        in do_deactivate. Pass `widget_key` to have it registered (and later
        unregistered) with the app widget registry as well. Reaching the section
        directly through app.get_widget('sidebar-plugin-section') still works
        and is fine; this only saves writing the teardown.
        """
        if not self.is_active():
            return False
        section = self.app.get_widget('sidebar-plugin-section')
        if section is None:
            self.log.warning("No sidebar plugin section to add a widget to")
            return False
        section.append(widget)
        registry = self._widget_registry()
        if registry is not None:
            registry.add(self.get_name(), lambda: section.remove(widget))
        self._register_widget_key(widget_key, widget)
        return True

    def add_headerbar_widget(self, widget, position: str = 'right',
                             widget_key: str = None):
        """Put a widget in the header bar, owned by this plugin.

        `position` is 'left' or 'right'. Removed on unload, as above.
        """
        if not self.is_active():
            return False
        key = 'headerbar-left-box' if position == 'left' else 'headerbar-right-box'
        box = self.app.get_widget(key)
        if box is None:
            self.log.warning(f"No '{key}' to add a widget to")
            return False
        box.append(widget)
        registry = self._widget_registry()
        if registry is not None:
            registry.add(self.get_name(), lambda: box.remove(widget))
        self._register_widget_key(widget_key, widget)
        return True

    def add_sidebar_dropdown(self, dropdown, widget_key: str = None,
                             width: int = 190, with_icon: bool = True):
        """Put a filter dropdown in the sidebar, wired the way the others are.

        One call replaces four steps that each needed undoing: join the shared
        size group so every dropdown lines up, join the 'plugin-dropdowns' list
        the workspace filter pass reads, register under `widget_key`, and append
        to the plugin section behind the plugin's icon.

        `widget_key` defaults to 'plugin-<Name>-dropdown', which is where the
        rest of the app looks for a plugin's filter dropdown.
        """
        if not self.is_active():
            return False
        registry = self._widget_registry()
        owner = self.get_name()
        if widget_key is None:
            widget_key = f'plugin-{owner}-dropdown'

        dropdown.set_size_request(width, -1)

        size_group = self.app.get_widget('sidebar-dropdown-size-group')
        if size_group is not None:
            size_group.add_widget(dropdown)
            if registry is not None:
                registry.add(owner, lambda: size_group.remove_widget(dropdown))

        dropdowns = self.app.get_widget('plugin-dropdowns')
        if dropdowns is not None:
            dropdowns.append(dropdown)
            if registry is not None:
                registry.add(owner, lambda: dropdowns.remove(dropdown))

        row = self._sidebar_row(dropdown) if with_icon else dropdown
        # The key names the dropdown, not the row around it: callers look the
        # key up to read the selection.
        self._register_widget_key(widget_key, dropdown)
        return self.add_sidebar_widget(row)

    def _sidebar_row(self, widget):
        """The plugin's icon next to its widget, or the widget on its own."""
        icon_path = self.get_icon_path()
        if not icon_path:
            return widget
        image = Gtk.Image.new_from_file(icon_path)
        image.set_pixel_size(16)
        image.set_valign(Gtk.Align.CENTER)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_hexpand(True)
        row.append(image)
        row.append(widget)
        return row

    def register_document_tab(self, name, title, factory, icon_name=None, weight=100):
        """Contribute a tab to the single-document rename dialog.

        `factory` is called with the app once per dialog and must return a
        Gtk.Widget answering set_document(doc_id) and apply(old_id, new_id).
        See the plugin contract in AGENTS.md.

        Without an explicit icon_name the tab wears the plugin's own icon, so a
        plugin gets a recognisable tab without doing anything about it.
        """
        if not self.is_active():
            return
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

    def register_suggest_item(self, name, label, callback, section=None):
        """Contribute an entry to the rename dialog's Suggest menu.

        Everything that proposes values for the filename fields belongs under
        that one button, so a plugin adds an entry here rather than packing a
        button of its own into the dialog.

        `name` is the application action name and must be unique; `callback`
        has the Gio.SimpleAction 'activate' signature and should resolve the
        current rename widget itself, since the menu outlives any one dialog.
        `section` is the heading the entry appears under: say what the entry
        does with the document, because a user deciding between a local guess
        and one that leaves the machine needs to see the difference before
        choosing, not after.
        """
        if not self.is_active():
            return
        actions = self.app.get_service('actions')
        if actions is None:
            return
        actions.register_suggest_item(owner=self.get_name(), name=name,
                                      label=label, callback=callback,
                                      section=section)

    def unregister_suggest_items(self):
        actions = self.app.get_service('actions')
        if actions is not None:
            actions.unregister_suggest_items(owner=self.get_name())


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
        # What plugins contributed to shared UI, so unload_plugin can take it
        # away the same way it already does web content and dialog tabs.
        self.pages = PluginPageRegistry()
        self.views = PluginViewRegistry()
        self.widgets = PluginWidgetRegistry()
        self.menus = PluginMenuRegistry()
        self.settings = PluginSettingsRegistry()
        self._setup_plugins_dir()
        self._plugin_list = []
        self.scan_plugin_index()
        self.log.info("Plugin system initialited")
        srvrepo = self.app.get_service('repo')
        # Only the per-repository half. What is on disk has not changed.
        srvrepo.connect('repository-switched', self._on_repository_switched)

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
        plugin_name, plugin_ext = utils.filename_details(plugin_path)
        plugin_code = f"{plugin_name}.py"
        plugin_meta = f"{plugin_name}.plugin"
        # Read the listing under 'with': an archive that fails validation used
        # to be left open.
        with zipfile.ZipFile(plugin_path) as azip:
            names = azip.namelist()
        valid = plugin_code in names and plugin_meta in names

        if valid:
            ENV = self.app.get_env()
            # Through util.unzip, not extractall: that is where the "stay
            # inside the target directory" check lives, and this is the same
            # untrusted archive the plugin settings import handles.
            utils.unzip(plugin_path, ENV['LPATH']['PLUGINS'])
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
            self._remove_plugin_pages(plugin)
            self._remove_plugin_views(plugin)
            self.menus.forget(plugin.get_name())
            self.settings.forget(plugin.get_name())
            self.widgets.undo_all(plugin.get_name())
            self.log.info(f"Plugin {pname} v{pvers} unloaded")
            self.emit('plugins-updated')
        except Exception as error:
            self.log.error(error)

    def unload_all(self) -> int:
        """Unload every loaded plugin. Returns how many were unloaded.

        Used when the repository changes: the enabled set is per repository
        (plugins-used.json lives in the repository's .conf), so the plugins of
        the one being left have to go before those of the one being opened
        arrive. Each unload runs the same teardown a manual disable does, so a
        plugin cannot leave a page, a rename tab or a header bar button behind.

        One plugin that fails to unload does not stop the rest: unload_plugin
        already logs and swallows, and the caller is in the middle of a switch
        that has to finish either way.
        """
        unloaded = 0
        for plugin in self.plugins:
            if self.is_plugin_loaded(plugin):
                self.unload_plugin(plugin)
                unloaded += 1
        if unloaded:
            self.log.info(f"Plugins unloaded: {unloaded}")
        return unloaded

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

    def _remove_plugin_pages(self, plugin: Peas.PluginInfo):
        """Take back the workspace pages of a plugin when it is unloaded.

        Pages used to stay in the Adw.ViewStack for the life of the process,
        hidden, because re-adding one under a name already in the stack warns.
        Removing it here frees the name, so the plugin just builds a fresh page
        next time it is activated.
        """
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return
        for name in self.pages.pop_all(plugin.get_name()):
            try:
                workspace.remove_stack_page(name)
                self.log.debug(f"Removed workspace page '{name}'")
            except Exception as error:
                self.log.warning(f"Could not remove workspace page '{name}': {error}")

    def _remove_plugin_views(self, plugin: Peas.PluginInfo):
        """Take back the workspace views of a plugin when it is unloaded."""
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return
        for name in self.views.pop_all(plugin.get_name()):
            try:
                workspace.remove_view(name)
                self.log.debug(f"Removed workspace view '{name}'")
            except Exception as error:
                self.log.warning(f"Could not remove workspace view '{name}': {error}")

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

    def _on_repository_switched(self, *_args):
        # Not update_available_plugins directly: the signal hands the emitter
        # to its handler, which would arrive as the plugin list.
        self.update_available_plugins()

    def create_plugin_index(self, *args):
        """Scan both plugin directories, write the index, update the repository.

        Kept as one entry point for callers that really did change what is on
        disk, such as importing a plugin from a ZIP.
        """
        plugin_list = self.scan_plugin_index()
        self.update_available_plugins(plugin_list)
        return plugin_list

    def scan_plugin_index(self, *args):
        """Scan both plugin directories and write index-plugins.json.

        What is on disk does not depend on which repository is open, so this
        runs once at startup and again only when a plugin is added or removed.
        It used to be bolted onto the per-repository update below, which meant
        a full rescan, 19 Python modules parsed with ast, on every repository
        switch, and one wasted scan at startup whose result was thrown away.
        """
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
        self._plugin_list = plugin_list
        return plugin_list

    def update_available_plugins(self, plugin_list=None, *args):
        """Write the scanned plugins into the open repository's available set.

        This is the half that needs a repository, so it is what a repository
        switch runs. Before a repository is open there is no plugin config to
        write to, which is not a problem worth a warning: the switch that
        follows does the work.
        """
        if plugin_list is None:
            plugin_list = getattr(self, '_plugin_list', None) or self.scan_plugin_index()
        config_plugins = self.app.get_config('Plugin')
        if config_plugins is None:
            self.log.debug("No repository open yet, available plugins not written")
            return
        config = self.app.get_config_dict()
        repo_id = config['App'].get('current')
        config_plugins.add_available_batch(plugin_list)
        scanned = {p[0] for p in plugin_list}
        old_keys = set(config_plugins.load_available().keys()) - scanned
        for key in old_keys:
            config_plugins.remove_available(key)
        # A plugin that is gone (retired into the core, or deleted) stays in the
        # repository's used list forever otherwise: the startup loop walks the
        # plugins it found, so the name is never visited and never cleaned up,
        # and Settings goes on listing it as enabled with nothing behind it.
        retired = set(config_plugins.load_used().keys()) - scanned
        if retired:
            config_plugins.remove_used_batch(sorted(retired))
            self.log.info(f"Plugins no longer shipped, dropped from the used "
                          f"list: {', '.join(sorted(retired))}")
        self.log.info(f"Plugins available updated successfully for repository {repo_id}")
