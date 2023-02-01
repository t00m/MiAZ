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
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd

class MiAZSelector(Gtk.Box):
    def __init__(self, app, edit=True):
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.log = get_logger('MiAZSelector')
        super(MiAZSelector, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)


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

    # ~ def set_title(self, label:str = 'Selector'):
        # ~ self.title.set_markup(label)

    def _on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), '%s: add a new item' % self.config.config_for, 'Name', 'Description')
        etyValue1 = dialog.get_value1_widget()
        search_term = self.entry.get_text()
        etyValue1.set_text(search_term)
        dialog.connect('response', self._on_response_item_add)
        dialog.show()

    def _on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0:
                items = self.config.load(self.config.available)
                if not key.upper() in items:
                    items[key.upper()] = value
                    self.log.debug("%s (%s) added to list of available items", key.upper(), value)
                    self.config.save(filepath=self.config.available, items=items)
                    self.update()
        dialog.destroy()

    def _on_item_rename(self, *args):
        return

    def _on_item_remove(self, *args):
        item = self.viewAv.get_item()
        self.log.debug("%s > %s > %s", item, item.id, item.title)
        if item is None:
            return
        self.config.remove(item.id)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def update_available(self):
        items_available = []
        item_type = self.config.model
        items = self.config.load(self.config.available)
        for key in items:
            items_available.append(item_type(id=key, title=items[key]))
        self.viewAv.update(items_available)

    def update_used(self):
        items_used = []
        item_type = self.config.model
        items = self.config.load(self.config.used)
        for key in items:
            items_used.append(item_type(id=key, title=items[key]))
        self.viewSl.update(items_used)

    def _on_filter_selected(self, *args):
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s%s" % (item.id, item.title)
        if chunk in string.upper():
            return True
        return False

    def on_key_released(self, widget, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        self.log.debug("Key: %s", keyname)

    def _on_entrysearch_delete(self, *args):
        self.entry.set_text("")
