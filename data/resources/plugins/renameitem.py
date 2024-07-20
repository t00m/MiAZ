#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: renameitem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for rename documents
"""

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZToolbarRenameItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarRenameItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.RenameItem')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_toolbar_button)
        view = self.app.get_widget('workspace-view')
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def _on_selection_changed(self, *args):
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-rename')
        visible = len(items) == 1
        button.set_visible(visible)

    def add_toolbar_button(self, *args):
        if self.app.get_widget('toolbar-top-button-rename') is None:
            factory = self.app.get_service('factory')
            toolbar_top_right = self.app.get_widget('headerbar-right-box')
            button = factory.create_button(icon_name='io.github.t00m.MiAZ-text-editor-symbolic', callback=self.callback)
            button.set_visible(False)
            self.app.add_widget('toolbar-top-button-rename', button)
            toolbar_top_right.append(button)

    def callback(self, *args):
        try:
            workspace = self.app.get_widget('workspace')
            item = workspace.get_selected_items()[0]
            self.document_rename_single(item.id)
        except IndexError:
            self.log.debug("No item selected")

    def document_rename_single(self, doc):
        self.log.debug(f"Rename {doc}")
        actions = self.app.get_service('actions')
        rename = self.app.get_widget('rename')
        rename.set_data(doc)
        actions.show_stack_page_by_name('rename')
