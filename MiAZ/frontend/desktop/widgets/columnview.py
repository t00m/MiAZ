#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: columnview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom Gtk.Columnview widget for displaying info
"""

import os
import sys
from abc import abstractmethod
from datetime import datetime
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.backend.log import get_logger
from MiAZ.backend.env import ENV
from MiAZ.backend.models import MiAZItem


class ColLabel(Gtk.Box):
    """Row Id Widget"""
    __gtype_name__ = 'ColLabel'

    def __init__(self):
        super(ColLabel, self).__init__()
        label = Gtk.Label()
        self.append(label)

class ColIcon(Gtk.Box):
    """Row Icon Widget"""
    __gtype_name__ = 'ColIcon'

    def __init__(self):
        super(ColIcon, self).__init__()
        icon = Gtk.Image()
        self.append(icon)

class ColButton(Gtk.Box):
    """Row Icon Widget"""
    __gtype_name__ = 'ColButton'

    def __init__(self):
        super(ColButton, self).__init__()
        button = Gtk.Button()
        button.get_style_context().add_class(class_name='flat')
        self.append(button)

class ColMenuButton(Gtk.Box):
    """Row Icon Widget"""
    __gtype_name__ = 'ColMenuButton'

    def __init__(self):
        super(ColMenuButton, self).__init__()
        popover = Gtk.Popover()
        button = Gtk.MenuButton()
        button.set_popover(popover)
        button.get_style_context().add_class(class_name='flat')
        self.append(button)

class ColCheck(Gtk.Box):
    """Row Id Widget"""
    __gtype_name__ = 'ColCheck'

    def __init__(self):
        super(ColLabel, self).__init__()
        check = Gtk.CheckButton()
        self.append(check)

class MiAZColumnView(Gtk.Box):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnView'

    def __init__(self, app, item_type=MiAZItem):
        super(MiAZColumnView, self).__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True, vexpand=True)
        self.app = app
        self.item_type = item_type
        self.log = get_logger('MiAZColumnView')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.selected_items = []

        self.viewport = Gtk.Viewport()
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)

        # Set up the factories
        factory_id = Gtk.SignalListItemFactory()
        factory_id.connect("setup", self._on_factory_setup_id)
        factory_id.connect("bind", self._on_factory_bind_id)
        factory_title = Gtk.SignalListItemFactory()
        factory_title.connect("setup", self._on_factory_setup_title)
        factory_title.connect("bind", self._on_factory_bind_title)

        # Setup ColumnView Widget
        self.cv = Gtk.ColumnView()
        # ~ self.cv.get_style_context().add_class(class_name='monospace')
        self.cv.set_show_column_separators(False)
        self.cv.set_show_row_separators(False)
        # ~ self.cv.set_single_click_activate(True)
        self.scrwin.set_child(self.cv)

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
        self.viewport.set_child(self.scrwin)
        self.append(self.viewport)

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
        return self.selected_items

    def select_first_item(self):
        # ~ self.viewport.set_scroll_to_focus(False)
        # FIXME: code works (it selects the item) but not as expected
        # it is not displayed (Grabbing focus? How?)
        selection = self.get_selection()
        model = selection.get_model()
        pos = len(model)
        if pos > 0:
            selection.select_item(pos - 1, True) # Last item
            selection.select_item(0, True) # First item
        # ~ self.viewport.set_scroll_to_focus(True)
        # In any case, the scrollbar doesn't move

    def scroll_begin(self, *args):
        self.log.debug(args)

    def set_filter(self, filter_func):
        self.filter = Gtk.CustomFilter.new(filter_func, self.filter_model)
        self.filter_model.set_filter(self.filter)
        return self.filter

    def refilter(self):
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)

    # ~ def update(self, items):
        # ~ self.selected_items = []
        # ~ self.store.remove_all()
        # ~ ds = datetime.now()
        # ~ for item in items:
            # ~ # item =~ Subclass of MiAZModel(id='xxx', title='xxx', ...)
            # ~ self.store.append(item)
        # ~ self.select_first_item()
        # ~ de = datetime.now()
        # ~ dt = de - ds
        # ~ self.log.debug("Columnview for %s updated (%s)", self.item_type.__title__, dt)

    def update(self, items):
        self.selected_items = []
        ds = datetime.now()
        self.store.remove_all()
        self.store.splice(0, 0, items)
        de = datetime.now()
        dt = de - ds
        self.log.debug("View for %s updated with %d items in %s", self.item_type.__title__, len(items), dt)

    def _on_selection_changed(self, selection, position, n_items):
        self.selected_items = []
        model = selection.get_model()
        bitset = selection.get_selection()
        for index in range(bitset.get_size()):
            pos = bitset.get_nth(index)
            item = model.get_item(pos)
            self.selected_items.append(item)

    def _on_factory_setup_id(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_id(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.id)
        label.set_ellipsize(True)
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

    def _on_factory_setup_title(self, factory, list_item):
        box = ColLabel()
        list_item.set_child(box)

    def _on_factory_bind_title(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.title)
        label.set_ellipsize(True)
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

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
        self.log.debug(item.id)

    def _on_sort_string_func(self, item1, item2, prop):
        if eval("item1.%s.upper()" % prop) > eval("item2.%s.upper()" % prop):
            return Gtk.Ordering.LARGER
        elif eval("item1.%s.upper()" % prop) < eval("item2.%s.upper()" % prop):
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL
