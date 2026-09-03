#!/usr/bin/python3

"""What the MiAZContacts core does: IBANs, the model, the store, the parties.

The `contacts` package lives under the plugin directory, which is not on the
default path, so the test inserts it the way the plugin does at runtime.
"""

import os
import re
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZContacts')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def test_a_correct_iban_is_valid():
    from contacts import iban
    assert iban.is_valid('DE02120300000000202051')
    assert iban.is_valid('ES9121000418450200051332')
    assert iban.is_valid('GB33BUKB20201555555555')


def test_spacing_and_case_do_not_matter():
    from contacts import iban
    assert iban.is_valid('de02 1203 0000 0000 2020 51')
    assert iban.normalise('de02 1203-0000') == 'DE0212030000'


def test_a_wrong_checksum_is_not_valid():
    from contacts import iban
    assert not iban.is_valid('DE02120300000000202052')


def test_a_wrong_length_for_the_country_is_not_valid():
    from contacts import iban
    assert not iban.is_valid('DE0212030000000020205')


def test_something_that_is_not_an_iban_is_not_valid():
    from contacts import iban
    assert not iban.is_valid('')
    assert not iban.is_valid('not an iban')
    assert not iban.is_valid('12345678901234567890')


def test_an_unknown_country_still_gets_the_checksum():
    from contacts import iban
    # ZZ is in no registry, so only the checksum and the shape can speak.
    assert not iban.is_valid('ZZ00120300000000202051')


def test_display_groups_in_fours():
    from contacts import iban
    assert iban.display('DE02120300000000202051') == (
        'DE02 1203 0000 0000 2020 51')
    assert iban.display('') == ''


FULL_CARD = (
    'BEGIN:VCARD\r\n'
    'VERSION:4.0\r\n'
    'FN:John Doe\r\n'
    'N:Doe;John;Peter;Dr.;Jr.\r\n'
    'ORG:ACME S.A.\r\n'
    'X-MIAZ-KEY:JOHNDOE\r\n'
    'ADR;TYPE=home:;;Main St 1;Berlin;;10115;DE\r\n'
    'TEL;TYPE=cell;PREF=1:+49 170 1234567\r\n'
    'TEL;TYPE=work:+49 30 123456\r\n'
    'EMAIL;TYPE=home:john@example.com\r\n'
    'URL:https://example.com\r\n'
    'X-SOCIALPROFILE;TYPE=mastodon:https://mastodon.social/@john\r\n'
    'item1.X-MIAZ-IBAN:DE02120300000000202051\r\n'
    'item1.X-MIAZ-HOLDER:John Peter Doe\r\n'
    'item1.X-MIAZ-BIC:BYLADEM1001\r\n'
    'item1.X-MIAZ-BANK:Deutsche Bank\r\n'
    'item1.X-ABLabel:Salary\r\n'
    'NOTE:Two lines\\nof note\r\n'
    'BDAY:19800101\r\n'
    'END:VCARD\r\n')


def parsed_contact():
    from contacts import model, vcard
    return model.Contact.from_card(vcard.parse(FULL_CARD)[0])


def test_the_plain_fields_are_read():
    contact = parsed_contact()
    assert contact.key == 'JOHNDOE'
    assert contact.fn == 'John Doe'
    assert contact.family == 'Doe'
    assert contact.given == 'John'
    assert contact.additional == 'Peter'
    assert contact.prefix == 'Dr.'
    assert contact.suffix == 'Jr.'
    assert contact.org == 'ACME S.A.'
    assert contact.note == 'Two lines\nof note'


def test_the_repeatable_fields_are_read_with_type_and_preference():
    contact = parsed_contact()
    assert [(one.type, one.value, one.pref) for one in contact.phones] == [
        ('cell', '+49 170 1234567', True), ('work', '+49 30 123456', False)]
    assert [(one.type, one.value) for one in contact.emails] == [
        ('home', 'john@example.com')]
    assert [one.value for one in contact.urls] == ['https://example.com']
    assert [(one.type, one.value) for one in contact.socials] == [
        ('mastodon', 'https://mastodon.social/@john')]


def test_an_address_keeps_its_seven_components():
    contact = parsed_contact()
    address = contact.addresses[0]
    assert address.type == 'home'
    assert address.street == 'Main St 1'
    assert address.locality == 'Berlin'
    assert address.code == '10115'
    assert address.country == 'DE'
    assert address.lines() == ['Main St 1', '10115 Berlin', 'DE']


def test_a_bank_account_is_read_from_its_group():
    contact = parsed_contact()
    assert len(contact.accounts) == 1
    account = contact.accounts[0]
    assert account.iban == 'DE02120300000000202051'
    assert account.holder == 'John Peter Doe'
    assert account.bic == 'BYLADEM1001'
    assert account.bank == 'Deutsche Bank'
    assert account.label == 'Salary'
    assert account.complete


def test_an_account_without_holder_or_iban_is_incomplete():
    from contacts import model
    assert not model.Account(iban='DE02120300000000202051').complete
    assert not model.Account(holder='John Doe').complete


def test_a_property_the_model_does_not_know_is_kept():
    contact = parsed_contact()
    assert [prop.name for prop in contact.extras] == ['BDAY']


def test_a_label_alone_in_a_group_is_not_an_account():
    from contacts import model, vcard
    card = vcard.parse(
        'BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Jane Roe\r\n'
        'item1.EMAIL:jane@example.com\r\n'
        'item1.X-ABLabel:Work\r\nEND:VCARD\r\n')[0]
    contact = model.Contact.from_card(card)
    assert contact.accounts == []
    assert [one.value for one in contact.emails] == ['jane@example.com']
    again = model.Contact.from_card(vcard.parse(vcard.serialize([contact.to_card()]))[0])
    assert again.accounts == []
    assert [prop.text() for prop in again.extras if prop.name == 'X-ABLABEL'] == ['Work']


def test_a_contact_written_and_read_again_is_the_same():
    from contacts import model, vcard
    original = parsed_contact()
    again = model.Contact.from_card(vcard.parse(vcard.serialize([original.to_card()]))[0])
    assert again.key == original.key
    assert again.fn == original.fn
    assert again.family == original.family
    assert again.note == original.note
    assert [one.value for one in again.phones] == [one.value for one in original.phones]
    assert [one.type for one in again.phones] == [one.type for one in original.phones]
    assert again.addresses[0].lines() == original.addresses[0].lines()
    assert again.accounts[0].holder == original.accounts[0].holder
    assert again.accounts[0].iban == original.accounts[0].iban
    assert again.accounts[0].label == original.accounts[0].label
    assert [prop.name for prop in again.extras] == ['BDAY']


def test_two_accounts_stay_apart():
    from contacts import model, vcard
    contact = model.Contact(key='ACME', fn='ACME S.A.', accounts=[
        model.Account(holder='ACME S.A.', iban='DE02120300000000202051', label='One'),
        model.Account(holder='ACME S.A.', iban='ES9121000418450200051332', label='Two')])
    again = model.Contact.from_card(vcard.parse(vcard.serialize([contact.to_card()]))[0])
    assert [one.label for one in again.accounts] == ['One', 'Two']
    assert [one.iban for one in again.accounts] == [
        'DE02120300000000202051', 'ES9121000418450200051332']


def test_a_card_with_no_key_takes_the_one_it_is_given():
    from contacts import model, vcard
    card = vcard.parse('BEGIN:VCARD\r\nVERSION:4.0\r\nFN:Jane Roe\r\nEND:VCARD\r\n')[0]
    contact = model.Contact.from_card(card, key='JANEROE')
    assert contact.key == 'JANEROE'
    assert contact.to_card().get('X-MIAZ-KEY').text() == 'JANEROE'


def test_display_name_falls_back_to_the_key():
    from contacts import model
    assert model.Contact(key='BANKX').display_name() == 'BANKX'
    assert model.Contact(key='BANKX', fn='Bank X').display_name() == 'Bank X'


def a_contact(key='JOHNDOE', fn='John Doe'):
    from contacts import model
    return model.Contact(key=key, fn=fn, family=fn.split()[-1],
                         given=fn.split()[0])


def test_saving_writes_one_file_per_key(tmp_path):
    from contacts import store
    shop = store.ContactStore(str(tmp_path))
    path = shop.save(a_contact())
    assert os.path.basename(path) == 'JOHNDOE.vcf'
    assert os.path.exists(path)
    assert open(path, encoding='utf-8').read().startswith('BEGIN:VCARD')


def test_what_was_saved_is_read_back(tmp_path):
    from contacts import store
    shop = store.ContactStore(str(tmp_path))
    shop.save(a_contact())
    again = store.ContactStore(str(tmp_path))
    assert again.keys() == ['JOHNDOE']
    assert again.get('JOHNDOE').fn == 'John Doe'
    assert again.get('NOBODY') is None


def test_saving_twice_leaves_one_file(tmp_path):
    from contacts import store
    shop = store.ContactStore(str(tmp_path))
    shop.save(a_contact())
    shop.save(a_contact(fn='John P. Doe'))
    assert len(os.listdir(str(tmp_path))) == 1
    assert store.ContactStore(str(tmp_path)).get('JOHNDOE').fn == 'John P. Doe'


def test_saving_leaves_no_temporary_file_behind(tmp_path):
    from contacts import store
    store.ContactStore(str(tmp_path)).save(a_contact())
    assert os.listdir(str(tmp_path)) == ['JOHNDOE.vcf']


def test_deleting_removes_the_file_and_says_so(tmp_path):
    from contacts import store
    shop = store.ContactStore(str(tmp_path))
    shop.save(a_contact())
    assert shop.delete('JOHNDOE')
    assert shop.keys() == []
    assert not shop.delete('JOHNDOE')


def test_a_file_that_cannot_be_read_is_reported_not_raised(tmp_path):
    from contacts import store
    with open(os.path.join(str(tmp_path), 'BROKEN.vcf'), 'w', encoding='utf-8') as handle:
        handle.write('this is not a vcard')
    shop = store.ContactStore(str(tmp_path))
    assert shop.keys() == []
    assert 'BROKEN' in shop.broken()


def test_a_key_is_minted_from_the_name():
    from contacts import store
    assert store.mint_key('John Doe', taken=set()) == 'JOHNDOE'
    assert store.mint_key('ACME S.A.', taken=set()) == 'ACMESA'
    assert store.mint_key('Tomás Vírseda', taken=set()) == 'TOMASVIRSEDA'


def test_a_minted_key_does_not_collide():
    from contacts import store
    assert store.mint_key('John Doe', taken={'JOHNDOE'}) == 'JOHNDOE2'
    assert store.mint_key('John Doe', taken={'JOHNDOE', 'JOHNDOE2'}) == 'JOHNDOE3'


def test_a_nameless_card_still_gets_a_key():
    from contacts import store
    assert store.mint_key('', taken=set()) == 'CONTACT'


def _fake_valid_key(key):
    """A stand-in for util.valid_key, shaped the way the real one is."""
    key = str(key).strip().replace('-', '_').replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', key)


def test_a_minted_key_matches_valid_key_when_one_is_given():
    from contacts import store
    assert store.mint_key('Jane Roe', taken=set(), valid_key=_fake_valid_key) == 'JANE_ROE'
    # unchanged when no valid_key is given, so the old callers stay correct
    assert store.mint_key('Jane Roe', taken=set()) == 'JANEROE'


def test_importing_adds_what_the_file_holds(tmp_path):
    from contacts import store
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write(FULL_CARD)
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    shop = store.ContactStore(data)
    result = shop.import_file(source)
    assert result.added == ['JOHNDOE']
    assert result.updated == []
    assert shop.get('JOHNDOE').accounts[0].iban == 'DE02120300000000202051'


def test_importing_the_same_card_again_updates_it(tmp_path):
    from contacts import store
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write(FULL_CARD)
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    shop = store.ContactStore(data)
    shop.import_file(source)
    result = shop.import_file(source)
    assert result.added == []
    assert result.updated == ['JOHNDOE']


def test_a_card_with_no_key_is_matched_by_name(tmp_path):
    from contacts import store
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write('BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Bank X\r\nEND:VCARD\r\n')
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    result = store.ContactStore(data).import_file(source, known_names={'bank x': 'BANKX'})
    assert result.added == ['BANKX']


def test_a_card_with_neither_key_nor_match_gets_a_minted_key(tmp_path):
    from contacts import store
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write('BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Jane Roe\r\nEND:VCARD\r\n')
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    result = store.ContactStore(data).import_file(source)
    assert result.added == ['JANEROE']


def test_a_minted_import_key_follows_valid_key_when_given(tmp_path):
    from contacts import store
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write('BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Jane Roe\r\nEND:VCARD\r\n')
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    result = store.ContactStore(data).import_file(source, valid_key=_fake_valid_key)
    assert result.added == ['JANE_ROE']


def test_path_for_rejects_a_key_that_is_not_a_bare_filename(tmp_path):
    from contacts import store
    shop = store.ContactStore(str(tmp_path))
    with pytest.raises(ValueError):
        shop.path_for('../escape')
    with pytest.raises(ValueError):
        shop.path_for('')
    with pytest.raises(ValueError):
        shop.path_for('.hidden')


def test_an_imported_key_that_escapes_the_data_directory_is_rejected(tmp_path):
    from contacts import store
    hostile = FULL_CARD.replace('X-MIAZ-KEY:JOHNDOE', 'X-MIAZ-KEY:../escape')
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write(hostile + FULL_CARD)
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    shop = store.ContactStore(data)
    result = shop.import_file(source)
    assert result.added == ['JOHNDOE'], 'the good card after the hostile one still imports'
    assert len(result.failed) == 1
    escaped = os.path.normpath(os.path.join(data, '..', 'escape.vcf'))
    assert not os.path.exists(escaped), 'the hostile key must not write outside data_dir'
    assert shop.get('JOHNDOE') is not None


def test_a_file_that_holds_no_card_imports_nothing(tmp_path):
    from contacts import store
    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write('nothing here')
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    result = store.ContactStore(data).import_file(source)
    assert result.added == [] and result.updated == [] and result.failed == []


def test_exporting_writes_every_card_into_one_file(tmp_path):
    from contacts import store, vcard
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    shop = store.ContactStore(data)
    shop.save(a_contact('JOHNDOE', 'John Doe'))
    shop.save(a_contact('JANEROE', 'Jane Roe'))
    target = os.path.join(str(tmp_path), 'out.vcf')
    assert shop.export_file(target) == 2
    cards = vcard.parse(open(target, encoding='utf-8').read())
    assert sorted(one.get('FN').text() for one in cards) == ['Jane Roe', 'John Doe']


def test_exporting_can_be_narrowed_to_some_keys(tmp_path):
    from contacts import store, vcard
    data = os.path.join(str(tmp_path), 'data')
    os.makedirs(data)
    shop = store.ContactStore(data)
    shop.save(a_contact('JOHNDOE', 'John Doe'))
    shop.save(a_contact('JANEROE', 'Jane Roe'))
    target = os.path.join(str(tmp_path), 'out.vcf')
    assert shop.export_file(target, keys=['JANEROE']) == 1
    assert [one.get('FN').text() for one in
            vcard.parse(open(target, encoding='utf-8').read())] == ['Jane Roe']


class FakeItem:
    """What the workspace hands a view, reduced to the fields parties reads."""

    def __init__(self, name, sentby, sentto):
        self.id = name
        self.sentby_id = sentby
        self.sentby_dsc = sentby.title()
        self.sentto_id = sentto
        self.sentto_dsc = sentto.title()


def some_items():
    return [
        FakeItem('one.pdf', 'BANKX', 'JOHNDOE'),
        FakeItem('two.pdf', 'BANKX', 'JOHNDOE'),
        FakeItem('three.pdf', 'JOHNDOE', 'BANKX'),
        FakeItem('four.pdf', 'ACME', 'JOHNDOE'),
    ]


def test_a_party_appears_once_however_often_it_is_named():
    from contacts import parties
    found = parties.parties(some_items())
    assert [one.key for one in found] == ['JOHNDOE', 'BANKX', 'ACME']


def test_sent_and_received_are_counted_apart():
    from contacts import parties
    found = {one.key: one for one in parties.parties(some_items())}
    assert (found['BANKX'].sent, found['BANKX'].received) == (2, 1)
    assert (found['JOHNDOE'].sent, found['JOHNDOE'].received) == (1, 3)
    assert found['JOHNDOE'].total == 4


def test_the_description_comes_from_the_item():
    from contacts import parties
    found = {one.key: one for one in parties.parties(some_items())}
    assert found['BANKX'].description == 'Bankx'


def test_an_empty_document_set_has_no_parties():
    from contacts import parties
    assert parties.parties([]) == []


def test_an_empty_key_is_not_a_party():
    from contacts import parties
    items = [FakeItem('one.pdf', '', 'JOHNDOE')]
    assert [one.key for one in parties.parties(items)] == ['JOHNDOE']


def test_the_documents_of_one_party_are_the_ones_it_is_named_in():
    from contacts import parties
    assert parties.documents_for('BANKX', some_items()) == [
        'one.pdf', 'three.pdf', 'two.pdf']
