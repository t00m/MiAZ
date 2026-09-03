# File: timelineview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Chronological reading view of the filtered documents

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.thumbnails import request_thumbnail
from MiAZ.backend.util import date_is_valid, UNKNOWN_DATE
from MiAZ.frontend.desktop.widgets.filetypebadge import MiAZFileTypeBadge
from MiAZ.frontend.desktop.widgets.pills import MiAZFieldTable

log = MiAZLog('MiAZ.Timeline')

# A stretch at least this long collapses into a dashed gap marker.
GAP_MONTHS = 6

# Width the card thumbnail is rendered at.
THUMBNAIL_WIDTH = 320

# The box the preview is shown in: an A4 page at this height fits it.
PREVIEW_WIDTH = 136
PREVIEW_HEIGHT = 180


def two_party_split(pairs):
    """(left, right) when the set moves between exactly two parties, else None."""
    parties = set()
    for sentby, sentto in pairs:
        parties.add(sentby)
        parties.add(sentto)
        # A third party settles it: no later pair can take the count back down,
        # so the whole repository need not be walked to answer "not two".
        if len(parties) > 2:
            return None
    if len(parties) != 2:
        return None
    left, right = sorted(parties)
    return left, right


def months_between(sdate1, sdate2):
    """Whole months from sdate1 to sdate2, both YYYYMMDD; 0 when either is not a date."""
    if not (date_is_valid(sdate1) and date_is_valid(sdate2)):
        return 0
    first = datetime.strptime(sdate1, '%Y%m%d')
    second = datetime.strptime(sdate2, '%Y%m%d')
    return (second.year - first.year) * 12 + (second.month - first.month)


def timeline_marks(prev_sdate, sdate):
    """What to draw above a card: (year or None, gap months or None)."""
    year = sdate[:4] if (prev_sdate is None or sdate[:4] != prev_sdate[:4]) else None
    gap = None
    if prev_sdate is not None and UNKNOWN_DATE not in (prev_sdate, sdate):
        months = months_between(prev_sdate, sdate)
        if months >= GAP_MONTHS:
            gap = months
    return year, gap


class TimelineCard(Gtk.Box):
    """One entry: a headline beside the spine, its detail underneath.

    The shape is the one a printed timeline uses. A rule runs down the middle,
    every entry sits on one side of it with an arrow pointing back at the rule,
    and the headline carries what names the document while the box under it
    carries the rest.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.marks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # A centre box, not a homogeneous one: homogeneous shares the width
        # between all three children, which gave the rule a third of the row.
        # This gives the rule its own width and the halves the rest.
        self.row = Gtk.CenterBox()
        self.left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.left.add_css_class('miaz-timeline-half')
        self.left.set_hexpand(True)
        self.right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right.add_css_class('miaz-timeline-half')
        self.right.set_hexpand(True)
        # The rule. Every row draws its own segment, so they meet and read as
        # one line without anything having to be drawn over the list.
        self.spine = Gtk.Box()
        self.spine.add_css_class('miaz-timeline-spine')
        self.row.set_start_widget(self.left)
        self.row.set_center_widget(self.spine)
        self.row.set_end_widget(self.right)

        # The card: a headline with an arrow, then the detail box.
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.head_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.head.add_css_class('miaz-timeline-head')
        self.head.set_hexpand(True)
        self.label_concept = Gtk.Label(xalign=0.5)
        self.label_concept.add_css_class('miaz-timeline-title')
        self.label_concept.set_wrap(True)
        self.label_concept.set_justify(Gtk.Justification.CENTER)
        self.label_date = Gtk.Label(xalign=0.5)
        self.label_date.add_css_class('miaz-timeline-date')
        self.head.append(self.label_concept)
        self.head.append(self.label_date)
        self.arrow = Gtk.Image()
        self.arrow.add_css_class('miaz-timeline-arrow')
        self.arrow.set_pixel_size(24)
        self.arrow.set_valign(Gtk.Align.CENTER)
        self.head_row.append(self.head)
        self.head_row.append(self.arrow)

        # The detail box: the preview on the left, the fields beside it as a
        # table that stretches to the preview's height.
        self.body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.body.add_css_class('miaz-timeline-body')
        # An overlay over a fixed box: the box sets the size, so the page
        # never asks for its own width and every card keeps the same column.
        self.preview = Gtk.Overlay()
        self.preview.set_halign(Gtk.Align.START)
        self.preview.set_valign(Gtk.Align.START)
        frame = Gtk.Box()
        frame.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.preview.set_child(frame)
        self.thumbnail = Gtk.Picture()
        self.thumbnail.set_can_shrink(True)
        self.thumbnail.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.thumbnail.set_visible(False)
        # Shown instead of the page when the file type has no preview.
        self.badge = MiAZFileTypeBadge()
        self.badge.set_visible(False)
        self.preview.add_overlay(self.thumbnail)
        self.preview.add_overlay(self.badge)
        self.fields = MiAZFieldTable()
        self.fields.set_hexpand(True)
        self.fields.set_vexpand(True)
        self.body.append(self.preview)
        self.body.append(self.fields)

        self.card.append(self.head_row)
        self.card.append(self.body)
        self.append(self.marks)
        self.append(self.row)
        self._doc = None

    def update(self, item, prev, split, app, position=0):
        while (child := self.marks.get_first_child()) is not None:
            self.marks.remove(child)
        year, gap = timeline_marks(prev.date if prev is not None else None, item.date)
        if gap is not None:
            gap_label = Gtk.Label(label=_('No documents for {months} months').format(months=gap))
            gap_label.add_css_class('dim-label')
            gap_label.add_css_class('miaz-timeline-gap')
            self.marks.append(gap_label)
        if year is not None:
            self.marks.append(self._year_separator(year))

        self.label_concept.set_text(item.subtitle or os.path.basename(item.id))
        self.label_date.set_text(item.date_dsc)
        self.fields.set_item(item)

        # Which side. With exactly two parties the side says who sent it, which
        # is worth reading. Otherwise the entries simply alternate: it keeps the
        # shape of a timeline, and no meaning is claimed for the side.
        if split is not None:
            on_right = item.sentby_id == split[1]
        else:
            on_right = bool(position % 2)
        self._place(on_right)
        self._paint(position)
        self._load_thumbnail(item, app)

    def _place(self, on_right):
        """Move the card to its side and turn the arrow towards the spine."""
        target = self.right if on_right else self.left
        parent = self.card.get_parent()
        if parent is not target:
            if parent is not None:
                parent.remove(self.card)
            target.append(self.card)
        # The arrow is the first thing on a right-hand card and the last thing
        # on a left-hand one, so it always points back at the rule.
        first = self.head_row.get_first_child()
        if on_right and first is not self.arrow:
            self.head_row.reorder_child_after(self.head, self.arrow)
        elif not on_right and first is self.arrow:
            self.head_row.reorder_child_after(self.arrow, self.head)
        self.arrow.set_from_icon_name(
            'pan-start-symbolic' if on_right else 'pan-end-symbolic')
        for widget, css in ((self.head, 'miaz-timeline-head'),
                            (self.body, 'miaz-timeline-body')):
            widget.remove_css_class(f'{css}-right')
            widget.remove_css_class(f'{css}-left')
            widget.add_css_class(f'{css}-right' if on_right else f'{css}-left')

    def _paint(self, position):
        """Alternate the two tones, the way a printed timeline does."""
        tone = 'a' if position % 2 == 0 else 'b'
        other = 'b' if tone == 'a' else 'a'
        for widget, css in ((self.head, 'miaz-timeline-head'),
                            (self.body, 'miaz-timeline-body'),
                            (self.arrow, 'miaz-timeline-arrow')):
            widget.remove_css_class(f'{css}-{other}')
            widget.add_css_class(f'{css}-{tone}')

    def _year_separator(self, year):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        label = Gtk.Label(label=_('No date') if year == UNKNOWN_DATE[:4] else year)
        label.add_css_class('title-4')
        for widget in (Gtk.Separator(), label, Gtk.Separator()):
            if isinstance(widget, Gtk.Separator):
                widget.set_hexpand(True)
                widget.set_valign(Gtk.Align.CENTER)
            box.append(widget)
        return box

    def _load_thumbnail(self, item, app):
        self.thumbnail.set_visible(False)
        self.badge.set_visible(False)
        repo = app.get_service('repo')
        filepath = os.path.join(repo.docs, os.path.basename(item.id))
        self._doc = filepath
        cache_dir = os.path.join(ENV['LPATH']['CACHE'], 'thumbnails')
        request_thumbnail(
            filepath, cache_dir, THUMBNAIL_WIDTH,
            on_done=lambda path, doc=filepath: self._show_thumbnail(doc, path),
            is_wanted=lambda doc=filepath: doc == self._doc)

    def _show_thumbnail(self, doc, path):
        # The row may have been recycled for another document meanwhile.
        if doc != self._doc:
            return
        if path is None:
            self.badge.set_filepath(doc)
            self.badge.set_visible(True)
            return
        self.thumbnail.set_filename(path)
        self.thumbnail.set_visible(True)


class MiAZTimelineView(Gtk.Box):
    """Pure view over the filtered set; the sidebar does all the filtering."""
    __gtype_name__ = 'MiAZTimelineView'
    _css_installed = False

    def __init__(self, app, model=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZTimelineView')
        self._install_css()
        self._split = None
        # Pending rebind, so a burst of model changes costs one pass.
        self._rebind_id = None
        # True while this page is the one on screen. The list carries no model
        # otherwise, so a hidden page builds no rows and renders no pages.
        self._showing = False
        # Set when the documents changed while hidden, read when shown again.
        self._stale = True
        # Any Gio.ListModel of MiAZItem works; plugins can hand in their own.
        if model is None:
            model = self.app.get_widget('workspace-view').filter_model
        sorter = Gtk.CustomSorter.new(self._sort_by_date)
        self.sort_model = Gtk.SortListModel(model=model, sorter=sorter)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_setup)
        factory.connect('bind', self._on_bind)
        self.listview = Gtk.ListView(factory=factory)
        self.listview.add_css_class('miaz-timeline')
        self.listview.connect('activate', self._on_activate)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        scrwin.set_child(self.listview)
        self.append(scrwin)
        self.sort_model.connect('items-changed', self._on_items_changed)
        # The list gets its model when the page is shown, not before. An
        # Adw.ViewStack measures the pages it is not showing, which was enough
        # to make this one build hundreds of rows, each rendering a PDF, while
        # the user was looking at the document list.
        self.connect('map', self._on_map)
        self.connect('unmap', self._on_unmap)

    def _sort_by_date(self, item1, item2, data):
        return (item1.date > item2.date) - (item1.date < item2.date)

    def set_active(self, active):
        """Say whether this is the page on screen.

        An Adw.ViewStack maps a page the first time it is shown and never
        unmaps it again, so 'unmap' alone cannot tell the view it has been
        switched away from: whoever owns the stack has to say. Inactive means
        no model, which means no rows, no cards and nothing rendered.
        """
        if active == self._showing:
            return
        self._showing = active
        if active:
            if self._stale:
                self.refresh_split()
            self.listview.set_model(Gtk.NoSelection(model=self.sort_model))
        else:
            self._cancel_rebind()
            self.listview.set_model(None)

    def _cancel_rebind(self):
        if self._rebind_id is not None:
            GLib.source_remove(self._rebind_id)
            self._rebind_id = None

    def _on_map(self, *args):
        # For an owner that does not drive set_active, such as a plugin
        # embedding this view in a container of its own.
        self.set_active(True)

    def _on_unmap(self, *args):
        self.set_active(False)

    def _on_items_changed(self, *args):
        self._stale = True
        if self._showing:
            self.refresh_split()
            self._schedule_rebind()

    def get_split(self):
        """The two parties the set moves between, or None. Answered lazily.

        A hidden page does not follow the filters, so the answer is worked out
        on the first ask after the documents changed.
        """
        if self._stale:
            self.refresh_split()
        return self._split

    def refresh_split(self):
        def pairs():
            for position in range(self.sort_model.get_n_items()):
                item = self.sort_model.get_item(position)
                yield item.sentby_id, item.sentto_id

        # A generator, so two_party_split can stop at the third party rather
        # than making the whole repository into a list first.
        self._split = two_party_split(pairs())
        self._stale = False
        if self._split is None:
            self.listview.remove_css_class('miaz-timeline-two')
            self.listview.add_css_class('miaz-timeline-one')
        else:
            self.listview.remove_css_class('miaz-timeline-one')
            self.listview.add_css_class('miaz-timeline-two')

    def _schedule_rebind(self):
        """Ask for a rebind on the next idle, coalescing bursts into one.

        The model cannot be swapped from inside its own items-changed
        emission: GTK is halfway through updating the rows it lists and
        crashes. The swap therefore waits for the main loop.
        """
        if self._rebind_id is None:
            self._rebind_id = GLib.idle_add(self._rebind)

    def _rebind(self):
        # A fresh selection model rebinds every row, so cards change sides
        # and the year and gap marks are recomputed against their neighbour.
        self._rebind_id = None
        if self._showing:
            self.listview.set_model(Gtk.NoSelection(model=self.sort_model))
        return GLib.SOURCE_REMOVE

    def _on_setup(self, factory, list_item):
        list_item.set_child(TimelineCard())

    def _on_bind(self, factory, list_item):
        position = list_item.get_position()
        prev = self.sort_model.get_item(position - 1) if position > 0 else None
        list_item.get_child().update(list_item.get_item(), prev, self._split,
                                     self.app, position)

    def _on_activate(self, listview, position):
        item = listview.get_model().get_item(position)
        self.app.get_service('actions').document_display(item.id)

    @classmethod
    def _install_css(cls):
        if cls._css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        # Two tones alternating down the page, a rule between the columns and
        # an arrow from each headline back to it. The colours are written out
        # rather than taken from the theme, the way the pills and the filter
        # tags already are.
        css = (
            ".miaz-timeline-half { padding: 4px 14px; }"
            ".miaz-timeline-spine {"
            " min-width: 4px;"
            " background-color: #2b2b2b; }"
            ".miaz-timeline-head {"
            " padding: 8px 14px;"
            " border: 1px solid;"
            " border-radius: 4px;"
            " color: #2b2b2b; }"
            ".miaz-timeline-title { font-weight: bold; }"
            ".miaz-timeline-date { font-size: 0.85em; }"
            ".miaz-timeline-body {"
            " padding: 8px 14px;"
            " margin-bottom: 10px;"
            " border: 1px solid;"
            " border-top: none;"
            " border-radius: 0 0 4px 4px;"
            " background-color: #ffffff; }"
            # The lit tone and the quiet one.
            ".miaz-timeline-head-a {"
            " background-color: #f4f4c3;"
            " border-color: #cfcf7a; }"
            ".miaz-timeline-body-a { border-color: #cfcf7a; }"
            ".miaz-timeline-arrow-a { color: #c5d92b; }"
            ".miaz-timeline-head-b {"
            " background-color: #efefef;"
            " border-color: #cfcfcf; }"
            ".miaz-timeline-body-b { border-color: #cfcfcf; }"
            ".miaz-timeline-arrow-b { color: #b8b8b8; }"
            # The head is rounded away from the spine, square towards it.
            ".miaz-timeline-head-left { border-radius: 4px 4px 0 0; }"
            ".miaz-timeline-head-right { border-radius: 4px 4px 0 0; }"
            ".miaz-timeline-gap { font-style: italic; }"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        cls._css_installed = True
