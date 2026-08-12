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

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_halign(Gtk.Align.CENTER)

        # Primary action: the guided first-run assistant.
        button_setup = self.factory.create_button(title=_('Set up a repository'))
        button_setup.set_halign(Gtk.Align.CENTER)
        button_setup.add_css_class('suggested-action')
        button_setup.add_css_class('pill')
        button_setup.connect('clicked', self.actions.show_repository_assistant)
        box.append(button_setup)

        # Secondary action: the advanced repository manager.
        button_manage = self.factory.create_button(title=_('Manage repositories'))
        button_manage.set_halign(Gtk.Align.CENTER)
        button_manage.add_css_class('flat')
        button_manage.connect('clicked', self.actions.show_repository_manager)
        box.append(button_manage)

        status_page.set_child(box)

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
            description=_("Try a different search, reset filters or add new documents"),
            icon_name="io.github.t00m.MiAZ-edit-find-symbolic",
            vexpand=True,
        )

        self.append(status_page)

