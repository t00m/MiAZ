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


class MyCustomRow(Gtk.Box):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MyCustomRow'

    def __init__(self):
        super(MyCustomRow, self).__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        self.set_hexpand(True)
        icon = Gtk.Label()
        label = Gtk.Label()
        self.append(icon)
        self.append(label)

class ExampleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="GTK4 Listview/ColumnView")

        documents = get_files(sys.argv[1])

        # Populate the model
        model = Gio.ListStore(item_type=Row)
        for filepath in documents:
            model.append(Row(filepath=filepath))

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        # Setup ColumnView Widget
        selection = Gtk.SingleSelection.new(model)
        selection.set_autoselect(True)
        self.cv = Gtk.ColumnView(model=selection)
        self.cv.set_show_column_separators(True)
        self.cv.set_show_row_separators(True)

        column = Gtk.ColumnViewColumn.new("File path", factory)
        self.cv.append_column(column)
        self.cv.sort_by_column(column, Gtk.SortType.ASCENDING)
        self.cv.connect("activate", self._on_selected_item_notify)


        box = Gtk.Box(spacing=12, orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        box.props.margin_start = 12
        box.props.margin_end = 12
        box.props.margin_top = 6
        box.props.margin_bottom = 6
        box.append(Gtk.Label(label="Documents: %d" % len(documents)))
        # ~ box.append(self.cv)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)
        scrwin.set_child(self.cv)
        box.append(scrwin)
        self.set_child(box)

    # Set up the child of the list item; this can be an arbitrarily
    # complex widget but we use a simple label now
    def _on_factory_setup(self, factory, list_item):
        box = MyCustomRow()
        list_item.set_child(box)

    # Bind the item in the model to the row widget; again, since
    # the object in the model can contain multiple properties, and
    # the list item can contain any arbitrarily complex widget, we
    # can have very complex rows instead of the simple cell renderer
    # layouts in GtkComboBox
    def _on_factory_bind(self, factory, list_item):
        box = list_item.get_child()
        icon = box.get_first_child()
        label = box.get_last_child()

        row = list_item.get_item()
        mimetype, val = Gio.content_type_guess('filename=%s' % row.filepath)
        gicon = Gio.content_type_get_icon(mimetype)
        # ~ icon = Gtk.Image.new_from_gicon(gicon)
        icon.set_text(str(datetime.now()))
        label.set_text(row.filepath)
        print("%s > %s > %s" % (datetime.now(), icon, label))


    # The notify signal is fired when the selection changes
    def _on_selected_item_notify(self, *args):
        # ~ row = view.get_selected_item()
        print(args)


class ExampleApp(Adw.Application):
    def __init__(self):
        super().__init__()
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = ExampleWindow(self)
            self.window.set_default_size(600, 480)
        self.window.present()


app = ExampleApp()
app.run([])
