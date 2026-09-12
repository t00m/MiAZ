# File: card.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: One contact as a card: who they are and what MiAZ knows

import base64
from gettext import gettext as _
from gettext import ngettext

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from contacts import iban as ibanlib

# How many values of one kind a card shows before it stops listing them.
SHOWN = 3


def photo_texture(contact):
    """The contact photo as something GTK can draw, or None.

    A card can carry the photo as a data URI (vCard 4.0) or as base64 in the
    value (3.0). Anything that does not decode is simply not shown.
    """
    if contact is None or contact.photo is None:
        return None
    raw = contact.photo.text()
    if raw.startswith('data:'):
        _head, _sign, raw = raw.partition(',')
    try:
        data = base64.b64decode(raw, validate=False)
        return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
    except (ValueError, GLib.Error):
        return None


class ContactCard(Gtk.Box):
    """One party: the avatar, the name, the details, and what to do next."""
    __gtype_name__ = 'MiAZContactCard'
    __gsignals__ = {
        'show-documents': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'edit-contact': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class('card')
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self._key = ''

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        head.set_margin_top(10)
        head.set_margin_start(10)
        head.set_margin_end(10)
        self.avatar = Adw.Avatar(size=56, show_initials=True)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        titles.set_valign(Gtk.Align.CENTER)
        self.label_name = Gtk.Label(xalign=0)
        self.label_name.add_css_class('heading')
        self.label_name.set_ellipsize(Pango.EllipsizeMode.END)
        self.label_key = Gtk.Label(xalign=0)
        self.label_key.add_css_class('caption')
        self.label_key.add_css_class('dim-label')
        self.label_count = Gtk.Label(xalign=0)
        self.label_count.add_css_class('caption')
        self.label_count.add_css_class('dim-label')
        titles.append(self.label_name)
        titles.append(self.label_key)
        titles.append(self.label_count)
        head.append(self.avatar)
        head.append(titles)

        self.details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.details.set_margin_start(10)
        self.details.set_margin_end(10)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_halign(Gtk.Align.END)
        actions.set_margin_start(10)
        actions.set_margin_end(10)
        actions.set_margin_bottom(10)
        self.button_show = Gtk.Button(label=_('Show'))
        self.button_show.set_tooltip_text(_('Show this contact documents'))
        self.button_show.connect('clicked', lambda *args: self.emit('show-documents', self._key))
        self.button_edit = Gtk.Button()
        self.button_edit.connect('clicked', lambda *args: self.emit('edit-contact', self._key))
        actions.append(self.button_show)
        actions.append(self.button_edit)

        self.append(head)
        self.append(self.details)
        self.append(actions)

    def update(self, party, contact):
        """Draw one party, with the contact record when there is one."""
        self._key = party.key
        name = contact.display_name() if contact is not None else party.description
        self.label_name.set_text(name or party.key)
        self.label_name.set_tooltip_text(name or party.key)
        self.label_key.set_text(party.key)
        self.label_count.set_text(_('{total} documents, {sent} sent, {received} received').format(
            total=party.total, sent=party.sent, received=party.received))
        self.avatar.set_text(name or party.key)
        self.avatar.set_custom_image(photo_texture(contact))
        self.button_edit.set_label(
            _('Edit') if contact is not None else _('Add details'))
        while (child := self.details.get_first_child()) is not None:
            self.details.remove(child)
        for line in self._lines(contact):
            label = Gtk.Label(xalign=0, label=line)
            label.add_css_class('caption')
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_tooltip_text(line)
            self.details.append(label)

    def _lines(self, contact):
        """The details worth reading on a card, in the order they matter."""
        if contact is None:
            return [_('No details yet')]
        lines = []
        if contact.org and contact.org != contact.fn:
            lines.append(contact.org)
        for address in contact.addresses[:1]:
            lines.append(', '.join(address.lines()))
        for entry in contact.phones[:SHOWN]:
            lines.append(f"{entry.value} ({entry.type})" if entry.type else entry.value)
        for entry in contact.emails[:SHOWN]:
            lines.append(entry.value)
        for entry in contact.urls[:1]:
            lines.append(entry.value)
        if contact.socials:
            lines.append(ngettext('{count} social profile', '{count} social profiles',
                                  len(contact.socials)).format(count=len(contact.socials)))
        for account in contact.accounts:
            lines.append(self._account_line(account, contact))
        return lines or [_('No details yet')]

    @staticmethod
    def _account_line(account, contact):
        """One account: the label, the IBAN, and the holder when it differs.

        A payment is checked against the name on the account, so a holder that
        is not the contact name is the part worth showing.
        """
        parts = []
        if account.label:
            parts.append(f'{account.label}:')
        parts.append(ibanlib.display(account.iban) or _('no IBAN'))
        if account.holder and account.holder != contact.display_name():
            parts.append(_('held by {holder}').format(holder=account.holder))
        if not account.complete:
            parts.append(_('(incomplete)'))
        return ' '.join(parts)
