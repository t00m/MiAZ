# File: sidebarstack.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: A list of named pages on the left, the chosen one on the right

from gi.repository import Gdk, Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.services.pluginsystem import PLUGIN_DEFAULT_ICON

# Wide enough for the longest category and vocabulary names without the list
# stealing room from the page beside it.
SIDEBAR_WIDTH = 200


class MiAZSidebarStack(Gtk.Box):
    """A list of pages on the left, the selected one shown on the right.

    Both tabs of the Repository Settings dialog that hold more than one thing
    use this shape: Metadata lists the repository vocabularies, Settings lists
    the categories a plugin can file its options under. They had the same
    problem, a stack of content too long to scan, and one answer between them
    beats two that drift apart.
    """
    __gtype_name__ = 'MiAZSidebarStack'

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.app = app
        self.log = MiAZLog('MiAZ.SidebarStack')
        self._names = []

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class('navigation-sidebar')
        self.listbox.connect('row-selected', self._on_row_selected)
        sidebar = Gtk.ScrolledWindow()
        sidebar.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar.set_child(self.listbox)
        sidebar.set_size_request(SIDEBAR_WIDTH, -1)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        self.append(sidebar)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.append(self.stack)

    def add_page(self, name, title, icon_name, widget):
        """Add one page to the stack and its row to the list.

        `icon_name` can come from any plugin, in or out of tree, and a typo or
        an asset that was never shipped should not put a broken-image glyph in
        the list, so it is checked against the running icon theme first.
        """
        self.stack.add_titled(widget, name, title)
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        icon = Gtk.Image.new_from_icon_name(self._resolve_icon_name(icon_name))
        icon.set_pixel_size(16)
        box.append(icon)
        box.append(Gtk.Label(label=title, xalign=0))
        row.set_child(box)
        row._page_name = name
        self.listbox.append(row)
        self._names.append(name)
        if len(self._names) == 1:
            self.listbox.select_row(row)

    def remove_page(self, name):
        """Take one page away, with its row. Unknown names are ignored."""
        if name not in self._names:
            return
        child = self.stack.get_child_by_name(name)
        if child is not None:
            self.stack.remove(child)
        for row in list(self.listbox):
            if getattr(row, '_page_name', None) == name:
                self.listbox.remove(row)
                break
        self._names.remove(name)
        # Something has to be selected, or the right hand side goes blank with
        # no way back to it from the list.
        if self.listbox.get_selected_row() is None and self._names:
            self.show_page(self._names[0])

    def has_page(self, name) -> bool:
        return name in self._names

    def get_page_names(self) -> list:
        return list(self._names)

    def show_page(self, name):
        for row in self.listbox:
            if getattr(row, '_page_name', None) == name:
                self.listbox.select_row(row)
                return

    def _resolve_icon_name(self, icon_name):
        """`icon_name` if the running icon theme has it, the generic plugin
        icon otherwise.

        Mirrors MiAZPlugin.get_icon_name(), which falls back to
        PLUGIN_DEFAULT_ICON the same way for a plugin's own icon. There is no
        display in a headless context, so nothing to check against there; the
        name is trusted as given.
        """
        display = Gdk.Display.get_default()
        if display is None:
            return icon_name
        icon_theme = Gtk.IconTheme.get_for_display(display)
        if icon_theme.has_icon(icon_name):
            return icon_name
        return PLUGIN_DEFAULT_ICON

    def _on_row_selected(self, listbox, row):
        if row is not None:
            self.stack.set_visible_child_name(row._page_name)
