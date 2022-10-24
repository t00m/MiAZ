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
from MiAZ.backend.config import MiAZConfigSettingsCollections
from MiAZ.backend.config import MiAZConfigSettingsOrganizations
from MiAZ.backend.config import MiAZConfigSettingsCountries
from MiAZ.backend.config import MiAZConfigSettingsExtensions
from MiAZ.backend.config import MiAZConfigSettingsPurposes
from MiAZ.frontend.desktop.widgets.widget import MiAZWidget
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
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
        self.entry.connect('changed', self.on_entrysearch_changed)
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

        widget = self.setup_treeview()
        self.append(widget)

        self.log.debug("Initialized")

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

    def setup_treeview(self):
        # Treeview for displaying
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.scrwin.set_has_frame(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.ListStore(str)
        self.selection = self.treeview.get_selection()
        self.selection.connect('changed', self.on_selection_changed)

        # Column: Name
        self.renderer = Gtk.CellRendererText()
        self.column = Gtk.TreeViewColumn('Name', self.renderer, text=0)
        self.column.set_visible(True)
        self.column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.column.set_expand(False)
        self.column.set_clickable(False)
        self.column.set_sort_indicator(True)
        self.column.set_sort_column_id(0)
        self.treeview.append_column(self.column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 0)
        self.sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.treeview.set_model(self.sorted_model)

        self.scrwin.set_child(self.treeview)

        return self.scrwin

    def clb_sort_function(self, model, row1, row2, sort_column=0):
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    def on_selection_changed(self, selection):
        pass

    def __row_inserted(self, model, treepath, treeiter):
        self.treeview.set_cursor_on_cell(treepath, self.column, self.renderer, True)
        self.treeview.grab_focus()

    def config_save(self, items):
        with open(self.config_local, 'w') as fj:
            json.dump(items, fj)

    # ~ def on_item_add(self, *args):
        # ~ # Add new item, save config and refresh model
        # ~ item = self.entry.get_text().upper()
        # ~ items = self.config.load()
        # ~ items.add(item.upper())
        # ~ self.config.save(items)
        # ~ self.log.debug("%s - Added: %s", self.config_for, item)
        # ~ self.entry.set_text('')
        # ~ self.entry.activate()
        # ~ self.update()

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
                if not value in items:
                    items.append(value.upper())
                    self.config.save(items)
                    self.log.debug("Added: %s", value.upper())
                    self.update()
        dialog.destroy()

    def on_item_rename(self, *args):
        return

    def on_item_remove(self, *args):
        # Delete from config and refresh model
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        item = model[treeiter][0]

        if item is None:
            return
        if len(item) == 0:
            return

        self.config.remove(item)
        self.update()
        self.entry.set_text('')
        self.entry.activate()

    def update(self):
        if self.config_local is None:
            return

        # Check config file and create it if doesn't exist
        self.config_check()
        self.store.clear()
        items = self.config_load()
        pos = 0
        for item in items:
            node = self.store.insert_with_values(pos, (0,), (item,))
            pos += 1

    def clb_visible_function(self, model, itr, data):
        item_name = model.get(itr, 0)[0]
        if item_name is None:
            return True
        if self.search_term is None:
            return True

        return self.search_term.upper() in item_name.upper()

    def config_set(self, config_for, config_local, config_global):
        self.config_for = config_for
        self.config_local = config_local
        self.config_global = config_global




class MiAZCollections(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        self.config = MiAZConfigSettingsCollections()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)
        self.log = get_logger('MiAZSettings-%s' % config_for)

    def update(self):
        self.store.clear()
        for item in self.config.load():
            node = self.store.insert_with_values(-1, (0,), (item,))


class MiAZOrganizations(MiAZConfigView):
    """Class for managing Organizations from Settings"""
    __gtype_name__ = 'MiAZOrganizations'

    def __init__(self, app):
        self.config = MiAZConfigSettingsOrganizations()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: flag icon, code, name, checkbox
        self.store = Gtk.ListStore(str, str)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # Initials
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Initials', renderer, text=0)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(0)
        self.treeview.append_column(column)

        # Full name
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn('Full name', renderer, text=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(1)
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 1)
        self.sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.treeview.set_model(self.sorted_model)

        self.treeview.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.treeview)
        return self.scrwin

    def clb_visible_function(self, model, itr, data):
        item_code = model.get(itr, 0)[0]
        item_name = model.get(itr, 1)[0]
        item = item_code+item_name
        if item_code is None and item_name is None:
            self.log.debug("RETURN!!!")
            return True
        if self.search_term is None:
            self.log.debug("RETURN!!!")
            return True

        match = self.search_term.upper() in item.upper()
        if match:
            return True
        else:
            return False

    def selection_changed(self, selection):
        if selection is None:
            return
        try:
            model, treeiter = selection.get_selected()
            code = model[treeiter][0]
            name = model[treeiter][0]
            tbuf = self.entry.get_buffer()
            tbuf.set_text("%s, %s" % (code, name), -1)
        except Exception as error:
            pass

    def double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        key = self.sorted_model[treeiter][0]
        value = self.sorted_model[treeiter][1]
        dialog = MiAZDialogAdd(self.app, self.get_root(), 'Modify person or entity', 'Initials', 'Full name')
        dialog.set_value1(key.upper())
        dialog.set_value2(value)
        dialog.connect('response', self.on_response_item_add)
        dialog.show()

    def update(self):
        self.store.clear()
        items = self.config.load()
        for code in items:
            fullname = items[code]
            self.store.insert_with_values(-1, (0, 1), (code, fullname))

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

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: flag icon, code, name, checkbox
        self.store = Gtk.ListStore(Pixbuf, str, str, bool)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # Flag Icon
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn('Flag', renderer, pixbuf=0)
        renderer.set_alignment(0.0, 0.5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        column.set_expand(False)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(2)
        column.set_sort_order(Gtk.SortType.ASCENDING)
        self.treeview.append_column(column)

        # Code
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Country Code', renderer, text=1)
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(1)
        self.treeview.append_column(column)

        # Country name
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Country', renderer, text=2)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(2)
        self.treeview.append_column(column)

        # Checkbox
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.__clb_row_toggled)
        column = Gtk.TreeViewColumn('Default?', renderer, active=3)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        column.set_expand(False)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(3)
        column.set_property('spacing', 50)
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 3)
        self.sorted_model.set_sort_column_id(3, Gtk.SortType.DESCENDING)
        self.treeview.set_model(self.sorted_model)

        self.treeview.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.treeview)
        return self.scrwin

    def clb_visible_function(self, model, itr, data):
        item_code = model.get(itr, 1)[0]
        item_name = model.get(itr, 2)[0]
        item = item_code+item_name
        if item_code is None and item_name is None:
            self.log.debug("RETURN!!!")
            return True
        if self.search_term is None:
            self.log.debug("RETURN!!!")
            return True

        match = self.search_term.upper() in item.upper()
        # ~ self.log.debug("%s > %s > %s", self.search_term, item_name, match)
        if match:
            return True
        else:
            return False

    def infobar_message(self):
        message_label = Gtk.Label()
        message_label.set_markup('<b>Check those countries you are insterested in.</b>\nThey will appear later in the workspace when you review your documents\nand choose a country for the same field.')
        self.infobar.add_child(message_label)

    def double_click(self, treeview, treepath, treecolumn):
        model = self.sorted_model.get_model()
        model[treepath][3] = not model[treepath][3]
        self.config_save()

    def config_check(self):
        if not os.path.exists(self.config_local):
            self.config_save()
            self.log.debug("Local config file for %s created empty" % self.config_for)

    def update(self):
        try:
            countries = self.config.load_global()
        except FileNotFoundError as error:
            self.log.error(error)
            return

        try:
            checked = self.config.load()
        except FileNotFoundError:
            checked = []

        n = 0
        for code in countries:
            icon_flag = os.path.join(ENV['GPATH']['FLAGS'], "%s.svg" % code)
            if not os.path.exists(icon_flag):
                icon_flag = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
            icon = self.app.icman.get_pixbuf_from_file_at_size(icon_flag, 32, 32)
            name = "%s (%s)" % (countries[code]["Country Name"], code)
            self.store.insert_with_values(n, (0, 1, 2, 3), (icon, code, name, code in checked))
            n += 1

    def config_save(self):
        items = []
        def row(model, path, itr):
            code = model.get(itr, 1)[0]
            checked = model.get(itr, 3)[0]
            if checked:
                items.append(code)
        self.store.foreach(row)
        self.config.save(sorted(items))

    def __clb_row_toggled(self, cell, path):
        model = self.sorted_model.get_model()
        rpath = self.sorted_model.convert_path_to_child_path(Gtk.TreePath(path))
        model[rpath][3] = not model[rpath][3]
        self.config_save()

    def on_item_remove(self, *args):
        return


class MiAZExtensions(MiAZConfigView):
    """Class for managing Collections from Settings"""
    __gtype_name__ = 'MiAZExtensions'

    def __init__(self, app):
        self.config = MiAZConfigSettingsExtensions()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)
        self.box_buttons.set_visible(False)

    def setup_treeview(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: icon, type, extension
        self.store = Gtk.TreeStore(Pixbuf, str, str)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # Extension Type Icon
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn('Type', renderer, pixbuf=0)
        renderer.set_alignment(0.0, 0.5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        column.set_expand(False)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(1)
        column.set_sort_order(Gtk.SortType.ASCENDING)
        self.treeview.append_column(column)

        # Section
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Section', renderer, markup=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(1)
        self.treeview.append_column(column)

        # Extension
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Extension', renderer, markup=2)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(2)
        self.treeview.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 1)
        self.sorted_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.treeview.set_model(self.sorted_model)

        # ~ self.treeview.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.treeview)
        return self.scrwin

    def update(self):
        extensions = self.config.load_global()
        sections = {}
        for ext in extensions:
            esections = extensions[ext]
            for section in esections:
                try:
                    parent = sections[section]
                except KeyError:
                    icon = self.app.icman.get_pixbuf_by_name('miaz-mime-%s' % section, 24)
                    parent = self.store.insert_with_values(None, -1, (0, 1,), (icon, section,))
                    sections[section] = parent
                self.store.insert_with_values(parent, -1, (2,), (ext,))

    def clb_visible_function(self, model, itr, data):
        item_name = model.get(itr, 2)[0]
        if item_name is None:
            return True
        if self.search_term is None:
            return True

        match = self.search_term.upper() in item_name.upper()
        if match:
            return True
        else:
            return False


class MiAZPurposes(MiAZConfigView):
    """Class for managing Purposes from Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        self.config = MiAZConfigSettingsPurposes()
        config_for = self.config.get_config_for()
        super().__init__(app, config_for)


    def update(self):
        self.store.clear()
        for item in self.config.load():
            node = self.store.insert_with_values(-1, (0,), (item,))

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
