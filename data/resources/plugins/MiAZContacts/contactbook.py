# pylint: disable=E1101

"""
# File: contactbook.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Keep the details of senders and recipients
"""

import os
import sys
from gettext import gettext as _

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':        'contactbook',
    'Name':          'MiAZContacts',
    'Loader':        'Python3',
    'Description':   _('Keep the details of senders and recipients'),
    'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2026 Tomás Vírseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
    'Category':      'Documents',
    'Subcategory':   'Contacts',
    'MenuEntries':   [
        ('manage', _('Keep the details of senders and recipients')),
    ]
}

# The view this plugin registers on the documents toolbar.
VIEW_NAME = 'contacts'
VIEW_ICON = 'system-users-symbolic'


class Contacts(MiAZExtension):
    """The people and organisations the documents name.

    Every document says who sent it and who received it. This gives those
    codes a record: names, addresses, phones, emails, web, social profiles
    and bank accounts, kept as vCard so they can leave as easily as they
    arrived.
    """
    __gtype_name__ = 'MiAZContactsPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.repository = self.app.get_service('repo')
        self._store = None
        self._view = None

        source_dir = os.path.dirname(os.path.abspath(__file__))
        if source_dir not in sys.path:
            sys.path.insert(0, source_dir)

        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded',
                                                           self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if self.plugin.started():
            return
        self.plugin.install_menu_entries({'manage': self.open_manager})
        self._add_view()
        self.plugin.set_started(started=True)

    def _add_view(self):
        """Put the Contacts view beside the other views of the documents."""
        from contacts.cardview import MiAZContactsView
        self._view = MiAZContactsView(self.app, self)
        self.app.add_widget('workspace-contacts', self._view)
        self.plugin.add_workspace_view(self._view, VIEW_NAME, VIEW_ICON, _('Contacts'))

    def get_store(self):
        """The contact store of the open repository, built on first use."""
        if self._store is None:
            from contacts.store import ContactStore
            self._store = ContactStore(self.plugin.get_data_dir(), self.log)
        return self._store

    def make_manager(self):
        """A manager over this repository's store."""
        from contacts.manager import ContactManager
        return ContactManager(self.app, self)

    def open_manager(self, *args):
        """Open the list of every contact in this repository."""
        self.make_manager().present(self.app.get_widget('window'))

    def refresh_view(self):
        """Redraw the cards after the contacts changed."""
        self.get_store().load(force=True)
        if self._view is not None:
            self._view.refresh()

    def make_editor(self):
        """A fresh editor over this repository's store."""
        from contacts.editor import ContactEditor
        return ContactEditor(self.app, self.get_store())

    def open_editor(self, key, description=''):
        """Edit one contact, and redraw the cards once it is saved."""
        window = self.app.get_widget('window')
        editor = self.make_editor()
        editor.present(window, key, description, on_saved=self._on_saved)

    def _on_saved(self, contact):
        self.refresh_view()
        self.srvdlg.show_toast(
            _('Saved {name}').format(name=contact.display_name()))
