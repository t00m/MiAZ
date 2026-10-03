# File: chart.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Income and expense bars, drawn with Cairo

import math
from gettext import gettext as _
from gettext import ngettext

import gi
gi.require_version('PangoCairo', '1.0')

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import PangoCairo

from oikos.money import format_amount, format_money

# Two series with fixed identities, so they wear the first two categorical
# slots (blue, orange), not green and red: those are status colors, and the
# pair is also the one red-green colorblind readers cannot tell apart.
# Stepped separately for the light and the dark surface.
COLORS = {
    'light': {'income': (0x2a, 0x78, 0xd6), 'expense': (0xeb, 0x68, 0x34)},
    'dark': {'income': (0x39, 0x87, 0xe5), 'expense': (0xd9, 0x59, 0x26)},
}

# Geometry, in pixels.
BAR = 12            # thickness of one bar; thin marks, never the whole band
BAR_GAP = 2         # surface gap between the income and the expense bar
RADIUS = 4          # rounded data end, square at the baseline
ROW_PAD = 10        # air between two rows
SECTION_GAP = 18    # air between two currencies
HEADER = 26         # height of a currency heading
LEGEND = 28         # height of the legend line
MARGIN = 12
LABEL_MAX = 0.32    # the label column takes at most this share of the width
VALUE_ROOM = 110    # room kept after the longest bar for its value

ROW_HEIGHT = 2 * BAR + BAR_GAP + ROW_PAD


def _rgb(triple, alpha=1.0):
    return (triple[0] / 255, triple[1] / 255, triple[2] / 255, alpha)


class MiAZOikosChart(Gtk.DrawingArea):
    """Horizontal income and expense bars, one pair per row, per currency.

    Each currency is a section with its own scale: an amount in yen and one
    in euros share no axis. Rows are what the view grouped the documents by
    (one row per currency when not grouped at all).

    Identity is never color alone: there is a legend, and every bar carries
    its value at the tip in the text color. Hovering a row gives its income,
    expense, net and document count.
    """
    __gtype_name__ = 'MiAZOikosChart'

    def __init__(self):
        super().__init__()
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        self.set_has_tooltip(True)
        self.connect('query-tooltip', self._on_query_tooltip)
        self._sections = []
        # (y0, y1, currency, row) for every row drawn, for the tooltip.
        self._hit = []
        self._style = Adw.StyleManager.get_default()
        self._dark_handler = self._style.connect('notify::dark',
                                                 lambda *args: self.queue_draw())

    def dispose_chart(self):
        """Stop following the style manager, which outlives this widget."""
        if self._dark_handler is not None:
            self._style.disconnect(self._dark_handler)
            self._dark_handler = None

    def set_sections(self, sections):
        """[(currency, [Row])], in the order they are drawn."""
        self._sections = [(currency, rows) for currency, rows in sections if rows]
        height = MARGIN * 2 + LEGEND
        for _currency, rows in self._sections:
            height += HEADER + len(rows) * ROW_HEIGHT + SECTION_GAP
        self.set_content_height(height)
        self.queue_draw()

    def get_sections(self):
        return list(self._sections)

    # Drawing

    def _palette(self):
        return COLORS['dark' if self._style.get_dark() else 'light']

    def _ink(self, alpha=1.0):
        color = self.get_color()
        return (color.red, color.green, color.blue, color.alpha * alpha)

    def _layout(self, text, bold=False, small=False):
        layout = self.create_pango_layout(text)
        if bold or small:
            attrs = Pango.AttrList()
            if bold:
                attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
            if small:
                attrs.insert(Pango.attr_scale_new(0.9))
            layout.set_attributes(attrs)
        return layout

    def _text(self, cr, text, x, y, rgba, bold=False, small=False,
              width=None, center_y=None):
        layout = self._layout(text, bold=bold, small=small)
        if width is not None:
            layout.set_width(int(width * Pango.SCALE))
            layout.set_ellipsize(Pango.EllipsizeMode.END)
        _ink, logical = layout.get_pixel_extents()
        if center_y is not None:
            y = center_y - logical.height / 2
        cr.set_source_rgba(*rgba)
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)
        return logical.width

    def _bar(self, cr, x, y, length, rgba):
        """A bar growing right from x: square at the baseline, round at the tip."""
        if length <= 0:
            return
        radius = min(RADIUS, length, BAR / 2)
        cr.new_path()
        cr.move_to(x, y)
        cr.line_to(x + length - radius, y)
        cr.arc(x + length - radius, y + radius, radius, -math.pi / 2, 0)
        cr.line_to(x + length, y + BAR - radius)
        cr.arc(x + length - radius, y + BAR - radius, radius, 0, math.pi / 2)
        cr.line_to(x, y + BAR)
        cr.close_path()
        cr.set_source_rgba(*rgba)
        cr.fill()

    def _draw(self, _area, cr, width, _height):
        self._hit = []
        if not self._sections:
            return
        palette = self._palette()
        ink = self._ink()
        muted = self._ink(0.7)
        faint = self._ink(0.18)

        # Legend: two series, so it is always there.
        x = MARGIN
        y = MARGIN
        for key, label in (('income', _('Income')), ('expense', _('Expense'))):
            cr.set_source_rgba(*_rgb(palette[key]))
            cr.rectangle(x, y + 4, 12, 12)
            cr.fill()
            x += 18
            x += self._text(cr, label, x, y, muted, center_y=y + 10) + 18
        y += LEGEND

        label_width = max(60, min(width * LABEL_MAX, self._widest_label() + 12))
        origin = MARGIN + label_width
        span = max(40, width - origin - MARGIN - VALUE_ROOM)

        for currency, rows in self._sections:
            self._text(cr, currency, MARGIN, y, ink, bold=True,
                       center_y=y + HEADER / 2)
            y += HEADER
            top = max(max(row.totals.income, row.totals.expense) for row in rows)
            section_top = y
            for row in rows:
                self._draw_row(cr, row, currency, y, origin, span, top,
                               label_width, palette, ink, muted)
                y += ROW_HEIGHT
            # The baseline every bar of this currency grows from.
            cr.set_source_rgba(*faint)
            cr.rectangle(origin - 1, section_top - 2, 1, y - section_top - ROW_PAD + 4)
            cr.fill()
            y += SECTION_GAP

    def _draw_row(self, cr, row, currency, y, origin, span, top, label_width,
                  palette, ink, muted):
        totals = row.totals
        self._text(cr, row.label, MARGIN, y, ink, width=label_width - 12,
                   center_y=y + BAR + BAR_GAP / 2)
        for index, (key, value) in enumerate((('income', totals.income),
                                              ('expense', totals.expense))):
            bar_y = y + index * (BAR + BAR_GAP)
            length = float(value / top) * span if top > 0 else 0
            # A value that is there but tiny still shows as a sliver.
            if value > 0:
                length = max(length, 2)
            self._bar(cr, origin, bar_y, length, _rgb(palette[key]))
            self._text(cr, format_amount(value), origin + length + 6, bar_y,
                       muted, small=True, center_y=bar_y + BAR / 2)
        self._hit.append((y - ROW_PAD / 2, y + ROW_HEIGHT - ROW_PAD / 2,
                          currency, row))

    def _widest_label(self):
        widest = 0
        for _currency, rows in self._sections:
            for row in rows:
                _ink, logical = self._layout(row.label).get_pixel_extents()
                widest = max(widest, logical.width)
        return widest

    # Tooltip

    def _on_query_tooltip(self, _widget, _x, y, _keyboard, tooltip):
        for y0, y1, currency, row in self._hit:
            if y0 <= y < y1:
                tooltip.set_text(tooltip_text(row, currency))
                return True
        return False


def tooltip_text(row, currency):
    """What hovering a row says, in text rather than color."""
    totals = row.totals
    return '\n'.join([
        row.label,
        _('Income: {amount}').format(amount=format_money(totals.income, currency)),
        _('Expense: {amount}').format(amount=format_money(totals.expense, currency)),
        _('Net: {amount}').format(
            amount=format_money(totals.net, currency, signed=True)),
        ngettext('{count} document', '{count} documents',
                 totals.count).format(count=totals.count),
    ])
