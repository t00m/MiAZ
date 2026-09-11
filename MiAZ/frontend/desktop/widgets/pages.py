# File: pages.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Welcome page and the empty documents page

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
    """What the workspace shows in place of the documents when there are none.

    It sits inside the workspace, under its toolbar, so the Add button and the
    drop target stay where they are. Two cases: the repository has no
    documents at all ('no-documents'), or the filters hide all of them
    ('no-matches'). Only the first one has an Add button of its own.
    """
    def __init__(self, app):
        super().__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.mode = None

        self.status_page = Adw.StatusPage(vexpand=True)

        # The same menu as the toolbar Add button, so an Import plugin that
        # adds an entry there adds it here too.
        self.button_add = Gtk.MenuButton()
        self.button_add.set_child(Adw.ButtonContent(
            icon_name='list-add-symbolic', label=_('Add documents')))
        self.button_add.set_halign(Gtk.Align.CENTER)
        self.button_add.add_css_class('suggested-action')
        self.button_add.add_css_class('pill')
        self.button_add.set_menu_model(self.app.get_widget('headerbar-add-menu'))
        self.status_page.set_child(self.button_add)

        self.append(self.status_page)
        self.set_mode('no-matches')

    def set_mode(self, mode):
        """Show the 'no-documents' or the 'no-matches' case."""
        if mode == self.mode:
            return
        self.mode = mode
        if mode == 'no-documents':
            self.status_page.set_icon_name('io.github.t00m.MiAZ')
            self.status_page.set_title(_("This repository has no documents yet"))
            self.status_page.set_description(_("Add documents, or drop files here"))
            self.button_add.set_visible(True)
        else:
            self.status_page.set_icon_name('io.github.t00m.MiAZ-edit-find-symbolic')
            self.status_page.set_title(_("No documents found"))
            self.status_page.set_description(
                _("Try a different search, reset filters or add new documents"))
            self.button_add.set_visible(False)

