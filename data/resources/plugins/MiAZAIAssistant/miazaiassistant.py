#!/usr/bin/python3

"""
# File: miazaiassistant.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin that suggests MiAZ filename fields from document content
#              using configurable AI providers (Claude, OpenAI, Gemini, Ollama).
"""

import os
import sys
from gettext import gettext as _

from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

from miazai.providers import build_registry
from miazai.ui.settings import AIAssistantSettings
from miazai.ui.dialog import inject_suggest_button, remove_suggest_button

plugin_info = {
    'Module':      'miazaiassistant',
    'Name':        'MiAZAIAssistant',
    'Loader':      'Python3',
    'Description': _('Suggest filename fields from document content using an AI provider'),
    'Authors':     'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':   'Copyright © 2026 Tomás Vírseda',
    'Version':     '0.1.0',
    'Category':    'Artificial Intelligence',
    'Subcategory': 'AI Assistants',
}


class MiAZAIAssistantPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZAIAssistantPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()

        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.factory = self.app.get_service('factory')
        self.dialogs = self.app.get_service('dialogs')

        self.registry = build_registry(self.plugin, self.log)
        self._settings_dialog = AIAssistantSettings(
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
            label=_('Suggest filename…'),
            callback=self._on_suggest_clicked,
        )
        self.plugin.install_menu_entry(mnu)

        inject_suggest_button(
            self.app, self.registry, self.repository, self.util, self.log)

        self.plugin.set_started(True)

    def _on_suggest_clicked(self, *_args):
        actions = self.app.get_service('actions')
        actions.document_rename()

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

        remove_suggest_button(self.app)
        self.plugin.set_started(False)
