#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView

class MiAZSelector(Gtk.Box):
    conf_available = None

    def __init__(self, app, edit=True):
        self.app = app
        self.backend = self.app.get_backend()
        self.log = get_logger('MiAZSelector')
        self.dir_conf = self.backend.get_repo_conf_dir()
        super(MiAZSelector, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.factory = self.app.get_factory()

        # Entry and buttons for operations (edit/add/remove)
        self.boxOper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.boxOper.set_vexpand(False)
        boxEntry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        boxEntry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-clear')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self._on_entrysearch_delete)
        self.entry.connect('changed', self._on_filter_selected)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        boxEntry.append(self.entry)
        self.boxOper.append(boxEntry)
        if edit:
            self.boxButtons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
            self.boxButtons.set_hexpand(False)
            self.boxButtons.append(self.factory.create_button('miaz-list-add', '', self._on_item_add, self.config_for))
            self.boxButtons.append(self.factory.create_button('miaz-list-remove', '', self._on_item_remove))
            self.boxOper.append(self.boxButtons)
        self.append(self.boxOper)

        boxViews = self.factory.create_box_horizontal(spacing=0, hexpand=True, vexpand=True)
        boxLeft = self.factory.create_box_vertical(spacing=0, hexpand=True, vexpand=True)
        boxControls = Gtk.CenterBox()
        boxControls.set_orientation(Gtk.Orientation.VERTICAL)
        boxRight = self.factory.create_box_vertical(spacing=0, hexpand=True, vexpand=True)
        boxViews.append(boxLeft)
        boxViews.append(boxControls)
        boxViews.append(boxRight)
        self.append(boxViews)

        # Available
        self.frmViewAv = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup("<b>Available</b>")
        boxLeft.append(title)
        boxLeft.append(self.frmViewAv)

        # Controls
        boxSel = self.factory.create_box_vertical()
        btnAddToUsed = self.factory.create_button('miaz-selector-add', callback=self.action_add)
        btnRemoveFromUsed = self.factory.create_button('miaz-selector-remove', callback=self.action_remove)
        boxSel.append(btnAddToUsed)
        boxSel.append(btnRemoveFromUsed)
        boxControls.set_center_widget(boxSel)

        # Used
        self.frmViewSl = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup("<b>Used</b>")
        boxRight.append(title)
        boxRight.append(self.frmViewSl)
        self._setup_view_finish()

    def add_columnview_available(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        self.frmViewAv.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_title, Gtk.SortType.ASCENDING)

    def add_columnview_used(self, columnview):
        columnview.set_filter(None)
        columnview.column_title.set_expand(True)
        self.frmViewSl.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_title, Gtk.SortType.ASCENDING)

    def _setup_view_finish(self, *args):
        pass

    def update(self):
        self.update_available()
        self.update_used()

    def update_available(self):
        pass

    def update_used(self):
        pass

    def action_add(self, *args):
        changed = False
        items_used = self.config.load(self.config.used)
        for item_available in self.viewAv.get_selected_items():
            self.log.debug("Using %s (%s)", item_available.id, item_available.title)
            items_used[item_available.id] = item_available.title
            changed = True
        if changed:
            self.config.save(filepath=self.config.used, items=items_used)
            self.update_used()

    def action_remove(self, *args):
        changed = False
        items_used = self.config.load(self.config.used)
        items_available = self.config.load(self.config.available)
        for item in self.viewSl.get_selected_items():
            if item.id not in items_available:
                items_available[item.id] = item.title
            del(items_used[item.id])
            changed = True

        if changed:
            self.config.save(filepath=self.config.used, items=items_used)
            self.config.save(filepath=self.config.available, items=items_available)
            self.update_used()
            self.update_available()

    def set_title(self, label:str = 'Selector'):
        self.title.set_markup(label)

