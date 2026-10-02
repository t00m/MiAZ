# File: column.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The Amount column of the Details table

from gettext import gettext as _

from gi.repository import Gtk

from oikos.money import EXPENSE, INCOME, amount_cell

COLUMN_NAME = 'oikos-amount'

# libadwaita style classes: they follow the light and dark palettes.
STYLE = {INCOME: 'success', EXPENSE: 'error'}


class MiAZOikosColumn:
    """A Details column with each document's income or expense.

    The cells read the ledger when they are bound, so a change to an amount
    shows after workspace.refresh_rows(). Sorting puts documents with an
    amount first, grouped by currency, from the largest expense to the
    largest income; amounts in different currencies are never compared.
    """

    def __init__(self, ext):
        self.ext = ext
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_setup)
        factory.connect('bind', self._on_bind)
        self.factory = factory
        self.column = Gtk.ColumnViewColumn.new(_('Amount'), factory)
        self.column.set_resizable(True)
        self.column.set_sorter(Gtk.CustomSorter.new(self._compare, None))

    def _on_setup(self, _factory, list_item):
        label = Gtk.Label(xalign=1.0)
        label.add_css_class('numeric')
        list_item.set_child(label)

    def _on_bind(self, _factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if label is None:
            return
        # Recycled cells keep the last row's style; start from none.
        for style in STYLE.values():
            label.remove_css_class(style)
        entry = None
        if item is not None and self.ext.ledger is not None:
            entry = self.ext.ledger.get(item.id)
        if entry is None:
            label.set_text('')
            return
        text, kind = amount_cell(entry.kind, entry.amount, entry.currency)
        label.set_text(text)
        label.add_css_class(STYLE[kind])

    def _key(self, item):
        entry = self.ext.ledger.get(item.id) if self.ext.ledger is not None else None
        if entry is None:
            return (1, '', 0)
        return (0, entry.currency, entry.signed)

    def _compare(self, item1, item2, _data):
        a, b = self._key(item1), self._key(item2)
        if a == b:
            return Gtk.Ordering.EQUAL
        return Gtk.Ordering.SMALLER if a < b else Gtk.Ordering.LARGER
