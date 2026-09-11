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

    The workspace hides its toolbar while this page is up, so the page carries
    the two actions that lead somewhere from an empty view: Add, and Review
    when documents are waiting for it.
    """
    def __init__(self, app):
        super().__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        self.status_page = Adw.StatusPage(
            title=_("No documents found"),
            description=_("Try a different search, reset filters or add new documents"),
            icon_name="io.github.t00m.MiAZ-edit-find-symbolic",
            vexpand=True,
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_halign(Gtk.Align.CENTER)

        # The same menu as the toolbar Add button, so every enabled Import
        # plugin (scanner, ZIP file) has its entry here too.
        self.button_add = Gtk.MenuButton()
        self.button_add.set_child(Adw.ButtonContent(
            icon_name='list-add-symbolic', label=_('Add documents')))
        self.button_add.add_css_class('suggested-action')
        self.button_add.add_css_class('pill')
        self.button_add.set_menu_model(self.app.get_widget('headerbar-add-menu'))
        box.append(self.button_add)

        # A new document usually lands in Review, which leaves the view empty,
        # and the Review toggle is on the hidden toolbar. This button stands in
        # for it: shown when the toggle is, pressing it turns the toggle on.
        self.button_review = Gtk.Button()
        self.button_review.add_css_class('pill')
        self.button_review.connect('clicked', self._on_review_clicked)
        box.append(self.button_review)
        self._review_toggle = self.app.get_widget('workspace-togglebutton-pending-docs')
        if self._review_toggle is not None:
            self._review_toggle.connect('notify::visible', self._sync_review_button)
            self._review_toggle.connect('notify::active', self._sync_review_button)
        self.set_review_count(0)
        self._sync_review_button()

        self.status_page.set_child(box)
        self.append(self.status_page)

    def set_review_count(self, count):
        """Say how many documents are waiting for review."""
        self.button_review.set_label(_("Review ({review})").format(review=count))

    def _sync_review_button(self, *args):
        toggle = self._review_toggle
        visible = toggle is not None and toggle.get_visible() and not toggle.get_active()
        self.button_review.set_visible(visible)

    def _on_review_clicked(self, *args):
        if self._review_toggle is not None:
            self._review_toggle.set_active(True)

