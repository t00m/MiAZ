#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: selector.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom widget to manage available/used config items
"""

import os
from datetime import datetime
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Project, Repository
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog


class MiAZSelector(Gtk.Box):
    def __init__(self, app, edit=True):
        self.app = app
        self.edit = edit
        self.backend = self.app.get_service('backend')
        self.util = self.app.get_service('util')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repository')
        self.log = get_logger('MiAZ.Selector')
        super(MiAZSelector, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)

        # Entry and buttons for operations (edit/add/remove)
        self.boxOper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.boxOper.set_margin_top(24)
        self.boxOper.set_margin_bottom(6)
        self.boxOper.set_margin_start(6)
        self.boxOper.set_margin_end(0)
        self.boxOper.set_hexpand(True)
        self.boxOper.set_vexpand(False)
        boxEntry = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
        boxEntry.set_hexpand(False)
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class(class_name='caption')
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-clear')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self._on_entrysearch_delete)
        self.entry.connect('changed', self._on_filter_selected)
        self.entry.connect('activate', self.on_item_available_add, self.config_for)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        self.entry.set_placeholder_text('Type here for filtering')
        boxEntry.append(self.entry)
        self.boxOper.append(boxEntry)
        if edit:
            self.boxButtons = Gtk.Box(spacing=0, orientation=Gtk.Orientation.HORIZONTAL)
            self.boxButtons.get_style_context().add_class(class_name='linked')
            self.boxButtons.set_hexpand(True)
            self.boxButtons.append(self.factory.create_button(icon_name='miaz-list-add', title='', callback=self.on_item_available_add, data=self.config_for))
            self.boxButtons.append(self.factory.create_button(icon_name='miaz-list-remove', title='', callback=self._on_item_available_remove))
            # ~ self.boxButtons.append(self.factory.create_button(icon_name='miaz-import-config', tooltip='Import configuration', callback=self._on_config_import))
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
        title.set_markup(_('<b>Available</b>'))
        boxLeft.append(title)
        boxLeft.append(self.frmViewAv)

        # Controls
        boxSel = self.factory.create_box_vertical()
        btnAddToUsed = self.factory.create_button('miaz-selector-add', callback=self._on_item_used_add)
        btnRemoveFromUsed = self.factory.create_button('miaz-selector-remove', callback=self._on_item_used_remove)
        boxSel.append(btnAddToUsed)
        boxSel.append(btnRemoveFromUsed)
        boxControls.set_center_widget(boxSel)

        # Used
        self.frmViewSl = Gtk.Frame()
        title = Gtk.Label()
        title.set_markup(_('<b>Used</b>'))
        boxRight.append(title)
        boxRight.append(self.frmViewSl)
        self._setup_view_finish()

    def add_columnview_available(self, columnview):
        columnview.set_filter(self._do_filter_view)
        columnview.column_title.set_expand(True)
        columnview.cv.connect("activate", self._on_selected_item_available_notify)
        self.frmViewAv.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_title, Gtk.SortType.ASCENDING)
        columnview.cv.get_style_context().add_class(class_name='caption')

    def add_columnview_used(self, columnview):
        columnview.set_filter(None)
        columnview.column_title.set_expand(True)
        self.frmViewSl.set_child(columnview)
        columnview.cv.sort_by_column(columnview.column_title, Gtk.SortType.ASCENDING)
        columnview.cv.get_style_context().add_class(class_name='caption')

    def _setup_view_finish(self, *args):
        pass

    def update(self, *args):
        self._update_view_available()
        self._update_view_used()

    def _on_item_used_add(self, *args):
        changed = False
        items_used = self.config.load_used()
        for item_available in self.viewAv.get_selected_items():
            items_used[item_available.id] = item_available.title
            self.log.debug("Using %s (%s)", item_available.id, item_available.title)
            changed = True
        if changed:
            self.config.save_used(items=items_used)
            self._update_view_used()

    def _on_item_used_remove(self, *args):
        value_used = False
        changed = False
        items_used = self.config.load_used()
        items_available = self.config.load_available()
        for item_used in self.viewSl.get_selected_items():
            if item_used.id not in items_available:
                items_available[item_used.id] = item_used.title
            if self.config.model == Repository:
                value_used = False
            elif self.config.model == Project:
                projects = self.app.get_service('Projects')
                docs = projects.docs_in_project(item_used.id)
                value_used = len(docs) > 0
            else:
                value_used = self.util.field_used(self.repository.docs, self.config.model, item_used.id)

            if not value_used:
                del(items_used[item_used.id])
                changed = True
                text = _('Removed %s (%s) from used') % (item_used.id, item_used.title)
                self.log.debug(text)
            else:
                dtype = "warning"
                text = _('%s %s is still being used by some docs') % (self.config.model.__title__, item_used.id)
                window = self.app.get_widget('window')
                dtype = 'error'
                title = "Item can't be removed"
                dialog = CustomDialog(app=self.app, parent=window, use_header_bar=True, dtype=dtype, title=title, text=text)
                dialog.set_modal(True)
                dialog.show()
        if changed:
            self.config.save_used(items=items_used)
            self.config.save_available(items=items_available)
            self._update_view_used()
            self._update_view_available()

    def on_item_available_add(self, *args):
        if self.edit:
            dialog = MiAZDialogAdd(self.app, self.get_root(), _('%s: add a new item') % self.config.config_for, _('Name'), _('Description'))
            search_term = self.entry.get_text()
            dialog.set_value1(search_term)
            dialog.connect('response', self._on_response_item_available_add)
            dialog.show()

    def _on_response_item_available_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0:
                self.config.add_available(key.upper(), value)
                self.log.debug("%s (%s) added to list of available items", key, value)
                self.update()
        dialog.destroy()

    def _on_item_available_rename(self, item):
        dialog = MiAZDialogAdd(self.app, self.get_root(), _('%s: rename item') % self.config.config_for, _('Name'), _('Description'))
        dialog.set_value1(item.id)
        dialog.set_value2(item.title)
        dialog.connect('response', self._on_response_item_available_rename, item)
        dialog.show()

    def _on_response_item_available_rename(self, dialog, response, item):
        if response == Gtk.ResponseType.ACCEPT:
            oldkey = item.id
            newkey = dialog.get_value1()
            newval = dialog.get_value2()
            self.log.debug("Renaming %s by %s (%s)", oldkey, newkey, newval)
            if len(newkey) > 0:
                # Rename items used
                items_used = self.config.load_used()
                if oldkey in items_used:
                    self.config.remove_used(oldkey)
                    self.config.add_used(newkey, newval)
                    self.log.debug("Renamed items_used")
                # Rename items available
                items_available = self.config.load_available()
                self.config.remove_available(oldkey)
                self.config.add_available(newkey, newval)
                self.log.debug("%s renamed to %s (%s) in the list of available items", oldkey, newkey, newval)
                self.update()
        dialog.destroy()

    def _on_item_available_remove(self, *args):
        keys = []
        for item_available in self.viewAv.get_selected_items():
            keys.append(item_available.id)
        self.config.remove_available_batch(keys)
        # ~ # FIXME: self.config.remove_used(item.id)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def _on_selected_item_available_notify(self, colview, pos):
        model = colview.get_model()
        item = model.get_item(pos)
        self._on_item_available_rename(item)

    def _update_view_available(self):
        items_available = []
        item_type = self.config.model
        items = self.config.load_available()
        for key in items:
            items_available.append(item_type(id=key, title=items[key]))
        self.viewAv.update(items_available)

    def _update_view_used(self):
        items_used = []
        item_type = self.config.model
        items = self.config.load_used()
        for key in items:
            items_used.append(item_type(id=key, title=items[key]))
        self.viewSl.update(items_used)

    def _on_filter_selected(self, *args):
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s-%s" % (item.id, item.title)
        if chunk in string.upper():
            return True
        return False

    def _on_entrysearch_delete(self, *args):
        self.entry.set_text("")


    def _on_config_import(self, *args):
        pass

    def get_search_entry(self):
        return self.entry
