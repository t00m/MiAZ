# File: view.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Income and expenses of the selected documents

from gettext import gettext as _
from gettext import ngettext

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk

from oikos import aggregate
from oikos.chart import MiAZOikosChart
from oikos.money import format_money

# Coalesces a burst of selection changes (shift-click over fifty rows emits
# fifty) into one recount.
REFRESH_DELAY_MS = 120

GROUPING_LABELS = (
    (aggregate.GROUP_TOTAL, _('Total')),
    (aggregate.GROUP_YEAR, _('Year')),
    (aggregate.GROUP_MONTH, _('Month')),
    (aggregate.GROUP_GROUP, _('Group')),
    (aggregate.GROUP_SENTBY, _('Sent by')),
    (aggregate.GROUP_PURPOSE, _('Purpose')),
)


def group_key(item, grouping):
    """(key, label) of one document for a grouping; key None when unknown."""
    if grouping in (aggregate.GROUP_YEAR, aggregate.GROUP_MONTH):
        key = aggregate.date_key(item.date, grouping)
        return key, key
    if grouping == aggregate.GROUP_GROUP:
        return item.group or None, item.group_dsc or item.group
    if grouping == aggregate.GROUP_SENTBY:
        return item.sentby_id or None, item.sentby_dsc or item.sentby_id
    if grouping == aggregate.GROUP_PURPOSE:
        return item.purpose or None, item.purpose_dsc or item.purpose
    return None, None


class MiAZOikosView(Gtk.Box):
    """The money side of the documents selected in the other views.

    Details, Grid and Timeline share one selection, so whatever is selected
    there is what this view adds up. It follows the selection while on
    screen and does nothing while hidden, the contract every workspace view
    keeps: set_active(True) when shown, set_active(False) when not.
    """
    __gtype_name__ = 'MiAZOikosView'

    def __init__(self, app, ext):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.app = app
        self.ext = ext
        self._showing = False
        self._refresh_id = None
        self._missing = []
        self.workspace = app.get_widget('workspace')

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        self.stack.add_named(self._build_empty(), 'empty')
        self.stack.add_named(self._build_content(), 'content')
        self.append(self.stack)

        self._selection_handler = self.workspace.connect(
            'workspace-view-selection-changed', self._on_selection_changed)

    def dispose_view(self):
        """Let go of the workspace and the style manager, which outlive this."""
        if self._selection_handler is not None:
            self.workspace.disconnect(self._selection_handler)
            self._selection_handler = None
        self._cancel_refresh()
        self.chart.dispose_chart()

    # Building

    def _build_empty(self):
        self.status = Adw.StatusPage()
        self.status.set_icon_name('accessories-calculator-symbolic')
        self.set_button = Gtk.Button(label=_('Set income or expense…'))
        self.set_button.add_css_class('pill')
        self.set_button.add_css_class('suggested-action')
        self.set_button.set_halign(Gtk.Align.CENTER)
        self.set_button.connect('clicked', lambda *args: self.ext.edit_selection())
        self.status.set_child(self.set_button)
        return self.status

    def _build_content(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Filters in one row above the chart.
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label=_('Group by'))
        label.add_css_class('dim-label')
        bar.append(label)
        self.grouping = Gtk.DropDown.new_from_strings(
            [title for _key, title in GROUPING_LABELS])
        saved = self.ext.plugin.get_config_key('grouping')
        keys = [key for key, _title in GROUPING_LABELS]
        if saved in keys:
            self.grouping.set_selected(keys.index(saved))
        self.grouping.connect('notify::selected', self._on_grouping_changed)
        bar.append(self.grouping)
        self.counter = Gtk.Label(xalign=0.0, hexpand=True)
        self.counter.add_css_class('dim-label')
        self.counter.set_margin_start(12)
        bar.append(self.counter)
        edit = Gtk.Button(label=_('Set income or expense…'))
        edit.connect('clicked', lambda *args: self.ext.edit_selection())
        bar.append(edit)
        box.append(bar)

        # One tile per currency: the headline numbers, as text.
        self.tiles = Gtk.FlowBox()
        self.tiles.set_selection_mode(Gtk.SelectionMode.NONE)
        self.tiles.set_homogeneous(True)
        self.tiles.set_max_children_per_line(4)
        self.tiles.set_column_spacing(12)
        self.tiles.set_row_spacing(12)
        box.append(self.tiles)

        # Selected documents that have nothing recorded yet.
        self.missing_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.missing_label = Gtk.Label(xalign=0.0, hexpand=True, wrap=True)
        self.missing_bar.append(self.missing_label)
        missing_button = Gtk.Button(label=_('Set for these…'))
        missing_button.connect('clicked', self._on_set_missing)
        self.missing_bar.append(missing_button)
        box.append(self.missing_bar)

        self.chart = MiAZOikosChart()
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self.chart)
        box.append(scroller)
        return box

    def _tile(self, currency, totals):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        frame.add_css_class('card')
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        inner.set_margin_start(12)
        inner.set_margin_end(12)
        title = Gtk.Label(label=currency, xalign=0.0)
        title.add_css_class('heading')
        inner.append(title)
        # Net is the headline, so it is the one that is signed and emphasised.
        for caption, value, is_net in (
                (_('Income'), totals.income, False),
                (_('Expense'), totals.expense, False),
                (_('Net'), totals.net, True)):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            name = Gtk.Label(label=caption, xalign=0.0, hexpand=True)
            name.add_css_class('dim-label')
            amount = Gtk.Label(label=format_money(value, currency, signed=is_net),
                               xalign=1.0)
            amount.add_css_class('numeric')
            if is_net:
                amount.add_css_class('heading')
            row.append(name)
            row.append(amount)
            inner.append(row)
        frame.append(inner)
        return frame

    # Following the selection

    def set_active(self, active):
        """Say whether this is the view on screen."""
        if active == self._showing:
            return
        self._showing = active
        if active:
            self.refresh()
        else:
            self._cancel_refresh()

    def is_showing(self):
        return self._showing

    def _on_selection_changed(self, *args):
        self.queue_refresh()

    def _on_grouping_changed(self, *args):
        self.ext.plugin.set_config_key('grouping', self.get_grouping())
        self.refresh()

    def get_grouping(self):
        index = self.grouping.get_selected()
        if 0 <= index < len(GROUPING_LABELS):
            return GROUPING_LABELS[index][0]
        return aggregate.GROUP_TOTAL

    def queue_refresh(self):
        if not self._showing or self._refresh_id is not None:
            return
        self._refresh_id = GLib.timeout_add(REFRESH_DELAY_MS, self._on_refresh_due)

    def _on_refresh_due(self):
        self._refresh_id = None
        self.refresh()
        return GLib.SOURCE_REMOVE

    def _cancel_refresh(self):
        if self._refresh_id is not None:
            GLib.source_remove(self._refresh_id)
            self._refresh_id = None

    def refresh(self):
        """Recount the selection. Cheap: the ledger is in memory."""
        self._cancel_refresh()
        items = list(self.workspace.get_selected_items() or [])
        ledger = self.ext.ledger
        counted = []
        self._missing = []
        for item in items:
            entry = ledger.get(item.id)
            if entry is None:
                self._missing.append(item.id)
            else:
                counted.append((item, entry))

        if not items:
            self._show_empty(_('No documents selected'),
                             _('Select documents in Details, Grid or Timeline to see their income and expenses here.'),
                             can_set=False)
            return
        if not counted:
            self._show_empty(_('No income or expenses yet'),
                             ngettext('The selected document has no income or expense recorded.',
                                      'None of the {count} selected documents has an income or expense recorded.',
                                      len(items)).format(count=len(items)),
                             can_set=True)
            return

        self.stack.set_visible_child_name('content')
        self.counter.set_text(ngettext('{counted} of {count} selected document counted',
                                       '{counted} of {count} selected documents counted',
                                       len(items)).format(counted=len(counted), count=len(items)))

        totals = aggregate.summarize(entry for _item, entry in counted)
        self._fill_tiles(totals)

        if self._missing:
            self.missing_label.set_text(ngettext(
                '{count} selected document has no income or expense and is not counted.',
                '{count} selected documents have no income or expense and are not counted.',
                len(self._missing)).format(count=len(self._missing)))
        self.missing_bar.set_visible(bool(self._missing))

        grouping = self.get_grouping()
        if grouping == aggregate.GROUP_TOTAL:
            sections = [(currency, [aggregate.Row(key=currency, label=_('Total'), totals=t)])
                        for currency, t in totals.items()]
        else:
            pairs = [group_key(item, grouping) + (entry,) for item, entry in counted]
            unknown = (_('No date') if grouping in aggregate.CHRONOLOGICAL
                       else _('Unknown'))
            sections = list(aggregate.breakdown(pairs, grouping, unknown).items())
        self.chart.set_sections(self._default_first(sections))

    def _default_first(self, sections):
        default = self.ext.default_currency()
        return sorted(sections, key=lambda pair: (pair[0] != default, pair[0]))

    def _fill_tiles(self, totals):
        child = self.tiles.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.tiles.remove(child)
            child = following
        for currency, value in self._default_first(list(totals.items())):
            self.tiles.append(self._tile(currency, value))

    def _show_empty(self, title, description, can_set):
        self.status.set_title(title)
        self.status.set_description(description)
        self.set_button.set_visible(can_set)
        self.chart.set_sections([])
        self.stack.set_visible_child_name('empty')

    def _on_set_missing(self, *args):
        if self._missing:
            self.ext.edit_documents(list(self._missing))

    def get_missing(self):
        return list(self._missing)
