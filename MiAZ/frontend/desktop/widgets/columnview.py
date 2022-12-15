#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.backend.env import ENV
from MiAZ.backend.models import MiAZItem
from MiAZ.backend.util import json_load

class RowId(Gtk.Box):
    """Row Id Widget"""
    __gtype_name__ = 'RowId'

    def __init__(self):
        super(RowId, self).__init__()
        label = Gtk.Label()
        self.append(label)

class RowTitle(Gtk.Box):
    """Row Title Widget"""
    __gtype_name__ = 'RowTitle'

    def __init__(self):
        super(RowTitle, self).__init__()
        label = Gtk.Label()
        self.append(label)

class RowSubtitle(Gtk.Box):
    """Row Subtitle Widget"""
    __gtype_name__ = 'RowSubtitle'

    def __init__(self):
        super(RowSubtitle, self).__init__()
        label = Gtk.Label()
        self.append(label)

class RowIcon(Gtk.Box):
    """Row Icon Widget"""
    __gtype_name__ = 'RowIcon'

    def __init__(self):
        super(RowIcon, self).__init__()
        icon = Gtk.Image()
        self.append(icon)

class RowActive(Gtk.Box):
    """Row Active Widget"""
    __gtype_name__ = 'RowActive'

    def __init__(self):
        super(RowActive, self).__init__()
        button = Gtk.CheckButton()
        self.append(button)


class MiAZColumnView(Gtk.Box):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnView'

    def __init__(self, app, item_type=MiAZItem):
        super(MiAZColumnView, self).__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True, vexpand=True)
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
        self.icman = self.app.get_icman()
        selected_items = []

        scrwin = Gtk.ScrolledWindow()
        scrwin.set_hexpand(True)
        scrwin.set_vexpand(True)

        # Set up the factories
        factory_id = Gtk.SignalListItemFactory()
        factory_id.connect("setup", self._on_factory_setup_id)
        factory_id.connect("bind", self._on_factory_bind_id)
        factory_title = Gtk.SignalListItemFactory()
        factory_title.connect("setup", self._on_factory_setup_title)
        factory_title.connect("bind", self._on_factory_bind_title)

        # Setup ColumnView Widget
        self.cv = Gtk.ColumnView()
        self.cv.get_style_context().add_class(class_name='monospace')
        self.cv.set_show_column_separators(True)
        self.cv.set_show_row_separators(True)
        # ~ self.cv.set_single_click_activate(True)
        scrwin.set_child(self.cv)

        # Sorters
        self.prop_id_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='id')
        self.prop_title_sorter = Gtk.CustomSorter.new(sort_func=self._on_sort_string_func, user_data='title')

        # Setup columnview columns
        self.column_id = Gtk.ColumnViewColumn.new("Id", factory_id)
        self.column_id.set_sorter(self.prop_id_sorter)
        self.column_title = Gtk.ColumnViewColumn.new("Title", factory_title)
        self.column_title.set_sorter(self.prop_title_sorter)

        # Setup models
        cv_sorter = self.cv.get_sorter()
        self.store = Gio.ListStore(item_type=item_type)
        self.sort_model  = Gtk.SortListModel(model=self.store, sorter=cv_sorter)
        self.filter_model = Gtk.FilterListModel(model=self.sort_model)
        self.selection = Gtk.MultiSelection.new(self.filter_model)
        self.cv.set_model(self.selection)
        self.append(scrwin)

        # Connect signals
        self.cv.connect("activate", self._on_selected_item_notify)
        self.selection.connect('selection-changed', self._on_selection_changed)

    def get_columnview(self):
        return self.cv

    def get_filter(self):
        return self.filter

    def get_model_filter(self):
        return self.filter_model

    def get_selection(self):
        return self.selection

    def get_item(self):
        selection = self.get_selection()
        selected = selection.get_selection()
        model = self.get_model_filter()
        pos = selected.get_nth(0)
        return model.get_item(pos)

    def get_selected_items(self):
        items = []
        return self.selected_items

    def select_first_item(self):
        pass
        # ~ self.selection.set_selected(0)

    def set_filter(self, filter_func):
        self.filter = Gtk.CustomFilter.new(filter_func, self.filter_model)
        self.filter_model.set_filter(self.filter)
        return self.filter

    def refilter(self):
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)

    def update(self, items):
        repocnf = self.backend.get_repo_source_config_file()
        self.repodct = json_load(repocnf)
        # ~ self.repodct = repodct
        self.store.remove_all()
        for item in items:
            # item =~ Subclass of MiAZModel(id='xxx', title='xxx', ...)
            self.store.append(item)

    def _on_selection_changed(self, selection, position, n_items):
        self.selected_items = []
        model = selection.get_model()
        bitset = selection.get_selection()
        for index in range(bitset.get_size()):
            pos = bitset.get_nth(index)
            item = model.get_item(pos)
            self.selected_items.append(item)

    def _on_factory_setup_id(self, factory, list_item):
        box = RowId()
        list_item.set_child(box)

    def _on_factory_bind_id(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_text(item.id)

    def _on_factory_setup_title(self, factory, list_item):
        box = RowId()
        list_item.set_child(box)

    def _on_factory_bind_title(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.title)

    def _on_button_toggled(self, button):
        selection = self.cv.get_model()
        selected = selection.get_selection()
        pos = selected.get_nth(0)
        item = selection.get_item(pos)
        active = button.get_active()
        item.active = active

    def _on_filter_view(self, item, filter_list_model):
        must_filter = False
        text = self.etyFilter.get_text().upper()
        if text in item.filepath.upper():
            self.displayed += 1
            must_filter = True
        return must_filter

    def _on_selected_item_notify(self, colview, pos):
        model = colview.get_model()
        item = model.get_item(pos)
        print(item.id)

    def _on_sort_string_func(self, item1, item2, prop):
        # ~ print("%s %s %s" % (prop, eval("item1.%s.upper()" % prop), eval("item2.%s.upper()" % prop)))
        if eval("item1.%s.upper()" % prop) > eval("item2.%s.upper()" % prop):
            return Gtk.Ordering.LARGER
        elif eval("item1.%s.upper()" % prop) < eval("item2.%s.upper()" % prop):
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL
