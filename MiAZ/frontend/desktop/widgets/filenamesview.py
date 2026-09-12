# File: filenamesview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The filtered documents as their raw filenames, keys and all

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from gettext import gettext as _

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.pills import FIELDS, FIELD_COLORS

# Which column of the document list sorts each field of the filename. The
# order of a view is the order of the shared model, so sorting here sorts
# the list itself and the two cannot drift apart.
FIELD_COLUMNS = {
    'Date': 'column_date',
    'Country': 'column_country',
    'Group': 'column_group',
    'SentBy': 'column_sentby',
    'Purpose': 'column_purpose',
    'Concept': 'column_subtitle',
    'SentTo': 'column_sentto',
    # Not a filename field, but the row ends with it and the list can sort it.
    'Extension': 'column_extension',
}


class FilenameRow(Gtk.Box):
    """One filename, in a fixed width font, each field on its own colour.

    The other views show descriptions. This one shows what is on disk, so
    the keys a filter or a rename will act on can be read off the row.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class('miaz-filename-row')
        self.label = Gtk.Label(xalign=0)
        self.label.add_css_class('monospace')
        self.label.set_selectable(False)
        self.append(self.label)

    def update(self, item, util):
        basename = item.id
        fields = util.get_fields(basename)
        self.set_tooltip_text(basename)
        if len(fields) != 7:
            self.label.set_text(basename)
            return
        stem, dot, extension = basename.rpartition('.')
        parts = []
        for position, (style, _title) in enumerate(FIELDS):
            value = GLib.markup_escape_text(fields[position]) or ' '
            colour = FIELD_COLORS[style]
            parts.append(f'<span background="{colour}">{value}</span>')
        markup = '-'.join(parts)
        if dot:
            markup += GLib.markup_escape_text(f'.{extension}')
        self.label.set_markup(markup)


class MiAZFilenamesView(Gtk.Box):
    """Pure view over the filtered set, one raw filename per row.

    Shares the document list's selection, so picking here is picking in the
    workspace; double click opens the document and right click is the same
    menu the list has.
    """
    __gtype_name__ = 'MiAZFilenamesView'
    _css_installed = False

    def __init__(self, app, model=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZFilenamesView')
        self._install_css()
        self._showing = False
        self.view = self.app.get_widget('workspace-view')
        self.selection = None if model is not None else self.view.get_selection()
        if model is None:
            model = self.view.filter_model
        self.model = model
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_setup)
        factory.connect('bind', self._on_bind)
        self.listview = Gtk.ListView(factory=factory)
        self.listview.add_css_class('miaz-filenames')
        self.listview.set_enable_rubberband(True)
        self.listview.connect('activate', self._on_activate)
        self._context_popover = Gtk.PopoverMenu()
        self._context_popover.set_parent(self.listview)
        self._context_popover.set_has_arrow(False)
        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        gesture.connect('pressed', self._on_right_click)
        self.listview.add_controller(gesture)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        scrwin.set_child(self.listview)
        self.append(scrwin)
        self.connect('map', lambda *_a: self.set_active(True))
        self.connect('unmap', lambda *_a: self.set_active(False))
        # The header sorts the shared model, so only a view that shares it
        # gets one. A plugin handing in its own model sorts that itself.
        self._header_buttons = {}
        self._header_arrows = {}
        if self.selection is not None:
            self.prepend(self._build_header())
            sorter = self.view.cv.get_sorter()
            if sorter is not None:
                sorter.connect('changed', lambda *_a: self._sync_header())
            self._sync_header()

    def set_active(self, active):
        """Say whether this is the view on screen. Inactive means no model."""
        if active == self._showing:
            return
        self._showing = active
        if active:
            self.listview.set_model(self._selection_model())
        else:
            self.listview.set_model(None)

    def _selection_model(self):
        if self.selection is not None:
            return self.selection
        return Gtk.MultiSelection.new(self.model)

    def _build_header(self):
        """One button per field, in filename order, on the field's colour."""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        header.add_css_class('miaz-filenames-header')
        # The seven fields in filename order, then the extension, which is
        # where it sits on the row.
        for style, title in list(FIELDS) + [('Extension', _('Ext.'))]:
            if style not in FIELD_COLUMNS:
                continue
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            arrow = Gtk.Image()
            arrow.set_visible(False)
            box.append(Gtk.Label(label=title))
            box.append(arrow)
            button = Gtk.Button()
            button.set_child(box)
            button.add_css_class('flat')
            button.add_css_class(f'miaz-header-{style}')
            button.set_tooltip_text(_('Sort by {field}').format(field=title))
            button.connect('clicked', self._on_header_clicked, style)
            header.append(button)
            self._header_buttons[style] = button
            self._header_arrows[style] = arrow
        return header

    def _column(self, style):
        return getattr(self.view, FIELD_COLUMNS[style], None)

    def _on_header_clicked(self, button, style):
        """Sort by this field, or turn it round when it is already the one."""
        column = self._column(style)
        if column is None:
            return
        sorter = self.view.cv.get_sorter()
        order = Gtk.SortType.ASCENDING
        if (sorter is not None
                and sorter.get_primary_sort_column() is column
                and sorter.get_primary_sort_order() == Gtk.SortType.ASCENDING):
            order = Gtk.SortType.DESCENDING
        self.view.cv.sort_by_column(column, order)

    def _sync_header(self):
        """Show which field the documents are sorted by, wherever it was set."""
        sorter = self.view.cv.get_sorter()
        current = None if sorter is None else sorter.get_primary_sort_column()
        ascending = (sorter is not None
                     and sorter.get_primary_sort_order() == Gtk.SortType.ASCENDING)
        for style, button in self._header_buttons.items():
            active = self._column(style) is current
            arrow = self._header_arrows[style]
            arrow.set_visible(active)
            if active:
                arrow.set_from_icon_name(
                    'pan-up-symbolic' if ascending else 'pan-down-symbolic')
            button.remove_css_class('miaz-header-active')
            if active:
                button.add_css_class('miaz-header-active')

    def _on_setup(self, factory, list_item):
        list_item.set_child(FilenameRow())

    def _on_bind(self, factory, list_item):
        list_item.get_child().update(list_item.get_item(), self.app.get_service('util'))

    def _on_activate(self, listview, position):
        item = listview.get_model().get_item(position)
        self.app.get_service('actions').document_display(item.id)

    def _on_right_click(self, gesture, n_press, x, y):
        menu_model = self.app.get_widget('workspace-menu-selection')
        if menu_model is None:
            return
        self._context_popover.set_menu_model(menu_model)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 0, 0
        self._context_popover.set_pointing_to(rect)
        self._context_popover.popup()

    @classmethod
    def _install_css(cls):
        if cls._css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        parts = [
            ".miaz-filename-row { padding: 2px 6px; }",
            ".miaz-filename-row label { color: #2b2b2b; }",
            ".miaz-filenames-header { padding: 4px 6px; }",
            ".miaz-filenames-header button {"
            " padding: 2px 8px;"
            " min-height: 0;"
            " border-radius: 4px;"
            " color: #2b2b2b; }",
            ".miaz-header-active { font-weight: bold; }",
            # The extension is plain on the row, so its button is plain too.
            ".miaz-header-Extension {"
            " background-color: #ffffff;"
            " border: 1px solid #d8d8d8; }",
        ]
        # The header buttons wear the same colours as the fields under them.
        for key, colour in FIELD_COLORS.items():
            parts.append(f".miaz-header-{key} {{ background-color: {colour}; }}")
        css = "".join(parts)
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        cls._css_installed = True
