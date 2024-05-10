#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: statusbar.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Simple statusbar widget
"""

from gi.repository import Gtk


class MiAZStatusbar(Gtk.Box):
    def __init__(self, app):
        self.app = app
        self.factory = self.app.get_service('factory')
        super(MiAZStatusbar, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False, spacing=3)
        self.set_margin_top(margin=0)
        self.set_margin_bottom(margin=6)
        self.set_margin_start(margin=6)
        self.set_margin_end(margin=6)
        self.get_style_context().add_class(class_name='linked')
        self.get_style_context().add_class(class_name='osd')
        self.get_style_context().add_class(class_name='monospace')
        self.get_style_context().add_class(class_name='toolbar')
        self.get_style_context().add_class(class_name='linked')

        # Separator
        # ~ separator = Gtk.Separator.new(orientation=Gtk.Orientation.HORIZONTAL)
        # ~ self.append(separator)

        hbox = self.factory.create_box_horizontal(margin=0, spacing=6, hexpand=True, vexpand=False)
        self.app.add_widget('statusbar-hbox', hbox)

        self.label_message = self.factory.create_label(text='Welcome to MiAZ')
        self.app.add_widget('statusbar-label-message', self.label_message)
        self.label_message.set_xalign(0.0)
        self.label_message.set_hexpand(True)
        hbox.append(self.label_message)

        self.label_repo = self.factory.create_label()
        self.app.add_widget('statusbar-label-repo', self.label_repo)
        self.label_repo.set_xalign(0.0)
        self.label_repo.set_hexpand(False)
        self.label_repo.set_xalign(1.0)
        hbox.append(self.label_repo)

        self.append(hbox)

    def message(self, text: str) -> None:
        self.label_message.set_markup(text)

    def repo(self, name: str) -> None:
        self.label_repo.set_text('[%s]' % name)


