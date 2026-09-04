# File: metadatapage.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The Metadata tab of the Repository Settings dialog

from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog


class MiAZMetadataPage(Gtk.Box):
    """The repository vocabularies, one list on the left and one view shown.

    They used to be five tabs across the top of the dialog, which left no room
    for a sixth: the plugins that own a vocabulary of their own had to put it
    behind a button somewhere else. A list takes as many as it is given.
    """
    __gtype_name__ = 'MiAZMetadataPage'

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.app = app
        self.log = MiAZLog('MiAZ.MetadataPage')
        self._names = []

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class('navigation-sidebar')
        self.listbox.connect('row-selected', self._on_row_selected)
        sidebar = Gtk.ScrolledWindow()
        sidebar.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar.set_child(self.listbox)
        sidebar.set_size_request(200, -1)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        self.append(sidebar)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.append(self.stack)
        self.app.add_widget('repository-settings-page-metadata', self)

    def add_view(self, name, title, icon_name, widget):
        """Add one vocabulary to the list and its view to the stack."""
        self.stack.add_titled(widget, name, title)
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        box.append(icon)
        box.append(Gtk.Label(label=title, xalign=0))
        row.set_child(box)
        row._view_name = name
        self.listbox.append(row)
        self._names.append(name)
        if len(self._names) == 1:
            self.listbox.select_row(row)

    def add_plugin_views(self):
        """Add the vocabularies plugins own, after the built-in ones."""
        registry = self.app.get_service('plugin-system').settings
        for _owner, name, title, icon_name, factory in registry.views():
            if name in self._names:
                continue
            try:
                widget = factory()
            except Exception as error:
                self.log.error(f"Metadata view {name}: {error}")
                continue
            if widget is not None:
                self.add_view(name, title, icon_name, widget)

    def get_view_names(self) -> list:
        return list(self._names)

    def show_view(self, name):
        for row in self.listbox:
            if getattr(row, '_view_name', None) == name:
                self.listbox.select_row(row)
                return

    def _on_row_selected(self, listbox, row):
        if row is not None:
            self.stack.set_visible_child_name(row._view_name)
