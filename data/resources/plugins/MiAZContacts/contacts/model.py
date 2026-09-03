# File: model.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The contact record, read from and written to a vCard

from dataclasses import dataclass, field

from contacts import vcard

# Where MiAZ keeps the person key a document is filed under.
KEY_PROPERTY = 'X-MIAZ-KEY'

# Properties read as a social profile, in the order they are looked for.
SOCIAL_NAMES = ('X-SOCIALPROFILE', 'IMPP')

# The properties of a bank account group. X-ABLabel is what other address
# books already use for the name of an entry.
ACCOUNT_NAMES = ('X-MIAZ-IBAN', 'X-MIAZ-HOLDER', 'X-MIAZ-BIC',
                 'X-MIAZ-BANK', 'X-ABLABEL')

# The seven components of ADR, in vCard order.
ADDRESS_PARTS = ('po_box', 'extended', 'street', 'locality', 'region',
                 'code', 'country')


@dataclass
class Entry:
    """One value of a repeatable field: a phone, an email, a url, a profile."""
    type: str = ''
    value: str = ''
    pref: bool = False


@dataclass
class Address:
    """One postal address, in the seven components vCard defines."""
    type: str = ''
    pref: bool = False
    po_box: str = ''
    extended: str = ''
    street: str = ''
    locality: str = ''
    region: str = ''
    code: str = ''
    country: str = ''

    def lines(self):
        """The address as it would be written on an envelope."""
        town = ' '.join(part for part in (self.code, self.locality) if part)
        candidates = (self.po_box, self.extended, self.street, town,
                      self.region, self.country)
        return [part for part in candidates if part]


@dataclass
class Account:
    """One bank account. Holder and IBAN are the pair a transfer needs."""
    holder: str = ''
    iban: str = ''
    bic: str = ''
    bank: str = ''
    label: str = ''

    @property
    def complete(self):
        return bool(self.holder.strip() and self.iban.strip())


@dataclass
class Contact:
    """Everything MiAZ keeps about one sender or recipient."""
    key: str = ''
    fn: str = ''
    family: str = ''
    given: str = ''
    additional: str = ''
    prefix: str = ''
    suffix: str = ''
    org: str = ''
    note: str = ''
    photo: object = None
    uid: str = ''
    addresses: list = field(default_factory=list)
    phones: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    urls: list = field(default_factory=list)
    socials: list = field(default_factory=list)
    accounts: list = field(default_factory=list)
    extras: list = field(default_factory=list)

    def display_name(self):
        return self.fn or self.org or self.key

    def is_empty(self):
        """True when nothing but the key is filled in."""
        return not any((self.fn, self.org, self.note, self.addresses,
                        self.phones, self.emails, self.urls, self.socials,
                        self.accounts))

    @classmethod
    def from_card(cls, card, key=''):
        """A contact read from a parsed card. The key is the card's, or given."""
        contact = cls(key=key)
        grouped = {}
        for prop in card.properties:
            if prop.name in vcard.STRUCTURAL:
                continue
            if prop.group and prop.name in ACCOUNT_NAMES:
                grouped.setdefault(prop.group, []).append(prop)
                continue
            if not _read_property(contact, prop):
                contact.extras.append(prop)
        for group in sorted(grouped):
            props = grouped[group]
            # X-ABLabel alone labels another property, as Apple writes it.
            if not any(prop.name.startswith('X-MIAZ-') for prop in props):
                contact.extras.extend(props)
                continue
            values = {prop.name: prop.text() for prop in props}
            contact.accounts.append(Account(
                holder=values.get('X-MIAZ-HOLDER', ''),
                iban=values.get('X-MIAZ-IBAN', ''),
                bic=values.get('X-MIAZ-BIC', ''),
                bank=values.get('X-MIAZ-BANK', ''),
                label=values.get('X-ABLABEL', '')))
        return contact

    def to_card(self):
        """The contact as a card, ready to be written."""
        props = [vcard.Property.from_text('FN', self.display_name()),
                 vcard.Property.from_components(
                     'N', [self.family, self.given, self.additional,
                           self.prefix, self.suffix])]
        if self.org:
            props.append(vcard.Property.from_text('ORG', self.org))
        for address in self.addresses:
            props.append(vcard.Property.from_components(
                'ADR', [address.po_box, address.extended, address.street,
                        address.locality, address.region, address.code,
                        address.country],
                params=_entry_params(address.type, address.pref)))
        for name, entries in (('TEL', self.phones), ('EMAIL', self.emails),
                              ('URL', self.urls), ('X-SOCIALPROFILE', self.socials)):
            for entry in entries:
                props.append(vcard.Property.from_text(
                    name, entry.value, params=_entry_params(entry.type, entry.pref)))
        for position, account in enumerate(self.accounts, start=1):
            group = f'item{position}'
            for name, value in (('X-MIAZ-IBAN', account.iban),
                                ('X-MIAZ-HOLDER', account.holder),
                                ('X-MIAZ-BIC', account.bic),
                                ('X-MIAZ-BANK', account.bank),
                                ('X-ABLabel', account.label)):
                if value:
                    props.append(vcard.Property.from_text(name, value, group=group))
        if self.note:
            props.append(vcard.Property.from_text('NOTE', self.note))
        if self.photo is not None:
            props.append(self.photo)
        if self.uid:
            props.append(vcard.Property.from_text('UID', self.uid))
        if self.key:
            props.append(vcard.Property.from_text(KEY_PROPERTY, self.key))
        props.extend(self.extras)
        return vcard.Card(props)


def _entry_params(type_name, pref):
    params = {}
    if type_name:
        params['TYPE'] = [type_name]
    if pref:
        params['PREF'] = ['1']
    return params


def _first_type(prop):
    types = [one for one in prop.types() if one != 'pref']
    return types[0] if types else ''


def _read_property(contact, prop):
    """Put one property where it belongs. False means nothing knew it."""
    name = prop.name
    if name == 'FN':
        contact.fn = prop.text()
    elif name == 'N':
        parts = prop.components()
        values = [', '.join(one for one in part if one) for part in parts]
        values += [''] * (5 - len(values))
        (contact.family, contact.given, contact.additional,
         contact.prefix, contact.suffix) = values[:5]
    elif name == 'ORG':
        contact.org = prop.component(0)
    elif name == 'NOTE':
        contact.note = prop.text()
    elif name == 'UID':
        contact.uid = prop.text()
    elif name == 'PHOTO':
        contact.photo = prop
    elif name == KEY_PROPERTY:
        contact.key = contact.key or prop.text()
    elif name == 'ADR':
        parts = prop.components()
        values = [', '.join(one for one in part if one) for part in parts]
        values += [''] * (7 - len(values))
        contact.addresses.append(Address(
            type=_first_type(prop), pref=prop.is_preferred(),
            **dict(zip(ADDRESS_PARTS, values[:7]))))
    elif name == 'TEL':
        contact.phones.append(_entry(prop))
    elif name == 'EMAIL':
        contact.emails.append(_entry(prop))
    elif name == 'URL':
        contact.urls.append(_entry(prop))
    elif name in SOCIAL_NAMES:
        contact.socials.append(_entry(prop))
    else:
        return False
    return True


def _entry(prop):
    return Entry(type=_first_type(prop), value=prop.text(), pref=prop.is_preferred())
