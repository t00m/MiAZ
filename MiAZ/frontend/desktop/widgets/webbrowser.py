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
        # Create the WebKit WebView
        self.webview = WebKit.WebView()
        self.app.add_widget('webbrowser-view', self.webview)

        # Navigation bar
        self.header = self.app.add_widget('webbrowser-headerbar', Gtk.HeaderBar())


        # ~ self.back_button = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        # ~ self.back_button.connect("clicked", self.on_back_clicked)
        # ~ self.header.pack_start(self.back_button)

        # ~ self.forward_button = Gtk.Button.new_from_icon_name("go-next-symbolic")
        # ~ self.forward_button.connect("clicked", self.on_forward_clicked)
        # ~ self.header.pack_start(self.forward_button)

        # ~ self.address_entry = Gtk.Entry()
        # ~ self.address_entry.set_placeholder_text("Enter URL...")
        # ~ self.address_entry.connect("activate", self.on_url_entered)
        # ~ self.header.pack_end(self.address_entry)

        self.append(self.header)
        self.append(self.webview)

        self.set_vexpand(True)

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
        if not url.startswith("http"):
            url = "https://" + url
        self.webview.load_uri(url)
