#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: button.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom popover button
"""

from gettext import gettext as _

import gi
from gi.repository import Gtk


class MiAZPopoverButton(Gtk.Box):
    """Custom Popover Button"""
    def __init__(self, app, icon_name: str = '', title: str = '', css_classes: list = [], widgets: list = []):
        super(Gtk.Box, self).__init__(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        self.app = app
        ENV = app.get_env()
        self.icon_name = icon_name
        self.title = title
        self.css_classes = css_classes
        self.widgets = widgets
        self.build_ui()

    def build_ui(self):
        self.set_margin_start(0)
        self.set_margin_end(0)
        self.set_margin_top(0)
        self.set_margin_bottom(0)
        self.listbox = Gtk.ListBox.new()
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        for widget in self.widgets:
            self.listbox.append(child=widget)
        vbox = self.app.factory.create_box_vertical(spacing=0, margin=0, hexpand=False, vexpand=False)
        vbox.append(child=self.listbox)
        self.popover = Gtk.Popover()
        self.popover.set_child(vbox)
        self.popover.present()
        self.button = Gtk.MenuButton(child=self.app.factory.create_button_content(icon_name=self.icon_name, title=self.title, css_classes=self.css_classes))
        self.button.set_popover(self.popover)
        self.append(self.button)

    def add_widget(self, widget: Gtk.Widget):
        self.listbox.append(child=widget)

    def remove_widget(self, widget: Gtk.Widget):
        self.listbox.remove(child=widget)

    def set_has_frame(self, has_frame: bool = False):
        self.button.set_has_frame(has_frame)