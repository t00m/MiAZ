# File: editor.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Say what one or many documents are worth

from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from oikos.ledger import Entry
from oikos.money import EXPENSE, INCOME, format_amount, parse_amount
from oikos.vocabulary import Currency, currency_label

# The kind a document with no entry is shown with in the rename dialog tab.
NONE = 'none'

# The per-document list scrolls past this height instead of growing the dialog.
LIST_MAX_HEIGHT = 280


def _common(values):
    """The one value every item shares, or None when they differ."""
    values = set(values)
    return values.pop() if len(values) == 1 else None


def plain_amount(value):
    """An amount as it goes back into an entry: the locale's decimal
    separator, no grouping, so it reads back as the same amount."""
    return format_amount(value, places=max(2, -value.as_tuple().exponent),
                         thousands_sep='')


def mixed_hint(kind, currency):
    """Why the editor left the type or the currency unchosen, or ''."""
    if kind and currency:
        return _('These documents differ in type and in currency. Choose both '
                 'for all of them; amounts are not converted.')
    if kind:
        return _('These documents are not all the same type. Choose one for '
                 'all of them.')
    if currency:
        return _('These documents are not all in the same currency. Choose '
                 'one for all of them; amounts are not converted.')
    return ''


class MiAZOikosEditor(Gtk.Box):
    """Kind, currency and amount for a set of documents.

    Nothing is written here. The caller asks is_valid() and entries() and
    writes through the ledger, so Cancel changes nothing.

    With more than one document the amount is either one shared value or one
    per document; the list of entries is prefilled with what each document
    already has, so correcting one amount in twenty does not mean retyping
    nineteen.

    `allow_none` adds a third kind, Neither, for the rename dialog tab, where
    the user may also take a document's entry away.
    """
    __gtype_name__ = 'MiAZOikosEditor'
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app, ext, docs, allow_none=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.app = app
        self.ext = ext
        self.docs = list(docs)
        self.allow_none = allow_none
        self.util = app.get_service('util')
        self._amount_entries = {}

        # What the documents already disagree on, said in a hint above.
        self._mixed_kind = False
        self._mixed_currency = False

        existing = {doc: ext.ledger.get(doc) for doc in self.docs}
        known = [entry for entry in existing.values() if entry is not None]
        complete = len(known) == len(self.docs)

        self.hint = Gtk.Label(xalign=0.0, wrap=True)
        self.hint.add_css_class('dim-label')
        self.append(self.hint)
        self._build_kind(known)
        self._build_currency(known)
        self._build_amounts(existing, known, complete)
        hint = mixed_hint(self._mixed_kind, self._mixed_currency)
        self.hint.set_text(hint)
        self.hint.set_visible(bool(hint))
        self._sync_sensitivity()

    # Kind

    def _build_kind(self, known):
        kinds = [(INCOME, _('Income')), (EXPENSE, _('Expense'))]
        if self.allow_none:
            kinds.insert(0, (NONE, _('Neither')))
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class('linked')
        box.set_halign(Gtk.Align.START)
        self._kind_buttons = {}
        group = None
        for kind, label in kinds:
            button = Gtk.ToggleButton(label=label)
            if group is None:
                group = button
            else:
                button.set_group(group)
            box.append(button)
            self._kind_buttons[kind] = button

        # Documents that already disagree get no kind until the user picks
        # one: preselecting Expense would turn a salary into a bill on Apply.
        kinds_known = {entry.kind for entry in known}
        if len(kinds_known) > 1:
            chosen = None
            self._mixed_kind = True
        elif kinds_known:
            chosen = kinds_known.pop()
        else:
            chosen = NONE if self.allow_none else EXPENSE
        if chosen is not None:
            self._kind_buttons[chosen].set_active(True)
        # Connected only now, so building the editor emits nothing.
        for button in self._kind_buttons.values():
            button.connect('toggled', self._on_kind_toggled)
        self.append(self._row(_('Type'), box))

    def get_kind(self):
        for kind, button in self._kind_buttons.items():
            if button.get_active():
                return kind
        return None

    def _on_kind_toggled(self, button):
        if button.get_active():
            self._sync_sensitivity()
            self.emit('changed')

    # Currency

    def _build_currency(self, known):
        factory = self.app.get_service('factory')
        self.currency = factory.create_dropdown_generic(Currency, ellipsize=True,
                                                        enable_search=True)
        used = self.ext.config.load_used()
        codes = set(used)
        # A document may carry a currency the repository no longer enables;
        # it stays choosable here, or opening the editor would change it.
        codes.update(entry.currency for entry in known)
        items = [Currency(id=code, title=currency_label(code, used))
                 for code in sorted(codes)]
        model = self.currency.get_model().get_model().get_model()
        model.splice(0, model.get_n_items(), items)

        # As with the kind: documents in different currencies get none, or
        # Apply would relabel dollars as euros without converting anything.
        currencies = {entry.currency for entry in known}
        if len(currencies) > 1:
            chosen = None
            self._mixed_currency = True
        else:
            chosen = currencies.pop() if currencies else self.ext.default_currency()
        self.currency.set_selected(Gtk.INVALID_LIST_POSITION)
        for position, item in enumerate(items):
            if item.id == chosen:
                self.currency.set_selected(position)
                break
        self.currency.connect('notify::selected-item', lambda *args: self.emit('changed'))
        self.append(self._row(_('Currency'), self.currency))

    def get_currency(self):
        item = self.currency.get_selected_item()
        return item.id if item is not None else None

    # Amounts

    def _build_amounts(self, existing, known, complete):
        amounts = [entry.amount for entry in known]
        shared_value = _common(amounts) if complete else None

        self.same = None
        self.list_scroller = None
        if len(self.docs) > 1:
            # One shared amount unless the documents already differ.
            different = len(set(amounts)) > 1
            self.same = Gtk.CheckButton(label=_('Same amount for all documents'))
            self.same.set_active(not different)
            self.same.connect('toggled', self._on_same_toggled)
            self.append(self.same)

        self.shared = self._amount_entry()
        if shared_value is not None:
            self.shared.set_text(plain_amount(shared_value))
        self.shared_row = self._row(_('Amount'), self.shared)
        self.append(self.shared_row)
        if self.same is None:
            return

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class('boxed-list')
        for doc in self.docs:
            entry = self._amount_entry()
            if existing.get(doc) is not None:
                entry.set_text(plain_amount(existing[doc].amount))
            elif shared_value is not None:
                entry.set_text(plain_amount(shared_value))
            self._amount_entries[doc] = entry
            listbox.append(self._document_row(doc, entry))
        self.list_scroller = Gtk.ScrolledWindow()
        self.list_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_scroller.set_propagate_natural_height(True)
        self.list_scroller.set_max_content_height(LIST_MAX_HEIGHT)
        self.list_scroller.set_child(listbox)
        self.append(self.list_scroller)

    def _amount_entry(self):
        entry = Gtk.Entry()
        entry.set_input_purpose(Gtk.InputPurpose.NUMBER)
        entry.set_placeholder_text('0.00')
        entry.set_width_chars(12)
        entry.set_alignment(1.0)
        entry.set_activates_default(True)
        entry.connect('changed', self._on_amount_changed)
        return entry

    def _document_row(self, doc, entry):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_top(6)
        row.set_margin_bottom(6)
        row.set_margin_start(12)
        row.set_margin_end(12)
        label = Gtk.Label(label=self.describe(doc), xalign=0.0, hexpand=True)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_tooltip_text(doc)
        row.append(label)
        entry.set_valign(Gtk.Align.CENTER)
        row.append(entry)
        return row

    def describe(self, doc):
        """Date, sender and concept: what tells two invoices apart."""
        try:
            fields = self.util.get_fields(doc)
        except Exception:
            return doc
        if len(fields) != 7:
            return doc
        date, _country, _group, sentby, _purpose, concept, _sentto = fields
        return ' · '.join(part.replace('_', ' ') for part in (date, sentby, concept) if part)

    def _on_same_toggled(self, _button):
        self._sync_sensitivity()
        self.emit('changed')

    def _on_amount_changed(self, entry):
        self._mark(entry)
        self.emit('changed')

    def _mark(self, entry):
        valid = self._parse(entry) is not None
        if valid or not entry.get_text().strip():
            entry.remove_css_class('error')
        else:
            entry.add_css_class('error')

    @staticmethod
    def _parse(entry):
        try:
            return parse_amount(entry.get_text())
        except ValueError:
            return None

    def uses_shared_amount(self):
        return self.same is None or self.same.get_active()

    def _sync_sensitivity(self):
        active = self.get_kind() != NONE
        self.currency.set_sensitive(active)
        shared = self.uses_shared_amount()
        self.shared_row.set_visible(shared)
        self.shared.set_sensitive(active)
        if self.list_scroller is not None:
            self.list_scroller.set_visible(not shared)
            self.list_scroller.set_sensitive(active)

    # What the caller reads

    def is_valid(self):
        return self.entries() is not None

    def entries(self):
        """{doc: Entry} as typed, {} for Neither, None while anything is invalid."""
        kind = self.get_kind()
        if kind == NONE:
            return {}
        currency = self.get_currency()
        if kind is None or currency is None:
            return None
        if self.uses_shared_amount():
            amount = self._parse(self.shared)
            if amount is None:
                return None
            return {doc: Entry(kind, amount, currency) for doc in self.docs}
        result = {}
        for doc, entry in self._amount_entries.items():
            amount = self._parse(entry)
            if amount is None:
                return None
            result[doc] = Entry(kind, amount, currency)
        return result

    # Layout

    def _row(self, title, widget):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        label = Gtk.Label(label=title, xalign=0.0)
        label.set_size_request(90, -1)
        label.add_css_class('dim-label')
        box.append(label)
        widget.set_hexpand(isinstance(widget, Gtk.DropDown))
        box.append(widget)
        return box


class MiAZOikosTab(Gtk.Box):
    """Income or expense of one document, as a tab in the rename dialog.

    The editor only holds the choice; apply() writes it after the rename went
    through, against the document's new name, so Cancel changes nothing.
    """
    __gtype_name__ = 'MiAZOikosTab'

    def __init__(self, app, ext):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         hexpand=True, vexpand=True)
        self.app = app
        self.ext = ext
        self.editor = None
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        label = Gtk.Label(xalign=0.0)
        label.add_css_class('dim-label')
        label.set_wrap(True)
        label.set_text(_('Whether this document is money coming in or going out, and how much'))
        self.append(label)

    # Document tab contract
    def set_document(self, doc_id):
        if self.editor is not None:
            self.remove(self.editor)
        self.editor = MiAZOikosEditor(self.app, self.ext, [doc_id], allow_none=True)
        self.append(self.editor)

    def is_valid(self):
        return self.editor is None or self.editor.is_valid()

    def apply(self, old_id, new_id):
        """Write what the tab holds. True when something actually changed."""
        if self.editor is None:
            return False
        entries = self.editor.entries()
        if entries is None:
            return False
        if not entries:
            return self.ext.clear_documents([new_id]) > 0
        entry = entries[old_id]
        return self.ext.set_entries({new_id: entry}) > 0
