# File: editor.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Edit one contact: the fields, the repeats, the bank accounts

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from contacts import iban as ibanlib
from contacts.model import Account, Address, Contact, Entry

# The type a repeated value can carry, per kind of field.
TYPES = {
    'phone': ('cell', 'work', 'home', 'fax', 'voice'),
    'email': ('home', 'work'),
    'url': ('home', 'work'),
    'social': ('mastodon', 'linkedin', 'x', 'facebook', 'instagram', 'other'),
    'address': ('home', 'work', 'postal'),
}


class EntryRow(Adw.ActionRow):
    """One repeated value: its type, the value, preferred, and a way out."""

    def __init__(self, kind, entry, on_remove):
        super().__init__()
        self.kind = kind
        self.dropdown = Gtk.DropDown.new_from_strings(list(TYPES[kind]))
        self.dropdown.set_valign(Gtk.Align.CENTER)
        if entry.type in TYPES[kind]:
            self.dropdown.set_selected(TYPES[kind].index(entry.type))
        self.entry = Gtk.Entry()
        self.entry.set_valign(Gtk.Align.CENTER)
        self.entry.set_hexpand(True)
        self.entry.set_width_chars(26)
        self.entry.set_text(entry.value)
        self.check = Gtk.CheckButton()
        self.check.set_valign(Gtk.Align.CENTER)
        self.check.set_tooltip_text(_('Preferred'))
        self.check.set_active(entry.pref)
        remove = Gtk.Button(icon_name='list-remove-symbolic')
        remove.set_valign(Gtk.Align.CENTER)
        remove.add_css_class('flat')
        remove.set_tooltip_text(_('Remove'))
        remove.connect('clicked', lambda *args: on_remove(self))
        self.add_prefix(self.dropdown)
        self.add_suffix(self.entry)
        self.add_suffix(self.check)
        self.add_suffix(remove)

    def value(self):
        return Entry(type=TYPES[self.kind][self.dropdown.get_selected()],
                     value=self.entry.get_text().strip(),
                     pref=self.check.get_active())


class AddressRow(Adw.ExpanderRow):
    """One postal address, in the components vCard keeps it in."""

    FIELDS = (('street', _('Street')), ('extended', _('Extended')),
              ('po_box', _('PO box')), ('locality', _('Town')),
              ('region', _('Region')), ('code', _('Postal code')),
              ('country', _('Country')))

    def __init__(self, address, on_remove):
        super().__init__()
        self.set_title(_('Address'))
        self.dropdown = Gtk.DropDown.new_from_strings(list(TYPES['address']))
        self.dropdown.set_valign(Gtk.Align.CENTER)
        if address.type in TYPES['address']:
            self.dropdown.set_selected(TYPES['address'].index(address.type))
        remove = Gtk.Button(icon_name='list-remove-symbolic')
        remove.set_valign(Gtk.Align.CENTER)
        remove.add_css_class('flat')
        remove.connect('clicked', lambda *args: on_remove(self))
        self.add_suffix(self.dropdown)
        self.add_suffix(remove)
        self.entries = {}
        for name, title in self.FIELDS:
            row = Adw.EntryRow(title=title)
            row.set_text(getattr(address, name))
            self.entries[name] = row
            self.add_row(row)
        self.set_subtitle(', '.join(address.lines()))

    def value(self):
        values = {name: row.get_text().strip() for name, row in self.entries.items()}
        return Address(type=TYPES['address'][self.dropdown.get_selected()], **values)


class AccountRow(Adw.ExpanderRow):
    """One bank account: holder and IBAN are the pair a transfer needs."""

    def __init__(self, account, on_remove):
        super().__init__()
        self.row_holder = Adw.EntryRow(title=_('Account holder'))
        self.row_holder.set_text(account.holder)
        self.row_iban = Adw.EntryRow(title=_('IBAN'))
        self.row_iban.set_text(account.iban)
        self.row_bic = Adw.EntryRow(title=_('BIC'))
        self.row_bic.set_text(account.bic)
        self.row_bank = Adw.EntryRow(title=_('Bank'))
        self.row_bank.set_text(account.bank)
        self.row_label = Adw.EntryRow(title=_('Label'))
        self.row_label.set_text(account.label)
        remove = Gtk.Button(icon_name='list-remove-symbolic')
        remove.set_valign(Gtk.Align.CENTER)
        remove.add_css_class('flat')
        remove.connect('clicked', lambda *args: on_remove(self))
        self.add_suffix(remove)
        for row in (self.row_holder, self.row_iban, self.row_bic,
                    self.row_bank, self.row_label):
            self.add_row(row)
        self.row_iban.connect('changed', lambda *args: self._check())
        self.row_holder.connect('changed', lambda *args: self._check())
        self._check()

    def set_iban(self, value):
        self.row_iban.set_text(value)

    def _check(self):
        """Warn on an IBAN that cannot be right, and never block saving."""
        account = self.value()
        wrong = bool(account.iban) and not ibanlib.is_valid(account.iban)
        for css, on in (('error', wrong or not account.complete),):
            if on:
                self.add_css_class(css)
            else:
                self.remove_css_class(css)
        if wrong:
            self.set_subtitle(_('This IBAN does not check out'))
        elif not account.complete:
            self.set_subtitle(_('Holder and IBAN are both needed'))
        else:
            self.set_subtitle(ibanlib.display(account.iban))
        self.set_title(account.label or _('Bank account'))

    def value(self):
        return Account(holder=self.row_holder.get_text().strip(),
                       iban=self.row_iban.get_text().strip(),
                       bic=self.row_bic.get_text().strip(),
                       bank=self.row_bank.get_text().strip(),
                       label=self.row_label.get_text().strip())


class ContactEditor:
    """The dialog that edits one contact, and the contact it builds."""

    def __init__(self, app, store):
        self.app = app
        self.store = store
        self.srvdlg = app.get_service('dialogs')
        self.key = ''
        self.contact = None
        self.page = Adw.PreferencesPage()
        self.page.set_hexpand(True)
        self.page.set_vexpand(True)
        self._build()

    def _build(self):
        group = Adw.PreferencesGroup(title=_('Name'))
        self.entry_fn = Adw.EntryRow(title=_('Full name'))
        self.entry_given = Adw.EntryRow(title=_('Given name'))
        self.entry_family = Adw.EntryRow(title=_('Family name'))
        self.entry_org = Adw.EntryRow(title=_('Organisation'))
        for row in (self.entry_fn, self.entry_given, self.entry_family, self.entry_org):
            group.add(row)
        self.page.add(group)

        self.groups = {}
        for kind, title, adder in (
                ('address', _('Postal addresses'), self.add_address),
                ('phone', _('Telephone numbers'), self.add_phone),
                ('email', _('Email addresses'), self.add_email),
                ('url', _('Web'), self.add_url),
                ('social', _('Social profiles'), self.add_social),
                ('account', _('Bank accounts'), self.add_account)):
            group = Adw.PreferencesGroup(title=title)
            button = Gtk.Button(icon_name='list-add-symbolic')
            button.add_css_class('flat')
            button.set_tooltip_text(_('Add'))
            button.connect('clicked', lambda _button, add=adder: add())
            group.set_header_suffix(button)
            self.page.add(group)
            self.groups[kind] = {'group': group, 'rows': []}

        group = Adw.PreferencesGroup(title=_('Note'))
        self.entry_note = Adw.EntryRow(title=_('Note'))
        group.add(self.entry_note)
        self.page.add(group)

    def load(self, key, description=''):
        """Fill the editor with what is known about one key."""
        self.key = key
        self.contact = self.store.get(key) or Contact(key=key, fn=description)
        self.entry_fn.set_text(self.contact.fn or description)
        self.entry_given.set_text(self.contact.given)
        self.entry_family.set_text(self.contact.family)
        self.entry_org.set_text(self.contact.org)
        self.entry_note.set_text(self.contact.note)
        for kind in self.groups:
            for row in list(self.groups[kind]['rows']):
                self._remove(kind, row)
        for address in self.contact.addresses:
            self.add_address(address)
        for entry in self.contact.phones:
            self.add_phone(entry)
        for entry in self.contact.emails:
            self.add_email(entry)
        for entry in self.contact.urls:
            self.add_url(entry)
        for entry in self.contact.socials:
            self.add_social(entry)
        for account in self.contact.accounts:
            self.add_account(account)

    def _add(self, kind, row):
        self.groups[kind]['group'].add(row)
        self.groups[kind]['rows'].append(row)
        return row

    def _remove(self, kind, row):
        self.groups[kind]['group'].remove(row)
        self.groups[kind]['rows'].remove(row)

    def add_address(self, address=None):
        return self._add('address', AddressRow(
            address or Address(type='home'),
            lambda row: self._remove('address', row)))

    def add_phone(self, entry=None):
        return self._add('phone', EntryRow(
            'phone', entry or Entry(type='cell'),
            lambda row: self._remove('phone', row)))

    def add_email(self, entry=None):
        return self._add('email', EntryRow(
            'email', entry or Entry(type='home'),
            lambda row: self._remove('email', row)))

    def add_url(self, entry=None):
        return self._add('url', EntryRow(
            'url', entry or Entry(type='home'),
            lambda row: self._remove('url', row)))

    def add_social(self, entry=None):
        return self._add('social', EntryRow(
            'social', entry or Entry(type='mastodon'),
            lambda row: self._remove('social', row)))

    def add_account(self, account=None):
        # The holder starts as the contact name, which is right often enough
        # to save typing and wrong often enough to stay editable.
        if account is None:
            account = Account(holder=self.entry_fn.get_text().strip())
        return self._add('account', AccountRow(
            account, lambda row: self._remove('account', row)))

    def build_contact(self):
        """What the fields say, as a contact ready to be saved."""
        contact = self.contact or Contact(key=self.key)
        contact.key = self.key
        contact.fn = self.entry_fn.get_text().strip()
        contact.given = self.entry_given.get_text().strip()
        contact.family = self.entry_family.get_text().strip()
        contact.org = self.entry_org.get_text().strip()
        contact.note = self.entry_note.get_text().strip()
        contact.addresses = [row.value() for row in self.groups['address']['rows']]
        contact.phones = [row.value() for row in self.groups['phone']['rows']
                          if row.value().value]
        contact.emails = [row.value() for row in self.groups['email']['rows']
                          if row.value().value]
        contact.urls = [row.value() for row in self.groups['url']['rows']
                        if row.value().value]
        contact.socials = [row.value() for row in self.groups['social']['rows']
                           if row.value().value]
        contact.accounts = [row.value() for row in self.groups['account']['rows']
                            if row.value().iban or row.value().holder]
        return contact

    def present(self, parent, key, description='', on_saved=None):
        """Open the editor on one key. Apply saves, Cancel does not."""
        self.load(key, description)
        window = Gtk.ScrolledWindow()
        window.set_hexpand(True)
        window.set_vexpand(True)
        window.set_child(self.page)

        def responded(dialog, response, data):
            if response != 'apply':
                return
            contact = self.build_contact()
            self.store.save(contact)
            if on_saved is not None:
                on_saved(contact)

        dialog = self.srvdlg.create(
            dtype='action',
            title=_('Contact'),
            body=self.contact.display_name() or key,
            widget=window, callback=responded,
            width=760, height=680)
        dialog.present(parent)
        return dialog
