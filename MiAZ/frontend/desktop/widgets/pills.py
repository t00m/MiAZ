# File: pills.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The 7-field filename rendered as colored pills, in a row or a table

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango

# One entry per filename field, in filename order: style key and title.
FIELDS = [
    ('Date', _('Date')),
    ('Country', _('Country')),
    ('Group', _('Group')),
    ('SentBy', _('Sent by')),
    ('Purpose', _('Purpose')),
    ('Concept', _('Concept')),
    ('SentTo', _('Sent to')),
]

# Shared palette: the workspace filter tags use these same colors.
FIELD_COLORS = {
    'Date':    '#cfe3ff',
    'Country': '#d6f5d6',
    'Group':   '#fff2c2',
    'SentBy':  '#ffd9e3',
    'Purpose': '#e7dbff',
    'Concept': '#ececec',
    'SentTo':  '#ffe2c7',
}


def item_fields(item):
    """Keys and descriptions of an indexed item, in filename order."""
    keys = [item.date, item.country, item.group, item.sentby_id,
            item.purpose, item.subtitle, item.sentto_id]
    labels = [item.date_dsc, item.country_dsc, item.group_dsc, item.sentby_dsc,
              item.purpose_dsc, item.subtitle, item.sentto_dsc]
    return keys, labels


def paint_pill(label, style, title, value, text='', highlight=False):
    """Dress a label as the pill of one field: colour, text and tooltip."""
    label.set_text(text or value or '?')
    for css in list(label.get_css_classes()):
        if css.startswith('miaz-pill'):
            label.remove_css_class(css)
    label.add_css_class('miaz-pill')
    label.add_css_class(f'miaz-pill-{style}' if value else 'miaz-pill-missing')
    if highlight:
        label.add_css_class('miaz-pill-highlight')
    label.set_tooltip_text(f'{title}: {value}' if text and value else title)
    label.set_ellipsize(Pango.EllipsizeMode.END)


class MiAZFieldPills(Gtk.Box):
    """Compact document identity: one small pill per filename field."""
    __gtype_name__ = 'MiAZFieldPills'
    _css_installed = False

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._install_css()

    def set_filename(self, filename, util):
        self.set_fields(util.get_fields(filename))

    def set_item(self, item, highlight=None):
        """Pills from an indexed item: descriptions on the pill, keys in the
        tooltip. The keys belong to the filename, which the Filenames view
        shows as it is."""
        keys, labels = item_fields(item)
        self.set_fields(keys, highlight=highlight, labels=labels)

    def set_fields(self, fields, highlight=None, labels=None):
        while (child := self.get_first_child()) is not None:
            self.remove(child)
        for position, (style, title) in enumerate(FIELDS):
            value = fields[position] if position < len(fields) else ''
            text = labels[position] if labels is not None and position < len(labels) else ''
            label = Gtk.Label()
            paint_pill(label, style, title, value, text,
                       highlight is not None and position == highlight)
            label.set_max_width_chars(24)
            self.append(label)

    @classmethod
    def _install_css(cls):
        if cls._css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        parts = [
            ".miaz-pill {"
            " padding: 1px 8px;"
            " border-radius: 999px;"
            " color: #2b2b2b; }",
            ".miaz-pill-missing { background-color: #f5c2c7; }",
            ".miaz-pill-highlight { font-weight: bold; }",
        ]
        for key, color in FIELD_COLORS.items():
            parts.append(f".miaz-pill-{key} {{ background-color: {color}; }}")
        css = "".join(parts)
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        cls._css_installed = True


class MiAZFieldTable(Gtk.Grid):
    """The same seven fields as a table: the field name, then its value as a
    pill, one per row. The rows share the height evenly, so the table can be
    made as tall as whatever sits beside it."""
    __gtype_name__ = 'MiAZFieldTable'

    def __init__(self):
        super().__init__(column_spacing=8, row_spacing=2)
        MiAZFieldPills._install_css()
        self.set_row_homogeneous(True)
        self.keys = []
        self.values = []
        for position, (style, title) in enumerate(FIELDS):
            key = Gtk.Label(label=f'{title}:', xalign=1)
            key.add_css_class('dim-label')
            value = Gtk.Label(xalign=0)
            value.set_halign(Gtk.Align.START)
            value.set_hexpand(True)
            value.set_max_width_chars(30)
            paint_pill(value, style, title, '')
            self.attach(key, 0, position, 1, 1)
            self.attach(value, 1, position, 1, 1)
            self.keys.append(key)
            self.values.append(value)

    def set_item(self, item, highlight=None):
        keys, labels = item_fields(item)
        self.set_fields(keys, highlight=highlight, labels=labels)

    def set_fields(self, fields, highlight=None, labels=None):
        for position, (style, title) in enumerate(FIELDS):
            value = fields[position] if position < len(fields) else ''
            text = labels[position] if labels is not None and position < len(labels) else ''
            paint_pill(self.values[position], style, title, value, text,
                       highlight is not None and position == highlight)
