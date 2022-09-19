#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod
import json

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib

from MiAZ.backend.env import ENV
from MiAZ.frontend.desktop.widgets.widget import MiAZWidget
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView

class MiAZCollections(MiAZWidget, Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    __gtype_name__ = 'MiAZCollections'
    current = None

    def __init__(self, app):
        super().__init__(app, __class__.__name__)
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_bottom(margin=12)
        self.set_margin_start(margin=12)

        box_oper = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_entry.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_has_frame(True)
        box_entry.append(self.entry)
        box_oper.append(box_entry)

        box_buttons = Gtk.Box(spacing=3, orientation=Gtk.Orientation.HORIZONTAL)
        box_buttons.append(self.app.create_button('gtk-edit', '', self.rename))
        box_buttons.append(Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL))
        box_buttons.append(self.app.create_button('list-add', '', self.add))
        box_buttons.append(self.app.create_button('list-remove', '', self.remove))
        box_oper.append(box_buttons)
        self.append(box_oper)

        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_hexpand(True)
        self.scrwin.set_vexpand(True)
        self.scrwin.set_has_frame(True)
        self.treeview = MiAZTreeView(self.app)
        self.store = Gtk.TreeStore(str)
        # ~ self.store.connect('row-inserted', self.__row_inserted)
        self.treeview.set_model(self.store)
        self.treeview.connect('row-activated', self.double_click)
        self.selection = self.treeview.get_selection()
        self.sig_selection_changed = self.selection.connect('changed', self.selection_changed)

        # Column: Name
        self.renderer = Gtk.CellRendererText()
        # ~ self.renderer.set_property('editable', True)
        # ~ self.renderer.set_property('editable-set', True)
        # ~ self.renderer.connect('edited', self.edit_name)
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
        self.treefilter.set_visible_func(self.__clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.sort_function, None)
        # ~ self.sorted_model.connect('row-inserted', self.__row_inserted)

        # ~ self.tree.connect('row-activated', self.treeview.double_click)

        self.scrwin.set_child(self.treeview)
        self.append(self.scrwin)

        self.check()
        self.update()

    def sort_function(self, model, row1, row2, user_data):
        sort_column = 0

        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)

        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    def double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        name = self.sorted_model[treeiter][0]
        dlgManageCollection = Gtk.Dialog()
        dlgManageCollection.set_modal(True)
        dlgManageCollection.set_title('Manage collection %s' % name)
        dlgManageCollection.set_size_request(300, 500)
        dlgManageCollection.set_transient_for(self.app.win)
        # ~ dlgManageCollection.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        # ~ dlgManageCollection.connect("response", self.collections_response)
        contents = dlgManageCollection.get_content_area()

        wdgCollections = Gtk.Label.new("Hello World!")
        contents.append(wdgCollections)
        dlgManageCollection.show()

    def selection_changed(self, selection):
        try:
            model, treeiter = selection.get_selected()
            name = model[treeiter][0]
            tbuf = self.entry.get_buffer()
            tbuf.set_text(name, -1)
            self.current = name
        except:
            pass

    def edit_name(self, widget, path, target):
        treeiter = self.sorted_model.get_iter(path)
        name = self.sorted_model[treeiter][0]
        print(name)
        print(target)

    def __row_inserted(self, model, treepath, treeiter):
        self.treeview.set_cursor_on_cell(treepath, self.column, self.renderer, True)
        self.treeview.grab_focus()

    def add(self, *args):
        self.log.debug(args)
        # ~ node = self.store.insert_with_values(None, -1, (0,), ('',))
        row = self.store.append(None, ('Type new collection name...',))

    def rename(self, *args):
        # ~ self.selection.disconnect(self.sig_selection_changed)
        try:
            tbuf = self.entry.get_buffer()
            renamed = tbuf.get_text()
            model, treeiter = self.selection.get_selected()
            model.remove(treeiter)
            self.log.error(dir(model))
            treeiter = self.store.insert_with_values(None, -1, (0,), (renamed,))
            self.selection.select_iter(treeiter)
        except:
            pass

        items = []

        def row(model, path, itr):
            name = model.get(itr, 0)[0]
            self.log.error("%s > %s", name, type(name))
            items.append(name)
        model.foreach(row)
        with open(ENV['FILE']['COLLECTIONS'], 'w') as fj:
            json.dump(sorted(items), fj)

        self.sorted_model.sort_column_changed()
        self.update()

        # THIS WORKS. Work with a list instead a treeview
        # ~ self.selection.disconnect(self.sig_selection_changed)
        # ~ tbuf = self.entry.get_buffer()
        # ~ renamed = tbuf.get_text()
        # ~ if self.current is not None:
            # ~ try:
                # ~ self.items.remove(self.current)
                # ~ self.items.append(renamed.upper())
            # ~ except ValueError:
                # ~ self.log.warning("%s was not in the list..." % self.current)
        # ~ with open(ENV['FILE']['COLLECTIONS'], 'w') as fj:
            # ~ print(sorted(self.items))
            # ~ json.dump(sorted(self.items), fj)
        # ~ self.update()

        self.sig_selection_changed = self.selection.connect('changed', self.selection_changed)

    # ~ def row_activated
        # ~ row = widget.get_active()  # the ID of the requested row
        # ~ print(row)
        # ~ self.treeview.row_activated(Gtk.TreePath(row), Gtk.TreeViewColumn(None))
        # ~ self.treeview.set_cursor(Gtk.TreePath(row))

    def remove(self, *args):
        self.log.debug(args)

    def check(self):
        if not os.path.exists(ENV['FILE']['COLLECTIONS']):
            import shutil
            self.log.debug("Collections file doesn't exist.")
            default_collections = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-collections.json')
            shutil.copy(default_collections, ENV['FILE']['COLLECTIONS'])
            self.log.debug("Collections config file created")

        with open(ENV['FILE']['COLLECTIONS'], 'r') as fcol:
            self.items = json.load(fcol)
            self.log.debug(self.items)
            self.log.debug(type(self.items))

    def update(self):
        self.store.clear()
        with open(ENV['FILE']['COLLECTIONS'], 'r') as fin:
            items = json.load(fin)
        pos = 0
        for item in items:
            node = self.store.insert_with_values(None, pos, (0,), (item,))
            pos += 1
        # ~ self.sorted_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

    def __clb_visible_function(self, model, itr, data):
        return True
