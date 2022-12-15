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

from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView

class MiAZSelector(Gtk.Box):
    def __init__(self, app, edit=True):
        super(MiAZSelector, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.app = app
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
        self.frmViewAv = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup("Available")
        self.viewAv = MiAZColumnView(self.app)
        # ~ self.frmViewAv.set_child(self.viewAv)
        boxLeft.append(title)
        boxLeft.append(self.frmViewAv)

        # Controls
        box = self.factory.create_box_vertical()
        btnAddSelected = self.factory.create_button('miaz-selector-add', callback=self.action_add)
        btnRemoveSelected = self.factory.create_button('miaz-selector-remove', callback=self.action_remove)
        btnAddAll = self.factory.create_button('miaz-selector-add-all', callback=self.action_add_all)
        btnRemoveAll = self.factory.create_button('miaz-selector-remove-all', callback=self.action_remove_all)
        box.append(btnAddSelected)
        box.append(btnRemoveSelected)
        box.append(btnAddAll)
        box.append(btnRemoveAll)
        boxControls.set_center_widget(box)

        # Selected
        frmView = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup("<b>Selected</b>")
        self.viewSl = MiAZColumnView(self.app)
        frmView.set_child(self.viewSl)
        boxRight.append(title)
        boxRight.append(frmView)

        self._setup_view_finish()

    def _setup_view_finish(self, *args):
        pass

    def update_available(self):
        pass

    def update_selected(self):
        pass

    def action_add(self, *args):
        pass

    def action_remove(self, *args):
        pass

    def action_add_all(self, *args):
        pass

    def action_remove_all(self, *args):
        pass

    def set_title(self, label:str = 'Selector'):
        self.title.set_markup(label)

