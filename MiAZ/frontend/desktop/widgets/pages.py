#!/usr/bin/python3
# File: about.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Welcome widget

from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Adw

class MiAZWelcome(Gtk.Box):
    """
    About class
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        ENV = self.app.get_env()
        centerbox = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
        centerbox.set_vexpand(True)
        centerbox.set_hexpand(True)
        self.append(centerbox)

        vbox = self.factory.create_box_vertical(spacing=24, hexpand=True, vexpand=False)
        centerbox.set_center_widget(vbox)

        label = Gtk.Label.new(_(f"Welcome to {ENV['APP']['shortname']}!"))
        label.get_style_context().add_class(class_name='title-1')
        vbox.append(label)
        label = Gtk.Label()
        label.get_style_context().add_class(class_name='title-3')
        label.set_markup(_('No active repositories have been found\n'))
        vbox.append(label)

        button = self.factory.create_button(title='Manage repositories')
        button.set_valign(Gtk.Align.CENTER)
        button.set_halign(Gtk.Align.CENTER)
        button.connect('clicked', self.actions.show_app_settings)
        vbox.append(button)


class MiAZPageNotFound(Gtk.Box):
    """
    Page displayed when no docs are available in current view
    """
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')

        status_page = Adw.StatusPage(
            title=_("No documents found"),
            description=_(f"<big>Try a different search, reset filters or add new documents</big>"),
            icon_name="io.github.t00m.MiAZ-edit-find-symbolic",
            vexpand=True,
        )

        self.append(status_page)

