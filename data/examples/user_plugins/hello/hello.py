#!/usr/bin/python3

"""
# File: hello.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Example of MiAZuser plugin
"""

import os
import html

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog


class MiAZToolbarHelloItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarHelloItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.HelloItem')

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
        utils = self.app.get_service('util')
        pm = self.app.get_service('plugin-manager')
        plugin_name, module_ext = utils.filename_details(__file__)
        plugin = pm.get_plugin_info(plugin_name)
        self.log.debug(dir(plugin))
        ENV = self.app.get_env()
        PLUGRES = os.path.join(ENV['LPATH']['PLUGRES'], plugin_name)
        CSS = 'noprint.css'
        CSS_EXISTS = os.path.exists(os.path.join(PLUGRES, 'css', CSS))
        srvdlg = self.app.get_service('dialogs')
        window = self.app.get_widget('window')
        dtype = 'info'
        title = "Hello World!"
        text = "<big>"
        text += f"<b>Plugin</b>: {plugin.get_name()} v{plugin.get_version()}\n"
        text += f"<b>Author(s)</b>:  {html.escape(', '.join(plugin.get_authors()))}\n"
        text += f"<b>Copyright</b>: {plugin.get_copyright()}"
        text += "</big>"
        # ~ text = f'CSS file exists? {CSS_EXISTS}'
        dialog = srvdlg.create(parent=window, dtype=dtype, title=title, body=text)
        dialog.show()
