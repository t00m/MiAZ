#!/usr/bin/python3

"""
# File: miazaichat.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin to chat about the selected document with an AI provider
#              (Claude, OpenAI, Gemini, Ollama). When MiAZNotes is active, a
#              question and its answer can be saved as a note.
"""

import os
import sys
from gettext import gettext as _

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

from miazaic.providers import build_registry
from miazaic.ui.settings import AIChatSettings
from miazaic.ui.chat import MiAZAIChatDialog

plugin_info = {
    'Module':      'miazaichat',
    'Name':        'MiAZAIChat',
    'Loader':      'Python3',
    'Description': _('Ask questions about the selected document and get answers in a chat'),
    'Authors':     'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':   'Copyright © 2026 Tomás Vírseda',
    'Version':     '0.1.0',
    'Category':    'Artificial Intelligence',
    'Subcategory': 'AI Assistants',
}


class MiAZAIChatPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZAIChatPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()

        self.actions = self.app.get_service('actions')
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.factory = self.app.get_service('factory')

        self.registry = build_registry(self.plugin, self.log)
        self._settings_dialog = AIChatSettings(
            self.app, self.plugin, self.registry, self.log)

        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect(
                'workspace-loaded', self.startup)

    def startup(self, *_args):
        if self.plugin.started():
            return
        mnu = self.factory.create_menuitem(
            name=self.plugin.get_menu_item_name(),
            label=_('Chat with document…'),
            callback=self._on_chat,
        )
        self.plugin.install_menu_entry(mnu)
        self.plugin.set_started(True)

    def _on_chat(self, *_args):
        items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug('No items selected')
            return
        # Chat is per document: use the first selected one.
        item = items[0]
        dialog = MiAZAIChatDialog(
            self.app, item.id, self.registry, self.plugin, self.log)
        dialog.set_transient_for(self.workspace.get_root())
        dialog.present()

    def show_settings(self, widget=None):
        parent = widget if widget is not None else self.app.get_widget('window')
        self._settings_dialog.present(parent)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            try:
                self.workspace.disconnect(self._startup_handler)
            except Exception as exc:
                self.log.debug(f'disconnect startup handler: {exc}')
            del self._startup_handler
        self.plugin.set_started(False)
