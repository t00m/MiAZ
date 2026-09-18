"""
# File: shortcuts.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: One registry for every keyboard shortcut, core and plugin
"""

from collections import namedtuple

from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog


def N_(message: str) -> str:
    """Mark a string for translation without translating it yet.

    The table below is built at import time, before a locale has been chosen,
    so it stores msgids. gettext is applied when the Keyboard Shortcuts window
    is built, which is what lets that window follow the language in use rather
    than the one loaded first. xgettext still collects these strings: po builds
    through meson's glib preset, which passes --keyword=N_.
    """
    return message


# Section names, as msgids. This is also the order the window shows them in.
SECTION_APPLICATION = N_('Application')
SECTION_DOCUMENTS = N_('Documents')
SECTION_VIEWS = N_('Views')
SECTION_WORKSPACE = N_('Workspace')
SECTION_PLUGINS = N_('Plugins')

SECTION_ORDER = (SECTION_APPLICATION, SECTION_DOCUMENTS, SECTION_VIEWS,
                 SECTION_WORKSPACE, SECTION_PLUGINS)

# Where a shortcut is installed.
#
# GLOBAL goes on the application with set_accels_for_action and fires wherever
# focus is. LIST goes on the document list through a Gtk.ShortcutController
# with LOCAL scope and fires only while that list has focus.
#
# The distinction exists for Delete. MiAZ has a search entry that can hold
# focus, and a global Delete that removed documents while somebody was editing
# a filter would be a data loss bug.
GLOBAL = 'global'
LIST = 'list'

# Combinations the desktop or a GTK text entry already owns. Nothing in CORE
# may take one. Five of these were bound by MiAZ before this work:
# Ctrl+S, Ctrl+Insert, Shift+Insert, Ctrl+BackSpace and Ctrl+Delete.
RESERVED = (
    '<Control>BackSpace',   # delete the previous word, in any text entry
    '<Control>Delete',      # delete the next word, in any text entry
    '<Control>Insert',      # copy
    '<Shift>Insert',        # paste
    '<Control>s',           # save
    '<Control>o',           # open
    '<Control>p',           # print
    '<Control>w',           # close
    '<Control>c',           # copy
    '<Control>x',           # cut
    '<Control>v',           # paste
    '<Control>z',           # undo
    'F11',                  # fullscreen
)

# (section, label msgid, action name, accelerator, scope)
CORE = (
    (SECTION_APPLICATION, N_('Settings'), 'app-settings', '<Control>comma', GLOBAL),
    (SECTION_APPLICATION, N_('Repository management'), 'repo-management', '<Control>r', GLOBAL),
    (SECTION_APPLICATION, N_('Repository settings'), 'repo-settings', '<Control><Shift>r', GLOBAL),
    (SECTION_APPLICATION, N_('Keyboard shortcuts'), 'app-shortcuts', '<Control>question', GLOBAL),
    (SECTION_APPLICATION, N_('Help'), 'app-help', 'F1', GLOBAL),
    (SECTION_APPLICATION, N_('Main menu'), 'app-menu', 'F10', GLOBAL),
    (SECTION_APPLICATION, N_('Quit'), 'app-quit', '<Control>q', GLOBAL),

    (SECTION_DOCUMENTS, N_('Add new document(s)'), 'import-doc', '<Control>i', GLOBAL),
    (SECTION_DOCUMENTS, N_('Add documents from a directory'), 'import-dir', '<Control><Shift>i', GLOBAL),
    (SECTION_DOCUMENTS, N_('Open document'), 'document-open', 'Return', LIST),
    (SECTION_DOCUMENTS, N_('Rename document'), 'document-rename', 'F2', LIST),
    (SECTION_DOCUMENTS, N_('Delete documents'), 'document-delete', 'Delete', LIST),
    (SECTION_DOCUMENTS, N_('Select all documents'), 'document-select-all', '<Control>a', LIST),
    (SECTION_DOCUMENTS, N_('Copy document names'), 'copy-document-names', '<Control><Shift>c', GLOBAL),
    (SECTION_DOCUMENTS, N_('Mass renaming'), 'massrename-open', '<Control>m', GLOBAL),
    (SECTION_DOCUMENTS, N_('Create a new note'), 'notes-doc', '<Control>n', GLOBAL),
    (SECTION_DOCUMENTS, N_('See all notes'), 'notes-all', '<Control><Shift>n', GLOBAL),

    (SECTION_VIEWS, N_('Details'), 'view-details', '<Control>1', GLOBAL),
    (SECTION_VIEWS, N_('Grid'), 'view-grid', '<Control>2', GLOBAL),
    (SECTION_VIEWS, N_('Timeline'), 'view-timeline', '<Control>3', GLOBAL),
    (SECTION_VIEWS, N_('Conversations'), 'view-conversation', '<Control>4', GLOBAL),
    (SECTION_VIEWS, N_('Filenames'), 'view-filenames', '<Control>5', GLOBAL),

    (SECTION_WORKSPACE, N_('Search in all fields'), 'search-focus', '<Control>f', GLOBAL),
    (SECTION_WORKSPACE, N_('Search in Concept field'), 'search-focus-concept', '<Control><Shift>f', GLOBAL),
    (SECTION_WORKSPACE, N_('Clear all filters'), 'filters-clear', 'Escape', LIST),
    (SECTION_WORKSPACE, N_('Toggle sidebar'), 'sidebar-toggle', 'F9', GLOBAL),
    (SECTION_WORKSPACE, N_('Toggle document preview'), 'preview-toggle', 'F8', GLOBAL),
    (SECTION_WORKSPACE, N_('Choose the columns to show'), 'columns-choose', '<Control><Shift>k', GLOBAL),
)

Binding = namedtuple('Binding',
                     'owner action accelerator label section scope')


class MiAZShortcuts:
    """Every keyboard shortcut in MiAZ, and who holds it.

    One accelerator, one owner. The first claim wins and a later one is
    refused, logged and recorded in conflicts(). First rather than last
    because the core table registers at startup, before any plugin loads, so
    a plugin can never quietly take a key out from under the application and
    leave the Keyboard Shortcuts window telling the user something untrue.

    Keys are compared parsed, never as strings: the codebase contains both
    '<Ctrl>N' and '<Control>n', and string comparison would call those two
    different keys and let a real collision through.
    """

    def __init__(self, app=None):
        self.app = app
        self.log = MiAZLog('MiAZ.Shortcuts')
        # (keyval, mods) -> Binding
        self._held = {}
        # owner -> [(keyval, mods)]
        self._owned = {}
        self._conflicts = []

    def register(self, owner: str, action: str, accelerator: str,
                 label: str = '', section: str = SECTION_PLUGINS,
                 scope: str = GLOBAL) -> bool:
        """Claim one accelerator. True when granted, False when refused."""
        key = self._parse(accelerator)
        if key is None:
            self.log.warning(f"'{owner}' asked for '{accelerator}' on "
                             f"'{action}', which GTK cannot parse")
            return False
        held = self._held.get(key)
        if held is not None:
            if held.owner == owner and held.action == action:
                # Menus are rebuilt whenever plugins load or unload, so the
                # same claim arriving twice is ordinary, not a conflict.
                return True
            self._conflicts.append({
                'owner': owner, 'action': action,
                'accelerator': accelerator,
                'held_by': held.owner, 'held_action': held.action})
            self.log.warning(
                f"'{owner}' asked for '{accelerator}' on '{action}', but "
                f"'{held.owner}' already holds it for '{held.action}'. The "
                "menu entry still works with the mouse.")
            return False
        binding = Binding(owner, action, accelerator, label, section, scope)
        self._held[key] = binding
        self._owned.setdefault(owner, []).append(key)
        return True

    def register_core(self) -> None:
        """Load the core table. Called once, before any plugin can load."""
        for section, label, action, accelerator, scope in CORE:
            self.register('core', action, accelerator, label=label,
                          section=section, scope=scope)

    def unregister_owner(self, owner: str) -> None:
        """Release everything one owner holds, so its keys are free again."""
        for key in self._owned.pop(owner, []):
            self._held.pop(key, None)

    def accelerators_for(self, action: str) -> list:
        """What to hand set_accels_for_action for this action.

        Global scope only. A list scoped key is installed on the document
        list, so giving it to the application here would make it fire
        everywhere, which is the whole thing that scoping prevents.
        """
        return [binding.accelerator for binding in self._held.values()
                if binding.action == action and binding.scope == GLOBAL]

    def bindings(self, scope: str = None) -> list:
        """Every binding, in section order, then in registration order."""
        held = [b for b in self._held.values()
                if scope is None or b.scope == scope]
        order = {name: index for index, name in enumerate(SECTION_ORDER)}
        return sorted(held, key=lambda b: order.get(b.section, len(order)))

    def conflicts(self) -> list:
        """Every refusal, as dicts naming both sides. Empty is the goal."""
        return list(self._conflicts)

    @staticmethod
    def _parse(accelerator: str):
        """(keyval, mods), or None when GTK cannot read it."""
        try:
            ok, key, mods = Gtk.accelerator_parse(accelerator)
        except (TypeError, ValueError):
            return None
        return (key, mods) if ok else None
