#!/usr/bin/python3

"""The Contacts view: one card per party of the documents on screen."""

import pytest


@pytest.fixture
def contacts(clean_view):
    """The plugin, loaded for this file only and unloaded afterwards.

    MiAZContacts is not in the sandbox's enabled set on purpose: every other
    UI test would pay for a view it does not use.
    """
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('contactbook')
    assert info is not None, 'the MiAZContacts plugin was not found'
    assert system.load_plugin(info), 'the MiAZContacts plugin did not load'
    clean_view.wait_until(
        lambda: clean_view.widget('plugin-MiAZContacts') is not None,
        message='the plugin registers itself')
    plugin = clean_view.widget('plugin-MiAZContacts')
    clean_view.wait_until(
        lambda: 'contacts' in clean_view.workspace.get_views(),
        message='the Contacts view is registered')
    yield plugin
    clean_view.workspace.show_view('details')
    system.unload_plugin(info)
    clean_view.pump(0.3)


def _cards(view):
    count = 0
    child = view.gridview.get_first_child()
    while child is not None:
        count += 1
        child = child.get_next_sibling()
    return count


def test_the_view_is_registered_and_empty_until_it_is_shown(contacts, clean_view):
    view = clean_view.widget('workspace-contacts')
    assert view is not None
    assert view.gridview.get_model() is None, 'nothing is built while hidden'
    assert _cards(view) == 0


def test_one_card_per_party_of_the_documents_on_screen(contacts, clean_view):
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-contacts')
    workspace.show_view('contacts')
    clean_view.wait_until(lambda: view.gridview.get_model() is not None,
                          message='the view takes its model when shown')
    clean_view.wait_until(lambda: _cards(view) > 0, message='cards are built')

    keys = [party.key for party in view.get_parties()]
    assert len(keys) == len(set(keys)), 'a party appears once'
    assert 'JOHNDOE' in keys
    assert 'BANKX' in keys
    johndoe = next(party for party in view.get_parties() if party.key == 'JOHNDOE')
    assert johndoe.received >= 3


def test_the_view_follows_the_filter(contacts, clean_view):
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-contacts')
    workspace.show_view('contacts')
    clean_view.wait_until(lambda: view.gridview.get_model() is not None,
                          message='the view takes its model when shown')
    clean_view.select_dropdown_value('SentBy', 'BANKX')
    clean_view.wait_until(
        lambda: {party.key for party in view.get_parties()} == {'BANKX', 'JOHNDOE'},
        message='the parties follow the filter')


def test_unloading_the_plugin_takes_the_view_away(contacts, clean_view):
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('contactbook')
    system.unload_plugin(info)
    clean_view.pump(0.3)
    assert 'contacts' not in clean_view.workspace.get_views()
    assert clean_view.workspace.get_view_stack().get_child_by_name('contacts') is None
    # Load it again so the fixture teardown finds what it expects.
    system.load_plugin(info)
    clean_view.pump(0.3)


def test_the_editor_writes_a_contact_the_store_reads_back(contacts, clean_view):
    from contacts.model import Account, Entry

    store = contacts.get_store()
    editor = contacts.make_editor()
    editor.load('BANKX', 'Bank X')
    editor.entry_fn.set_text('Bank X S.A.')
    editor.add_phone(Entry(type='work', value='+34 900 123 456'))
    editor.add_email(Entry(type='work', value='info@bankx.example'))
    editor.add_account(Account(holder='Bank X S.A.',
                               iban='ES9121000418450200051332',
                               bic='CAIXESBBXXX', bank='Bank X', label='Fees'))
    store.save(editor.build_contact())

    again = contacts.get_store()
    again.load(force=True)
    saved = again.get('BANKX')
    assert saved.fn == 'Bank X S.A.'
    assert [one.value for one in saved.phones] == ['+34 900 123 456']
    assert [one.value for one in saved.emails] == ['info@bankx.example']
    assert saved.accounts[0].iban == 'ES9121000418450200051332'
    assert saved.accounts[0].holder == 'Bank X S.A.'
    assert saved.accounts[0].label == 'Fees'
    assert saved.accounts[0].complete
    assert store.delete('BANKX')


def test_the_editor_marks_an_iban_that_cannot_be_right(contacts, clean_view):
    from contacts.model import Account

    editor = contacts.make_editor()
    editor.load('BANKX', 'Bank X')
    row = editor.add_account(Account(holder='Bank X', iban='ES912100041845020005133'))
    assert row.has_css_class('error')
    row.set_iban('ES9121000418450200051332')
    assert not row.has_css_class('error')


def test_a_file_of_cards_imports_and_exports_again(contacts, clean_view, tmp_path):
    import os

    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write('BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Bank X\r\n'
                     'EMAIL:info@bankx.example\r\nEND:VCARD\r\n')
    manager = contacts.make_manager()
    result = manager.import_path(source)
    assert result.added == ['BANKX'], 'the card matches the vocabulary by name'

    store = contacts.get_store()
    assert store.get('BANKX').emails[0].value == 'info@bankx.example'

    target = os.path.join(str(tmp_path), 'out.vcf')
    assert manager.export_path(target, keys=['BANKX']) == 1
    written = open(target, encoding='utf-8').read()
    assert 'VERSION:4.0' in written
    assert 'X-MIAZ-KEY:BANKX' in written
    assert store.delete('BANKX')


def test_an_imported_name_the_vocabulary_does_not_know_gets_a_key(contacts,
                                                                  clean_view,
                                                                  tmp_path):
    import os

    source = os.path.join(str(tmp_path), 'in.vcf')
    with open(source, 'w', encoding='utf-8') as handle:
        handle.write('BEGIN:VCARD\r\nVERSION:4.0\r\nFN:Jane Roe\r\nEND:VCARD\r\n')
    result = contacts.make_manager().import_path(source)
    # shaped like util.valid_key would shape it, not the pure-Python fallback
    assert result.added == ['JANE_ROE']
    person = clean_view.app.get_config('Person')
    assert person.exists_available('JANE_ROE'), 'a minted key joins the people pool'
    person.remove_available('JANE_ROE')
    assert contacts.get_store().delete('JANE_ROE')


def test_new_contact_creates_a_record_and_joins_the_people_pool(contacts, clean_view):
    person = clean_view.app.get_config('Person')
    manager = contacts.make_manager()

    manager.new_contact('Jane Roe')

    store = contacts.get_store()
    saved = store.get('JANE_ROE')
    assert saved is not None, 'the New entry point must save a contact under the minted key'
    assert saved.fn == 'Jane Roe'
    assert person.exists_available('JANE_ROE')
    person.remove_available('JANE_ROE')
    assert store.delete('JANE_ROE')


def test_new_contact_does_nothing_for_an_empty_name(contacts, clean_view):
    manager = contacts.make_manager()
    store = contacts.get_store()
    before = set(store.keys())

    manager.new_contact('   ')

    assert set(store.keys()) == before
