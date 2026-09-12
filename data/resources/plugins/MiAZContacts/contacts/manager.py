# File: manager.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Every contact in one list, with import, export and delete

import os
from datetime import datetime
from gettext import gettext as _
from gettext import ngettext

from gi.repository import Adw
from gi.repository import Gtk

from contacts.editor import ContactEditor
from contacts.model import Contact
from contacts.store import mint_key

# Which configurations hold the names a card can be matched against.
NAME_CONFIGS = ('SentBy', 'SentTo', 'Person')


class ContactManager:
    """The whole address book: search, edit, delete, import, export."""

    def __init__(self, app, plugin):
        self.app = app
        self.plugin = plugin
        self.log = plugin.log
        self.store = plugin.get_store()
        self.srvdlg = app.get_service('dialogs')
        self.page = Adw.PreferencesPage()
        self.page.set_hexpand(True)
        self.page.set_vexpand(True)
        self.group = Adw.PreferencesGroup()
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text(_('Search contacts'))
        self.search.connect('search-changed', lambda *args: self.refresh())
        self.group.set_header_suffix(self.search)
        self.page.add(self.group)
        self._rows = []

    def known_names(self):
        """Every name the vocabulary knows, mapped to its key.

        An imported card usually carries no MiAZ key, so the name is the only
        thing that can tie it to a party the documents already name.
        """
        names = {}
        for config_name in NAME_CONFIGS:
            config = self.app.get_config(config_name)
            if config is None:
                continue
            for key, description in config.load_available().items():
                if description:
                    names[description] = key
                names[key] = key
        return names

    def refresh(self):
        """Redraw the list, narrowed by whatever the search box says."""
        for row in self._rows:
            self.group.remove(row)
        self._rows = []
        needle = self.search.get_text().strip().lower()
        self.store.load(force=True)
        for key in self.store.keys():
            contact = self.store.get(key)
            haystack = f'{key} {contact.display_name()}'.lower()
            if needle and needle not in haystack:
                continue
            self._rows.append(self._build_row(key, contact))
            self.group.add(self._rows[-1])
        for key, error in self.store.broken().items():
            row = Adw.ActionRow(title=key)
            row.set_subtitle(_('This contact file could not be read: {error}').format(error=error))
            row.add_css_class('error')
            self._rows.append(row)
            self.group.add(row)

    def _build_row(self, key, contact):
        row = Adw.ActionRow(title=contact.display_name())
        row.set_subtitle(key)
        edit = Gtk.Button(label=_('Edit'))
        edit.set_valign(Gtk.Align.CENTER)
        edit.connect('clicked', lambda *args: self._edit(key))
        delete = Gtk.Button(label=_('Delete'))
        delete.set_valign(Gtk.Align.CENTER)
        delete.add_css_class('destructive-action')
        delete.connect('clicked', lambda *args: self._delete(key, contact))
        row.add_suffix(edit)
        row.add_suffix(delete)
        return row

    def _edit(self, key):
        window = self.app.get_widget('window')
        editor = ContactEditor(self.app, self.store)
        editor.present(window, key, on_saved=lambda contact: self._saved(contact))

    def _saved(self, contact):
        self.refresh()
        self.plugin.refresh_view()

    def _delete(self, key, contact):
        """Ask first, and say what deleting does not do."""
        window = self.app.get_widget('window')
        def responded(dialog, response, data):
            if response != 'apply':
                return
            self.store.delete(key)
            self.refresh()
            self.plugin.refresh_view()
        dialog = self.srvdlg.show_confirmation(
            title=_('Delete these details?'),
            body=_('The details of {name} are deleted. {key} stays in the '
                   'vocabulary, because documents are filed under it.').format(
                       name=contact.display_name(), key=key),
            callback=responded)
        dialog.present(window)

    def _add_to_pool(self, key, description):
        """Make a key a party MiAZ knows, so it can be picked as sender or recipient."""
        config = self.app.get_config('Person')
        if config is None:
            return
        if not config.exists_available(key):
            config.add_available(key, description)

    def import_path(self, path):
        """Read one file of cards into the store."""
        util = self.app.get_service('util')
        result = self.store.import_file(
            path, known_names=self.known_names(), valid_key=util.valid_key)
        self.store.load(force=True)
        for key in result.added:
            contact = self.store.get(key)
            self._add_to_pool(key, contact.display_name() if contact else key)
        return result

    def export_path(self, path, keys=None):
        """Write contacts to one file of cards."""
        return self.store.export_file(path, keys=keys)

    def new_contact(self, name):
        """Create a bare contact for a name with no card yet. Returns its key.

        This is the New button's entry point, but it is also the only way a
        person with no documents on screen can get a record, since the card
        view's "Add details" only reaches parties already in the current
        filter. An empty name does nothing and returns ''.
        """
        name = (name or '').strip()
        if not name:
            return ''
        util = self.app.get_service('util')
        taken = set(self.store.keys()) | set(self.known_names().values())
        key = mint_key(name, taken=taken, valid_key=util.valid_key)
        self._add_to_pool(key, name)
        self.store.save(Contact(key=key, fn=name))
        self.refresh()
        self.plugin.refresh_view()
        return key

    def _pick_new(self, *args):
        window = self.app.get_widget('window')
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        entry.set_placeholder_text(_('Name'))

        def responded(dialog, response, data):
            if response != 'apply':
                return
            key = self.new_contact(entry.get_text())
            if key:
                self._edit(key)

        dialog = self.srvdlg.create(
            dtype='action', title=_('New contact'), body=_('Name of the new contact'),
            widget=entry, callback=responded, width=420, height=160)
        dialog.present(window)

    def _pick_import(self, *args):
        window = self.app.get_widget('window')
        dialog = Gtk.FileDialog()
        dialog.set_title(_('Import contacts'))

        def chosen(source, result, data=None):
            try:
                gfile = source.open_finish(result)
            except Exception:
                return
            outcome = self.import_path(gfile.get_path())
            self.refresh()
            self.plugin.refresh_view()
            self.srvdlg.show_toast(_('{added} added, {updated} updated, {failed} failed').format(
                added=len(outcome.added), updated=len(outcome.updated),
                failed=len(outcome.failed)))

        dialog.open(window, None, chosen)

    def _pick_export(self, *args):
        window = self.app.get_widget('window')
        repository = self.app.get_service('repo')
        name = os.path.basename(repository.docs.rstrip(os.sep)) or 'miaz'
        stamp = datetime.now().strftime('%Y%m%d')
        dialog = Gtk.FileDialog()
        dialog.set_title(_('Export contacts'))
        dialog.set_initial_name(f'contacts-{name}-{stamp}.vcf')

        def chosen(source, result, data=None):
            try:
                gfile = source.save_finish(result)
            except Exception:
                return
            written = self.export_path(gfile.get_path())
            self.srvdlg.show_toast(ngettext(
                '{count} contact exported', '{count} contacts exported',
                written).format(count=written))

        dialog.save(window, None, chosen)

    def present(self, parent):
        """Open the manager."""
        self.refresh()
        window = Gtk.ScrolledWindow()
        window.set_hexpand(True)
        window.set_vexpand(True)
        window.set_child(self.page)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.set_halign(Gtk.Align.CENTER)
        bar.set_margin_top(6)
        for label, handler in ((_('New'), self._pick_new),
                               (_('Import'), self._pick_import),
                               (_('Export'), self._pick_export)):
            button = Gtk.Button(label=label)
            button.connect('clicked', handler)
            bar.append(button)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_hexpand(True)
        box.set_vexpand(True)
        box.append(window)
        box.append(bar)

        dialog = self.srvdlg.show_noop(
            title=_('Contacts'),
            body=ngettext('{count} contact', '{count} contacts',
                          len(self.store.keys())).format(count=len(self.store.keys())),
            widget=box, width=780, height=660)
        self.app.add_widget('contacts-dialog', dialog)
        dialog.present(parent)
        return dialog
