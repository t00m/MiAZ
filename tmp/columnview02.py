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
    """Item holding the row info"""
    __gtype_name__ = 'Row'

    def __init__(self, filepath, active=False):
        super().__init__()

        self._filepath = filepath
        self._active = active

    @GObject.Property
    def filepath(self):
        return self._filepath

    @GObject.Property
    def basename(self):
        return os.path.basename(self._filepath)

    @GObject.Property(type=bool, default=False)
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        self._active = active


class RowLabel(Gtk.Box):
    """Row Label Widget"""
    __gtype_name__ = 'RowLabel'

    def __init__(self):
        super(RowLabel, self).__init__()
        label = Gtk.Label()
        self.append(label)

class RowIcon(Gtk.Box):
    """Row Icon Widget"""
    __gtype_name__ = 'RowIcon'

    def __init__(self):
        super(RowIcon, self).__init__()
        icon = Gtk.Image()
        self.append(icon)

class RowCheck(Gtk.Box):
    """Row Check Widget"""
    __gtype_name__ = 'RowCheck'

    def __init__(self):
        super(RowCheck, self).__init__()
        button = Gtk.CheckButton()
        self.append(button)

class MyColumnView(Gtk.Box):
    __gtype_name__ = 'MyColumnView'

    def __init__(self):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)

        self.displayed = 0
        self.total = 0

        # model
        self.store = Gio.ListStore(item_type=Row)
        self.sort_model  = Gtk.SortListModel(model=self.store)
        self.sorter = Gtk.CustomSorter.new(sort_func=self._sort_func)
        self.sort_model.set_sorter(self.sorter)
        self.filter_model = Gtk.FilterListModel(model=self.sort_model)
        self.filter = Gtk.CustomFilter.new(self._do_filter_view, self.filter_model)
        self.model = self.filter_model
        selection = Gtk.SingleSelection.new(self.model)

        # Set up the factories
        factory_label = Gtk.SignalListItemFactory()
        factory_label.connect("setup", self._on_factory_setup_label)
        factory_label.connect("bind", self._on_factory_bind_label)
        factory_check = Gtk.SignalListItemFactory()
        factory_check.connect("setup", self._on_factory_setup_check)
        factory_check.connect("bind", self._on_factory_bind_check)

        # Setup ColumnView Widget
        self.cv = Gtk.ColumnView(model=selection)
        self.cv.set_show_column_separators(True)
        self.cv.set_show_row_separators(True)
        self.cv.set_single_click_activate(True)
        scrwin.set_child(self.cv)

        # Setup columnview columns
        column_label = Gtk.ColumnViewColumn.new("File path", factory_label)
        column_label.set_sorter(self.sorter)
        column_label.set_expand(True)
        column_check = Gtk.ColumnViewColumn.new("check", factory_check)
        self.cv.append_column(column_label)
        self.cv.append_column(column_check)
        self.cv.sort_by_column(column_label, Gtk.SortType.ASCENDING)
        self.cv.connect("activate", self._on_selected_item_notify)

        box = Gtk.Box(spacing=12, orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        box.props.margin_start = 12
        box.props.margin_end = 12
        box.props.margin_top = 6
        box.props.margin_bottom = 6
        self.lblDocs = Gtk.Label()
        self.etyFilter = Gtk.Entry(placeholder_text="Type something to filter the view")
        self.etyFilter.connect('changed', self._on_filter_selected)
        box.append(self.lblDocs)
        box.append(self.etyFilter)
        box.append(scrwin)
        self.append(box)

        self.filter_model.set_filter(self.filter)

    def _on_filter_selected(self, *args):
        self.displayed = 0
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.lblDocs.set_text("Documents: %d/%d" % (self.displayed, self.total))

    def _do_filter_view(self, item, filter_list_model):
        must_filter = False
        text = self.etyFilter.get_text().upper()
        if text in item.filepath.upper():
            self.displayed += 1
            must_filter = True
        return must_filter

    def _sort_func(self, item1, item2, data):
        if item1.filepath.upper() > item2.filepath.upper():
            return Gtk.Ordering.LARGER
        elif item1.filepath.upper() < item2.filepath.upper():
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL

    def _on_factory_setup_label(self, factory, list_item):
        box = RowLabel()
        list_item.set_child(box)

    def _on_factory_bind_label(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_last_child()
        label.set_text(item.basename)

    def _on_factory_setup_check(self, factory, list_item):
        box = RowCheck()
        list_item.set_child(box)
        button = box.get_first_child()

    def _on_factory_bind_check(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        button = box.get_first_child()
        button.set_active(item.active)
        button.connect('toggled', self._on_button_toggled)

    def _on_selected_item_notify(self, colview, pos):
        model = colview.get_model()
        item = model.get_item(pos)
        # ~ print(item.filepath)

    def _on_button_toggled(self, button):
        selection = self.cv.get_model()
        selected = selection.get_selection()
        pos = selected.get_nth(0)
        cvitem = selection.get_item(pos)
        filepath = cvitem.filepath
        active = button.get_active()
        cvitem.active = active

    def update(self, documents):
        self.store.remove_all()
        for filepath in documents:
            self.store.append(Row(filepath=filepath))


class ExampleWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="GTK4 Listview/ColumnView")

        documents = get_files(sys.argv[1])
        self.total = len(documents)
        self.toggled = set()

        # Populate the model

        cv = MyColumnView()
        cv.update(documents)
        self.set_child(cv)


        # ~ print("Item %s set to: %s" % (item.filepath, item.active))
        # ~ for item in model:
            # ~ if item.active:
                # ~ print("Active: %s" % item.filepath)


class ExampleApp(Adw.Application):
    def __init__(self):
        super().__init__()
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = ExampleWindow(self)
            self.window.set_default_size(1024, 728)
        self.window.present()


app = ExampleApp()
app.run([])
