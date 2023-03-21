#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import tempfile

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger


class MiAZToolbarViewItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarViewItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.ViewItem')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_actions()
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.util = self.backend.util
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-toolbar-top", self.add_toolbar_button)
        view = self.app.get_widget('workspace-view')
        view.cv.connect("activate", self.callback)
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def _on_selection_changed(self, *args):
        items = self.workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-view')
        visible = len(items) == 1
        button.set_visible(visible)

    def add_toolbar_button(self, *args):
        toolbar_top_right = self.app.get_widget('workspace-toolbar-top-right')
        button = self.factory.create_button(icon_name='miaz-display', callback=self.callback)
        button.set_visible(False)
        self.app.add_widget('toolbar-top-button-view', button)
        toolbar_top_right.prepend(button)

    def callback(self, *args):
        try:
            item = self.workspace.get_selected_items()[0]
            self.actions.document_display(item.id)
        except IndexError:
            self.log.debug("No item selected")
