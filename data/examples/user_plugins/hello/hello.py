#!/usr/bin/python3

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Example of MiAZuser plugin
"""

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
        # ~ API = self.object
        self.app = self.object.app
        self.factory = self.app.get_service('factory')
        view = self.app.get_widget('workspace-view')
        self.add_toolbar_button()

    def do_deactivate(self):
        # Remove button
        toolbar = self.app.get_widget('headerbar-right-box')
        button = self.app.get_widget('toolbar-top-button-hello')
        toolbar.remove(button)
        self.app.remove_widget('toolbar-top-button-hello')

    def add_toolbar_button(self, *args):
        button = self.app.get_widget('toolbar-top-button-hello')
        if button is None:
            toolbar_top_right = self.app.get_widget('headerbar-right-box')
            button = self.factory.create_button(icon_name='help-faq', callback=self.callback)
            button.set_visible(True)
            self.app.add_widget('toolbar-top-button-hello', button)
            toolbar_top_right.append(button)
        else:
            button.set_visible(True)

    def callback(self, *args):
        window = self.app.get_widget('window')
        dtype = 'info'
        title = "Hello World!"
        text = 'This an example'
        dialog = CustomDialog(app=self.app, parent=window, use_header_bar=True, dtype=dtype, title=title, text=text)
        dialog.set_modal(True)
        dialog.show()
