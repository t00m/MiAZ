#!/usr/bin/python3
# File: window.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom Window widget

from gi.repository import Gdk, Gtk

from MiAZ.backend.log import MiAZLog


class MiAZCustomWindow(Gtk.Window):

    def __init__(self, app, name, title, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.name = name
        self.title = title
        self.set_title(title)
        logname = f"Miaz.{name.replace('-', '.').title()}"
        self.log = MiAZLog(logname)
        self.app.add_widget(f'window-{name}', self)
        self.connect('close-request', self._on_window_close_request)
        evk = Gtk.EventControllerKey.new()
        self.add_controller(evk)
        evk.connect("key-pressed", self._on_key_press)

        self._get_services()
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        headerbar = self.app.add_widget(f'window-{self.name}-headerbar', Gtk.HeaderBar())
        self.set_titlebar(headerbar)
        self.mainbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.set_child(self.mainbox)

    def _get_services(self):
        self.icman = self.app.get_service('icons')
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.config = self.app.get_config_dict()

    def _on_window_close_request(self, window):
        window.hide()

    def _on_key_press(self, event, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            self.hide()

    def _build_ui(self):
        pass

