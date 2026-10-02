#!/usr/bin/python3

"""The MiAZOikos view: income and expenses of the selected documents."""

from decimal import Decimal

import pytest

MORTGAGE = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'
ELECTRICITY = '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf'
PERMIT = '20240101-DE-ADM-CITY-NTF-permit-JOHNDOE.pdf'


@pytest.fixture
def oikos(clean_view):
    """The plugin, loaded for this file only and unloaded afterwards.

    MiAZOikos is not in the sandbox's enabled set on purpose: every other UI
    test would pay for a view it does not use.
    """
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('miazoikos')
    assert info is not None, 'the MiAZOikos plugin was not found'
    assert system.load_plugin(info), 'the MiAZOikos plugin did not load'
    clean_view.wait_until(
        lambda: clean_view.widget('plugin-MiAZOikos') is not None,
        message='the plugin registers itself')
    plugin = clean_view.widget('plugin-MiAZOikos')
    clean_view.wait_until(
        lambda: 'oikos' in clean_view.workspace.get_views(),
        message='the view is registered')
    yield plugin
    plugin.clear_documents([MORTGAGE, ELECTRICITY, PERMIT])
    clean_view.select_documents()
    clean_view.workspace.show_view('details')
    system.unload_plugin(info)
    clean_view.pump(0.3)


def test_the_view_says_so_when_nothing_is_selected(oikos, clean_view):
    clean_view.select_documents()
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(view.is_showing, message='the view is shown')
    assert view.stack.get_visible_child_name() == 'empty'
    assert not view.set_button.get_visible(), 'nothing to set without a selection'


def test_the_selection_is_added_up_per_currency(oikos, clean_view):
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('expense', '84.10', 'EUR'),
        PERMIT: Entry('income', '20', 'USD'),
    })
    clean_view.select_documents(MORTGAGE, ELECTRICITY, PERMIT)
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the totals are shown')

    sections = dict(view.chart.get_sections())
    assert sorted(sections) == ['EUR', 'USD'], 'currencies are never mixed'
    eur = sections['EUR'][0].totals
    assert eur.expense == Decimal('734.50')
    assert eur.income == Decimal('0')
    assert sections['USD'][0].totals.income == Decimal('20')
    assert view.get_missing() == []


def test_a_selected_document_without_an_amount_is_named_not_counted(oikos, clean_view):
    from oikos.ledger import Entry
    oikos.set_entries({MORTGAGE: Entry('expense', '650.40', 'EUR')})
    clean_view.select_documents(MORTGAGE, ELECTRICITY)
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the totals are shown')
    assert view.get_missing() == [ELECTRICITY]
    assert view.missing_bar.get_visible()


def test_the_view_follows_the_selection_while_shown(oikos, clean_view):
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('expense', '84.10', 'EUR'),
    })
    clean_view.select_documents(MORTGAGE)
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the totals are shown')
    clean_view.select_documents(MORTGAGE, ELECTRICITY)
    clean_view.wait_until(
        lambda: dict(view.chart.get_sections())['EUR'][0].totals.expense
        == Decimal('734.50'),
        message='the totals follow the selection')


def test_the_editor_writes_nothing_until_asked(oikos, clean_view):
    from oikos.editor import MiAZOikosEditor
    editor = MiAZOikosEditor(clean_view.app, oikos, [MORTGAGE, ELECTRICITY])
    assert editor.uses_shared_amount()
    assert not editor.is_valid(), 'no amount typed yet'
    editor.shared.set_text('1.234,50')
    entries = editor.entries()
    assert set(entries) == {MORTGAGE, ELECTRICITY}
    assert entries[MORTGAGE].amount == Decimal('1234.50')
    assert oikos.ledger.get(MORTGAGE) is None, 'the editor itself writes nothing'
