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


class _ListItem:
    """Just enough of a Gtk.ListItem for a factory's setup and bind handlers."""

    def __init__(self, doc_id):
        self._child = None
        self._item = type('Item', (), {'id': doc_id})()

    def set_child(self, child):
        self._child = child

    def get_child(self):
        return self._child

    def get_item(self):
        return self._item


def _bound_label(column, doc_id):
    """The label the Amount column shows for a document."""
    list_item = _ListItem(doc_id)
    column._on_setup(None, list_item)
    column._on_bind(None, list_item)
    return list_item.get_child()


def test_the_amount_column_is_in_the_table_and_the_chooser(oikos, clean_view):
    from oikos.column import COLUMN_NAME
    workspace = clean_view.workspace
    column = oikos.get_column().column
    assert COLUMN_NAME in workspace.get_extra_columns()
    columns = workspace.view.cv.get_columns()
    assert any(columns.get_item(i) is column for i in range(columns.get_n_items()))
    menu = workspace._columns_menu
    labels = [menu.get_item_attribute_value(i, 'label').get_string()
              for i in range(menu.get_n_items())]
    assert column.get_title() in labels, 'the column has a chooser entry'


def test_an_expense_is_negative_and_red_an_income_unsigned_and_green(oikos, clean_view):
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        PERMIT: Entry('income', '20', 'USD'),
    })
    column = oikos.get_column()
    expense = _bound_label(column, MORTGAGE)
    income = _bound_label(column, PERMIT)
    nothing = _bound_label(column, ELECTRICITY)
    assert expense.get_text().startswith('−650') and expense.get_text().endswith(' EUR')
    assert expense.has_css_class('error') and not expense.has_css_class('success')
    assert not income.get_text().startswith(('+', '−'))
    assert income.get_text().startswith('20') and income.get_text().endswith(' USD')
    assert income.has_css_class('success') and not income.has_css_class('error')
    assert nothing.get_text() == ''
    assert not nothing.has_css_class('error') and not nothing.has_css_class('success')


def test_the_amount_column_sorts_by_currency_then_amount(oikos, clean_view):
    from gi.repository import Gtk
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('income', '84.10', 'EUR'),
    })
    column = oikos.get_column()

    class Item:
        def __init__(self, doc):
            self.id = doc
    compare = column._compare
    assert compare(Item(MORTGAGE), Item(ELECTRICITY), None) == Gtk.Ordering.SMALLER
    assert compare(Item(ELECTRICITY), Item(PERMIT), None) == Gtk.Ordering.SMALLER, \
        'a document without an amount sorts last'


def test_unloading_the_plugin_takes_the_column_away(clean_view):
    from oikos.column import COLUMN_NAME
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('miazoikos')
    assert system.load_plugin(info)
    clean_view.wait_until(
        lambda: COLUMN_NAME in clean_view.workspace.get_extra_columns(),
        message='the column is added')
    menu = clean_view.workspace._columns_menu
    items_with = menu.get_n_items()
    system.unload_plugin(info)
    clean_view.pump(0.3)
    assert COLUMN_NAME not in clean_view.workspace.get_extra_columns()
    assert menu.get_n_items() == items_with - 1, 'the chooser entry goes too'
    columns = clean_view.workspace.view.cv.get_columns()
    titles = [columns.get_item(i).get_title() for i in range(columns.get_n_items())]
    assert 'Amount' not in titles


def _filtered(oikos, clean_view, choice):
    """Show the three test documents, then narrow them with the filter."""
    clean_view.workspace.show_documents([MORTGAGE, ELECTRICITY, PERMIT])
    clean_view.pump(0.3)
    oikos.get_filter().set_choice(choice)
    clean_view.pump(0.3)
    return sorted(clean_view.displayed())


def test_the_filter_is_a_sidebar_dropdown_with_any_first(oikos, clean_view):
    from oikos.filter import LABELS
    from oikos.money import FILTERS
    dropdown = oikos.get_filter().dropdown
    assert clean_view.app.get_widget('plugin-MiAZOikos-dropdown') is dropdown
    assert dropdown in clean_view.app.get_widget('plugin-dropdowns')
    assert [key for key, _label in LABELS] == list(FILTERS)
    assert oikos.get_filter().get_choice() == 'any'


def test_the_filter_narrows_the_documents(oikos, clean_view):
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        PERMIT: Entry('income', '20', 'USD'),
    })
    assert _filtered(oikos, clean_view, 'expense') == [MORTGAGE]
    assert _filtered(oikos, clean_view, 'income') == [PERMIT]
    assert _filtered(oikos, clean_view, 'missing') == [ELECTRICITY]
    assert _filtered(oikos, clean_view, 'recorded') == sorted([MORTGAGE, PERMIT])
    assert _filtered(oikos, clean_view, 'any') == sorted([MORTGAGE, ELECTRICITY, PERMIT])


def test_clear_filters_resets_the_filter(oikos, clean_view):
    oikos.get_filter().set_choice('expense')
    clean_view.pump(0.2)
    clean_view.workspace.clear_filters()
    clean_view.pump(0.3)
    assert oikos.get_filter().get_choice() == 'any'


def test_the_totals_follow_the_filter(oikos, clean_view):
    """With nothing selected the view counts what is shown, and the filter
    decides what is shown."""
    from oikos.ledger import Entry
    oikos.set_entries({
        MORTGAGE: Entry('expense', '650.40', 'EUR'),
        ELECTRICITY: Entry('income', '84.10', 'EUR'),
    })
    _filtered(oikos, clean_view, 'expense')
    clean_view.select_documents()
    clean_view.workspace.show_view('oikos')
    view = oikos.get_view()
    clean_view.wait_until(
        lambda: view.stack.get_visible_child_name() == 'content',
        message='the totals are shown')
    totals = dict(view.chart.get_sections())['EUR'][0].totals
    assert totals.expense == Decimal('650.40')
    assert totals.income == Decimal('0'), 'the income is filtered out'


def test_unloading_the_plugin_takes_the_filter_away(clean_view):
    from oikos.filter import FILTER_NAME
    system = clean_view.service('plugin-system')
    info = system.get_plugin_info('miazoikos')
    assert system.load_plugin(info)
    clean_view.wait_until(
        lambda: clean_view.app.get_widget('plugin-MiAZOikos-dropdown') is not None,
        message='the filter is added')
    dropdown = clean_view.app.get_widget('plugin-MiAZOikos-dropdown')
    system.unload_plugin(info)
    clean_view.pump(0.3)
    assert FILTER_NAME not in clean_view.workspace._workspace_filters
    assert dropdown not in clean_view.app.get_widget('plugin-dropdowns')
    assert clean_view.app.get_widget('plugin-MiAZOikos-dropdown') is None
