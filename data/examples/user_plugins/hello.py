#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Example of MiAZuser plugin
"""

import tempfile
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog


class MiAZToolbarHelloItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarHelloItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.HelloItem')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-toolbar-top", self.add_toolbar_button)
        view = self.app.get_widget('workspace-view')
        view.cv.connect("activate", self.callback)
        selection = view.get_selection()
        # ~ selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    # ~ def _on_selection_changed(self, *args):
        # ~ items = self.workspace.get_selected_items()
        # ~ button = self.app.get_widget('toolbar-top-button-hello')
        # ~ visible = len(items) == 1
        # ~ button.set_visible(True)

    def add_toolbar_button(self, *args):
        if self.app.get_widget('toolbar-top-button-hello') is None:
            toolbar_top_right = self.app.get_widget('headerbar-right-box')
            button = self.factory.create_button(icon_name='help-faq', callback=self.callback)
            button.set_visible(True)
            self.app.add_widget('toolbar-top-button-hello', button)
            toolbar_top_right.append(button)

    def callback(self, *args):
        window = self.app.get_widget('window')
        dtype = 'info'
        title = "Hello World!"
        text = ''
        dialog = CustomDialog(app=self.app, parent=window, use_header_bar=True, dtype=dtype, title=title, text=text)
        dialog.set_modal(True)
        dialog.show()
