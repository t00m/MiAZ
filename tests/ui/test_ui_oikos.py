#!/usr/bin/python3

"""The MiAZOikos view: income and expenses of the selected documents, or of
every document shown when nothing is selected."""

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
    clean_view.workspace.clear_filters()
    clean_view.workspace.show_view('details')
    system.unload_plugin(info)
    clean_view.pump(0.3)


def show_only(clean_view, *ids):
    """Filter the workspace down to exactly these documents.

    show_documents is the workspace call for an explicit list; it also
    switches to Details, so callers show the view they want afterwards.
    """
    clean_view.workspace.show_documents(ids)
    clean_view.pump(0.3)


def test_with_nothing_selected_every_document_shown_is_added_up(oikos, clean_view):
    from oikos.ledger import Entry
    from oikos.view import SCOPE_SHOWN
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('expense', '84.10', 'EUR'),
        PERMIT: Entry('income', '20', 'USD'),
    })
    show_only(clean_view, MORTGAGE, ELECTRICITY)
    clean_view.select_documents()
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the documents shown are added up')
    assert view.get_scope() == SCOPE_SHOWN
    sections = dict(view.chart.get_sections())
    assert sorted(sections) == ['EUR'], 'PERMIT is filtered out, so no USD'
    assert sections['EUR'][0].totals.expense == Decimal('734.50')
    assert 'shown' in view.counter.get_text()


def test_with_nothing_selected_the_totals_follow_the_filters(oikos, clean_view):
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('expense', '84.10', 'EUR'),
    })
    show_only(clean_view, MORTGAGE, ELECTRICITY)
    clean_view.select_documents()
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the totals are shown')
    # A filter change while the view is on screen, without leaving it.
    clean_view.widget('searchentry-concept').set_text('mortgage')
    clean_view.wait_until(
        lambda: dict(view.chart.get_sections())['EUR'][0].totals.expense
        == Decimal('650.40'),
        message='the totals follow the filter')
    clean_view.widget('searchentry-concept').set_text('')


def test_a_selection_is_counted_instead_of_everything_shown(oikos, clean_view):
    from oikos.ledger import Entry
    from oikos.view import SCOPE_SELECTION
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('expense', '84.10', 'EUR'),
    })
    show_only(clean_view, MORTGAGE, ELECTRICITY)
    clean_view.select_documents(ELECTRICITY)
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the totals are shown')
    assert view.get_scope() == SCOPE_SELECTION
    assert dict(view.chart.get_sections())['EUR'][0].totals.expense == Decimal('84.10')


def test_the_view_says_so_when_nothing_is_shown(oikos, clean_view):
    show_only(clean_view)
    clean_view.select_documents()
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(view.is_showing, message='the view is shown')
    clean_view.pump(0.3)
    assert view.stack.get_visible_child_name() == 'empty'
    assert not view.set_button.get_visible(), 'nothing to set when nothing is shown'


def test_the_set_button_edits_the_documents_counted(oikos, clean_view, monkeypatch):
    """With nothing selected the Set button must still have documents to
    edit: the ones shown, not an empty selection."""
    show_only(clean_view, MORTGAGE, ELECTRICITY)
    clean_view.select_documents()
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'empty',
        message='nothing recorded yet')
    assert view.set_button.get_visible()
    asked = []
    monkeypatch.setattr(oikos, 'edit_documents', lambda docs: asked.append(sorted(docs)))
    view.set_button.emit('clicked')
    assert asked == [sorted([MORTGAGE, ELECTRICITY])]


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
