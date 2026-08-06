#!/usr/bin/python3
# File: doctabs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Registry of the extra tabs shown by the single-document rename
#              dialog. Plugins register a tab here; the dialog asks for the
#              registrations when it is built.
#
# The dialog is constructed fresh on every rename, so a registry (rather than a
# signal each plugin has to connect and disconnect) keeps "this plugin offers a
# tab" independent from "a dialog exists right now".
#
# A registration is a plain dict:
#   owner      plugin name, so every tab of a plugin can be dropped at once
#   name       identifier of the page inside the view stack
#   title      visible label
#   factory    callable(app) -> Gtk.Widget, called once per dialog
#   icon_name  optional icon for the view switcher
#   weight     sort key; Fields is always first, plugins follow by weight

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class MiAZDocumentTabs(GObject.GObject):
    """Tabs contributed to the rename dialog by plugins."""
    __gtype_name__ = 'MiAZDocumentTabs'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.DocumentTabs')
        self._tabs = {}

    def register(self, owner, name, title, factory, icon_name=None, weight=100):
        """Add a tab, replacing any earlier one with the same name.

        Replacing rather than appending means a plugin that activates twice
        cannot end up contributing the same tab twice.
        """
        if not callable(factory):
            self.log.error(f"Tab '{name}' from '{owner}' has no callable factory")
            return
        if name in self._tabs:
            self.log.debug(f"Tab '{name}' re-registered by '{owner}'")
        self._tabs[name] = {
            'owner': owner,
            'name': name,
            'title': title,
            'factory': factory,
            'icon_name': icon_name,
            'weight': weight,
        }
        self.log.debug(f"Tab '{name}' registered by '{owner}'")

    def unregister(self, name):
        if self._tabs.pop(name, None) is not None:
            self.log.debug(f"Tab '{name}' unregistered")

    def unregister_all(self, owner):
        """Drop every tab of a plugin, called when it is deactivated."""
        for name in [key for key, tab in self._tabs.items() if tab['owner'] == owner]:
            del self._tabs[name]
            self.log.debug(f"Tab '{name}' unregistered with '{owner}'")

    def get_registrations(self):
        """Registrations in display order."""
        return sorted(self._tabs.values(), key=lambda tab: (tab['weight'], tab['title']))

    def count(self):
        return len(self._tabs)
