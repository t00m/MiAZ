#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZToolbarViewItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarViewItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.ViewItem')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.add_toolbar_button)
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
        if self.app.get_widget('toolbar-top-button-view') is None:
            toolbar_top_right = self.app.get_widget('headerbar-right-box')
            button = self.factory.create_button(icon_name='com.github.t00m.MiAZ-view-document', callback=self.callback)
            # ~ button.get_style_context().add_class(class_name='flat')
            button.set_visible(False)
            self.app.add_widget('toolbar-top-button-view', button)
            toolbar_top_right.append(button)

    def callback(self, *args):
        try:
            item = self.workspace.get_selected_items()[0]
            self.actions.document_display(item.id)
        except IndexError:
            self.log.debug("No item selected")
