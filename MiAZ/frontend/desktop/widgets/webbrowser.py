#!/usr/bin/python
# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Webbrowser widget

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, Adw, WebKit, Gio

from MiAZ.backend.log import MiAZLog

class MiAZWebBrowser(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.app = app
        self.log = MiAZLog('MiAZ.WebBrowser')
        self._build_ui()
        self.log.debug(f"{__class__.__name__} initialited")
        self.app.add_widget('webbrowser', self)

    def _build_ui(self):
        self.webview = self.app.add_widget('webbrowser-view', WebKit.WebView())
        self.append(self.webview)
        self.webview.set_vexpand(True)
        self.webview.set_hexpand(True)

    def on_back_clicked(self, _):
        if self.webview.can_go_back():
            self.webview.go_back()

    def on_forward_clicked(self, _):
        if self.webview.can_go_forward():
            self.webview.go_forward()

    def on_url_entered(self, entry):
        url = entry.get_text()
        if not url.startswith("http"):
            url = "https://" + url
        self.webview.load_uri(url)

    def load_url(self, url):
        # ~ if not url.startswith("http"):
            # ~ url = "https://" + url
        self.webview.load_uri(url)
        self.log.debug(f"Remote resource '{url}' loaded")

    def load_file(self, url):
        if not url.startswith('file://'):
            url = "file://" + url
        self.webview.load_uri(url)
        self.log.debug(f"Local resource '{url}' loaded")
