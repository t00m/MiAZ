# File: filter.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The income or expense filter in the sidebar

from gettext import gettext as _

from gi.repository import Gtk

from oikos.money import (FILTER_ANY, FILTER_EXPENSE, FILTER_INCOME,
                         FILTER_MISSING, FILTER_RECORDED, filter_matches)

FILTER_NAME = 'MiAZOikos'

LABELS = (
    (FILTER_ANY, _('Any amount')),
    (FILTER_INCOME, _('Income')),
    (FILTER_EXPENSE, _('Expense')),
    (FILTER_RECORDED, _('With an amount')),
    (FILTER_MISSING, _('Without an amount')),
)


class MiAZOikosFilter:
    """A sidebar dropdown that narrows the documents by income or expense.

    It is ANDed with the other filters through register_filter_view, and a
    change goes through workspace.filters_changed(), the pass the built-in
    dropdowns take, so the totals view follows it too.
    """

    def __init__(self, ext):
        self.ext = ext
        self.dropdown = Gtk.DropDown.new_from_strings([label for _key, label in LABELS])
        self.dropdown.set_tooltip_text(_('Filter by income or expense'))
        self.dropdown.connect('notify::selected', self._on_changed)

    def get_choice(self):
        index = self.dropdown.get_selected()
        if 0 <= index < len(LABELS):
            return LABELS[index][0]
        return FILTER_ANY

    def set_choice(self, choice):
        keys = [key for key, _label in LABELS]
        self.dropdown.set_selected(keys.index(choice))

    def matches(self, item, _filter_model=None):
        """The per-document condition the workspace calls on every refilter."""
        choice = self.get_choice()
        if choice == FILTER_ANY:
            # Inactive: no ledger lookup on each of a thousand rows.
            return True
        ledger = self.ext.ledger
        entry = ledger.get(item.id) if ledger is not None else None
        return filter_matches(choice, entry.kind if entry is not None else None)

    def _on_changed(self, *args):
        self.ext.workspace.filters_changed()
