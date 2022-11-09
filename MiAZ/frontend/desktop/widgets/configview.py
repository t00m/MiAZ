#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod
import json

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import File, Collection, Person, Country, Purpose, Concept
from MiAZ.backend.config import MiAZConfigSettingsCollections
from MiAZ.backend.config import MiAZConfigSettingsOrganizations
from MiAZ.backend.config import MiAZConfigSettingsCountries
from MiAZ.backend.config import MiAZConfigSettingsExtensions
from MiAZ.backend.config import MiAZConfigSettingsPurposes
from MiAZ.frontend.desktop.widgets.widget import MiAZWidget
# ~ from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd



class MiAZConfigView(MiAZWidget, Gtk.Box):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZConfigView'
    current = None
    config_local = None
    config_global = None
    config_for = None
    search_term = ''

    def __init__(self, app, config_for):
        super().__init__(app, __class__.__name__)
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.backend = app.get_backend()
        self.config_for = config_for
        self.factory = self.app.get_factory()
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_start(margin=12)

        # Entry and buttons for collection operations (edit/add/remove)
        self.box_oper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_oper.set_vexpand(False)
        box_entry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'miaz-entry-clear')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.connect('icon-press', self.on_entrysearch_delete)
        self.entry.connect('changed', self._on_filter_selected)
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        box_entry.append(self.entry)
        self.box_oper.append(box_entry)
        self.box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        self.box_buttons.set_hexpand(False)
        # ~ self.box_buttons.append(self.factory.create_button('miaz-edit', '', self.on_item_rename))
        # ~ self.box_buttons.append(Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL))
        self.box_buttons.append(self.factory.create_button('miaz-list-add', '', self.on_item_add, self.config_for))
        self.box_buttons.append(self.factory.create_button('miaz-list-remove', '', self.on_item_remove))
        self.box_oper.append(self.box_buttons)
        self.append(self.box_oper)

        widget = self._setup_view()
        self._setup_view_finish()
        self.append(widget)

        self.log.debug("Initialized")

    def _setup_view_finish(self):
        self.view.column_title.set_title(self.config_for.title())
        self.view.cv.append_column(self.view.column_title)
        self.view.column_title.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.ASCENDING)

    def _on_filter_selected(self, *args):
        self.view.refilter()

    def _do_filter_view(self, item, filter_list_model):
        chunk = self.entry.get_text().upper()
        string = "%s%s%s" % (item.id, item.title, item.subtitle)
        if chunk in string:
            return True
        return False


    def on_key_released(self, widget, keyval, keycode, state):
        self.log.debug("Active window: %s", self.app.get_active_window())
        keyname = Gdk.keyval_name(keyval)
        self.log.debug("Key: %s", keyname)

    def on_entrysearch_delete(self, *args):
        self.entry.set_text("")

    def on_entrysearch_changed(self, *args):
        self.search_term = self.entry.get_text()
        self.treefilter.refilter()
        if len(self.search_term) == 0:
            self.treeview.collapse_all()
        else:
            self.treeview.expand_all()

    def _setup_view(self):
        frmView = Gtk.Frame()
        self.view = MiAZColumnView(self.app)
        self.view.set_filter(self._do_filter_view)
        frmView.set_child(self.view)
        return frmView

    def __row_inserted(self, model, treepath, treeiter):
        self.treeview.set_cursor_on_cell(treepath, self.column, self.renderer, True)
        self.treeview.grab_focus()

    def config_save(self, items):
        with open(self.config_local, 'w') as fj:
            json.dump(items, fj)

    def on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'New %s' % self.config_for, '%s name' % self.config_for.title(), '')
        boxkey2 = dialog.get_boxKey2()
        boxkey2.set_visible(False)
        etyValue1 = dialog.get_value1_widget()
        search_term = self.entry.get_text()
        etyValue1.set_text(search_term)
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            value = dialog.get_value1()
            if len(value) > 0:
                items = self.config.load()
                if not value.upper() in items:
                    items.append(value.upper())
                    self.config.save(items)
                    self.log.debug("Added: %s", value.upper())
                    self.update()
        dialog.destroy()

    def on_item_rename(self, *args):
        return

    def on_item_remove(self, *args):
        # Delete from config and refresh model
        item = self.view.get_item()
        if item is None:
            return
        self.config.remove(item.id)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def config_set(self, config_for, config_local, config_global):
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global

    def update(self):
        items = []
        database = self.config.load()
        for row in database:
            items.append(File(id=row, title=row))
        self.view.update(items)


class MiAZCollections(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        self.config = MiAZConfigSettingsCollections()
        self.config_for = self.config.get_config_for()
        super().__init__(app, self.config_for)
        self.log = get_logger('MiAZSettings-%s' % self.config_for)


class MiAZOrganizations(MiAZConfigView):
    """Class for managing Organizations from Settings"""
    __gtype_name__ = 'MiAZOrganizations'

    def __init__(self, app):
        self.config = MiAZConfigSettingsOrganizations()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)


    def on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add new person or entity', 'Initials', 'Full name')
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            key = dialog.get_value1()
            value = dialog.get_value2()
            if len(key) > 0 and len(value) > 0:
                items = self.config.load()
                items[key.upper()] = value
                self.config.save(items)
                self.update()
                # ~ self.emit('updated')
        dialog.destroy()


class MiAZCountries(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        self.config = MiAZConfigSettingsCountries()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)
        self.box_buttons.set_visible(False)

    def config_check(self):
        if not os.path.exists(self.config_local):
            self.config_save()
            self.log.debug("Local config file for %s created empty" % self.config_for)

    def config_save(self):
        items = []
        def row(model, path, itr):
            code = model.get(itr, 1)[0]
            checked = model.get(itr, 3)[0]
            if checked:
                items.append(code)
        self.store.foreach(row)
        self.config.save(sorted(items))

    def on_item_remove(self, *args):
        return

class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        self.config = MiAZConfigSettingsPurposes()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)

    def on_item_add(self, *args):
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Add a new purpose', 'Purpose name', '')
        boxkey2 = dialog.get_boxKey2()
        boxkey2.set_visible(False)
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def on_response_item_add(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            value = dialog.get_value1()
            if len(value) > 0:
                items = self.config.load()
                if not value in items:
                    items.append(value.upper())
                    self.config.save(items)
                    self.update()
        dialog.destroy()
