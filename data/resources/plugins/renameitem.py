#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: renameitem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for rename documents
"""

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import get_logger


class MiAZToolbarRenameItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarRenameItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.RenameItem')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_toolbar_button)
        view = self.app.get_widget('workspace-view')
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def _on_selection_changed(self, *args):
        items = self.workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-rename')
        visible = len(items) == 1
        button.set_visible(visible)

    def add_toolbar_button(self, *args):
        if self.app.get_widget('toolbar-top-button-rename') is None:
            toolbar_top_right = self.app.get_widget('headerbar-right-box')
            button = self.factory.create_button(icon_name='com.github.t00m.MiAZ-text-editor-symbolic', callback=self.callback)
            # ~ button.get_style_context().add_class(class_name='flat')
            button.set_visible(False)
            self.app.add_widget('toolbar-top-button-rename', button)
            toolbar_top_right.append(button)

    def callback(self, *args):
        try:
            item = self.workspace.get_selected_items()[0]
            self.document_rename_single(item.id)
        except IndexError:
            self.log.debug("No item selected")

    def document_rename_single(self, doc):
        self.log.debug("Rename %s", doc)
        rename = self.app.get_widget('rename')
        rename.set_data(doc)
        self.actions.show_stack_page_by_name('rename')
