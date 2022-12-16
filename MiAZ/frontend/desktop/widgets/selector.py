#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime

import humanize

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
    def __init__(self, app, edit=True):
        self.app = app
        self.backend = self.app.get_backend()
        self.log = get_logger('MiAZSelector')
        self.dir_conf = self.backend.get_repo_conf_dir()
        super(MiAZSelector, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
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

        boxViews = self.factory.create_box_horizontal(hexpand=True, vexpand=True)
        boxLeft = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        boxControls = Gtk.CenterBox()
        boxControls.set_orientation(Gtk.Orientation.VERTICAL)
        boxRight = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        boxViews.append(boxLeft)
        boxViews.append(boxControls)
        boxViews.append(boxRight)
        self.append(boxViews)

        # Available
        self.scrWindowAv = Gtk.ScrolledWindow()
        self.scrWindowAv.set_hexpand(True)
        self.scrWindowAv.set_vexpand(True)
        frmViewAv = Gtk.Frame()
        frmViewAv.set_hexpand(True)
        frmViewAv.set_vexpand(True)
        title = Gtk.Label()
        title.set_markup("<b>Available</b>")
        frmViewAv.set_child(self.scrWindowAv)
        boxLeft.append(title)
        boxLeft.append(frmViewAv)

        # Controls
        boxSel = self.factory.create_box_vertical()
        boxAll = self.factory.create_box_vertical()
        btnAddSelected = self.factory.create_button('miaz-selector-add', callback=self.action_add)
        btnRemoveSelected = self.factory.create_button('miaz-selector-remove', callback=self.action_remove)
        btnAddAll = self.factory.create_button('miaz-selector-add-all', callback=self.action_add_all)
        btnRemoveAll = self.factory.create_button('miaz-selector-remove-all', callback=self.action_remove_all)
        boxSel.append(btnAddSelected)
        boxSel.append(btnRemoveSelected)
        boxAll.append(btnAddAll)
        boxAll.append(btnRemoveAll)
        boxControls.set_center_widget(boxSel)
        # ~ boxControls.set_end_widget(boxAll)

        # Selected
        self.scrWindowSl = Gtk.ScrolledWindow()
        self.scrWindowSl.set_hexpand(True)
        self.scrWindowSl.set_vexpand(True)
        frmViewSl = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup("<b>Selected</b>")
        frmViewSl.set_child(self.scrWindowSl)
        boxRight.append(title)
        boxRight.append(frmViewSl)
        self._setup_view_finish()

    def _setup_view_finish(self, *args):
        pass

    def set_config_file_available(self, path:str):
        self.dir_conf_available = path
        self.log.debug("%s > Available config path: %s", self.config.config_for, path)

    def set_config_file_selected(self, path:str):
        self.dir_conf_selected = path
        self.log.debug("%s > Selected config path: %s", self.config.config_for, path)

    def update(self):
        self.update_available()
        self.update_selected()

    def update_available(self):
        pass

    def update_selected(self):
        pass

    def action_add(self, *args):
        changed = False
        if self.config.config_is is dict:
            items = self.config.load(self.dir_conf_selected)
            for item in self.viewAv.get_selected_items():
                items[item.id] = item.title
                changed = True
        else:
            items = self.config.load(self.dir_conf_selected)
            for item in self.viewAv.get_selected_items():
                if item.id not in items:
                    items.append(item.id)
                changed = True
        if changed:
            self.config.save(items=items)
            self.update_selected()


    def action_remove(self, *args):
        changed = False
        if self.config.config_is is dict:
            items = self.config.load(self.dir_conf_selected)
            for item in self.viewSl.get_selected_items():
                del(items[item.id])
                changed = True
        else:
            items = self.config.load(self.dir_conf_selected)
            print("ITEM LIST? %s" % items)
            for item in self.viewSl.get_selected_items():
                items.remove(item.id)
                changed = True
        if changed:
            self.config.save(items=items)
            self.update_selected()

    def action_add_all(self, *args):
        changed = False
        items_available = self.config.load(self.config.config_global)
        items_selected = items_available.copy()
        self.config.save(items_selected)
        self.update_selected()

    def action_remove_all(self, *args):
        if self.config.config_is is dict:
            items = {}
        else:
            items = []
        self.config.save(items=items)
        self.update_selected()

    def set_title(self, label:str = 'Selector'):
        self.title.set_markup(label)

