#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: postit.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Post-it board popover for MiAZNotes. Shows every note attached to
#              a document as a sticky note (light yellow card with a pushpin).
"""

from gettext import gettext as _
from typing import Callable, Optional

from gi.repository import GLib
from gi.repository import Gtk


# Priority values that deserve a coloured accent on the card.
_PRIORITY_ACCENT = {
    'High': 'miaz-postit-prio-high',
    'Critical': 'miaz-postit-prio-critical',
}

PIN_ICON = 'io.github.t00m.MiAZ-view-pin-symbolic'


class NotesPostItBoard(Gtk.Popover):
    """A contextual popover that lays out a document's notes as post-its.

    Clicking a post-it opens the per-document notes window with that note
    selected; the footer opens the same window for adding/editing.
    """

    def __init__(self, app, store, log,
                 on_open_document: Callable[[str, Optional[str]], None]):
        super().__init__()
        self.app = app
        self.store = store
        self.log = log
        self._on_open_document = on_open_document
        self._document_id = ''
        self.add_css_class('miaz-postit-board')
        self.set_position(Gtk.PositionType.BOTTOM)
        self._build_ui()

    # UI
    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_size_request(460, -1)
        self.set_child(outer)

        self._title = Gtk.Label(xalign=0.0)
        self._title.add_css_class('heading')
        self._title.set_margin_top(12)
        self._title.set_margin_start(12)
        self._title.set_margin_end(12)
        self._title.set_margin_bottom(6)
        self._title.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        outer.append(self._title)

        self._flow = Gtk.FlowBox()
        self._flow.set_valign(Gtk.Align.START)
        self._flow.set_max_children_per_line(2)
        self._flow.set_min_children_per_line(1)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_row_spacing(12)
        self._flow.set_column_spacing(12)
        self._flow.set_homogeneous(True)
        self._flow.set_margin_start(12)
        self._flow.set_margin_end(12)
        self._flow.set_margin_bottom(12)
        self._flow.set_margin_top(0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(260)
        scroll.set_max_content_height(460)
        scroll.set_propagate_natural_height(True)
        scroll.set_child(self._flow)
        outer.append(scroll)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        footer.set_margin_start(12)
        footer.set_margin_end(12)
        footer.set_margin_bottom(12)
        footer.set_margin_top(0)
        footer.set_halign(Gtk.Align.END)
        self._btn_open = Gtk.Button(label=_('Open notes…'))
        self._btn_open.add_css_class('flat')
        self._btn_open.connect('clicked', self._on_open_clicked)
        footer.append(self._btn_open)
        outer.append(footer)

    # API
    def set_document(self, document_id: str):
        self._document_id = document_id or ''

    def refresh(self):
        child = self._flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flow.remove(child)
            child = nxt

        paths = self.store.list_for_document(self._document_id) if self._document_id else []
        self._title.set_text(
            _('{n} note(s) · {doc}').format(n=len(paths), doc=self._document_id))

        for note_path in paths:
            card = self._build_card(note_path)
            if card is not None:
                self._flow.append(card)

    # Card construction
    def _build_card(self, note_path: str):
        try:
            header, body = self.store.read(note_path)
        except Exception as error:
            self.log.warning(f"Post-it could not read '{note_path}': {error}")
            return None

        summary = self.store.summary_of(body) or _('(empty note)')
        category = (header.get('Category') or '').strip()
        priority = (header.get('Priority') or '').strip()
        status = (header.get('Status') or '').strip()
        date = (header.get('Date') or '').strip()

        button = Gtk.Button()
        button.add_css_class('miaz-postit')
        accent = _PRIORITY_ACCENT.get(priority)
        if accent:
            button.add_css_class(accent)
        button.set_hexpand(True)
        button.set_tooltip_text(summary)
        button.connect('clicked', self._on_card_clicked, note_path)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        pin = Gtk.Image.new_from_icon_name(PIN_ICON)
        pin.set_pixel_size(18)
        pin.add_css_class('miaz-postit-pin')
        pin.set_halign(Gtk.Align.CENTER)
        card.append(pin)

        lbl_summary = Gtk.Label(label=summary, xalign=0.0)
        lbl_summary.add_css_class('miaz-postit-summary')
        lbl_summary.set_wrap(True)
        lbl_summary.set_lines(4)
        lbl_summary.set_ellipsize(3)  # END
        lbl_summary.set_max_width_chars(26)
        card.append(lbl_summary)

        meta_bits = [b for b in (category, status) if b]
        if meta_bits:
            lbl_meta = Gtk.Label(label='  ·  '.join(meta_bits), xalign=0.0)
            lbl_meta.add_css_class('miaz-postit-meta')
            lbl_meta.set_ellipsize(3)
            card.append(lbl_meta)

        if date:
            lbl_date = Gtk.Label(label=date.split(' ')[0], xalign=0.0)
            lbl_date.add_css_class('miaz-postit-meta')
            card.append(lbl_date)

        button.set_child(card)
        return button

    # Callbacks
    def _on_card_clicked(self, _button, note_path: str):
        self.popdown()
        if self._on_open_document is not None and self._document_id:
            GLib.idle_add(self._on_open_document, self._document_id, note_path)

    def _on_open_clicked(self, _button):
        self.popdown()
        if self._on_open_document is not None and self._document_id:
            GLib.idle_add(self._on_open_document, self._document_id, None)
