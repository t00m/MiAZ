#!/usr/bin/python3
# File: pages.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Welcome widget

from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Adw

class MiAZWelcome(Gtk.Box):
    """Welcome / empty state shown when no active repository is available."""
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        ENV = self.app.get_env()

        status_page = Adw.StatusPage(
            icon_name='io.github.t00m.MiAZ',
            title=_("Welcome to {shortname}").format(shortname=ENV['APP']['shortname']),
            description=_("No active repositories have been found"),
            vexpand=True,
            hexpand=True,
        )

        button = self.factory.create_button(title=_('Manage Repositories'))
        button.set_halign(Gtk.Align.CENTER)
        button.add_css_class('suggested-action')
        button.add_css_class('pill')
        button.connect('clicked', self.actions.show_repository_manager)
        status_page.set_child(button)

        self.append(status_page)


class MiAZPageNotFound(Gtk.Box):
    """
    Page displayed when no docs are available in current view
    """
    def __init__(self, app):
        super().__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')

        status_page = Adw.StatusPage(
            title=_("No documents found"),
            description=_("<big>Try a different search, reset filters or add new documents</big>"),
            icon_name="io.github.t00m.MiAZ-edit-find-symbolic",
            vexpand=True,
        )

        self.append(status_page)

