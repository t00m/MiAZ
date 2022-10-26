#!/usr/bin/env python
# -*- coding: utf-8 -*-
# https://discourse.gnome.org/t/migrate-from-comboboxtext-to-comborow-dropdown/10565/2

import os
import sys
import glob
import json
from datetime import datetime

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw, Gio, GObject, Gtk, Pango
from gi.repository.GdkPixbuf import Pixbuf

def get_files(root_dir: str) -> []:
    """Get documents from a given directory recursively
    Avoid hidden documents and documents from hidden directories.
    """
    documents = set()
    hidden = set()
    subdirs = set()

    subdirs.add(os.path.abspath(root_dir))
    for root, dirs, files in os.walk(os.path.abspath(root_dir)):
        thisdir = os.path.abspath(root)
        if os.path.basename(thisdir).startswith('.'):
            hidden.add(thisdir)
        else:
            found = False
            for hidden_dir in hidden:
                if hidden_dir in thisdir:
                    found = True
            if not found:
                subdirs.add(thisdir)
    for directory in subdirs:
        files = glob.glob(os.path.join(directory, '*'))
        for thisfile in files:
            if not os.path.isdir(thisfile):
                if not os.path.basename(thisfile).startswith('.'):
                    documents.add(thisfile)
    return documents

class Row(GObject.Object):
    __gtype_name__ = 'Row'

    def __init__(self, filepath):
        super().__init__()

        self._filepath = filepath


    @GObject.Property
    def filepath(self):
        return self._filepath


class MiAZFlowBoxRow(Gtk.Box):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZFlowBoxRow'

    def __init__(self):
        super(MiAZFlowBoxRow, self).__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        self.set_hexpand(True)
        label = Gtk.Label()
        self.append(label)

class ExampleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="DropDown")

        documents = get_files(sys.argv[1])

        # Populate the model
        self.model = Gio.ListStore(item_type=Row)
        for filepath in documents:
            self.model.append(Row(filepath=filepath))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.dd = Gtk.ListView(model=Gtk.SingleSelection.new(self.model), factory=factory, hexpand=True)
        # ~ self.dd.connect("notify::selected-item", self._on_selected_item_notify)

        box = Gtk.Box(spacing=12, orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        box.props.margin_start = 12
        box.props.margin_end = 12
        box.props.margin_top = 6
        box.props.margin_bottom = 6
        box.append(Gtk.Label(label="Documents:"))
        box.append(self.dd)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_child(box)
        self.set_child(scrwin)

    # Set up the child of the list item; this can be an arbitrarily
    # complex widget but we use a simple label now
    def _on_factory_setup(self, factory, list_item):
        box = MiAZFlowBoxRow()
        list_item.set_child(box)

    # Bind the item in the model to the row widget; again, since
    # the object in the model can contain multiple properties, and
    # the list item can contain any arbitrarily complex widget, we
    # can have very complex rows instead of the simple cell renderer
    # layouts in GtkComboBox
    def _on_factory_bind(self, factory, list_item):
        # ~ label = list_item.get_child()
        # ~ country = list_item.get_item()
        # ~ label.set_text(country.country_name)
        box = list_item.get_child()
        label = box.get_first_child()

        row = list_item.get_item()
        label.set_text(row.filepath)


    # The notify signal is fired when the selection changes
    def _on_selected_item_notify(self, dropdown, _):
        country = dropdown.get_selected_item()
        print(country)


class ExampleApp(Adw.Application):
    def __init__(self):
        super().__init__()
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = ExampleWindow(self)
        self.window.present()


app = ExampleApp()
app.run([])
