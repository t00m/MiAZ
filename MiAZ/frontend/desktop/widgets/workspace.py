#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_backend()
        self.config = self.app.get_config('app')
        self.set_vexpand(True)
        self.set_margin_top(margin=6)
        self.set_margin_end(margin=6)
        self.set_margin_bottom(margin=6)
        self.set_margin_start(margin=6)

        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_has_frame(True)
        self.scrwin.set_vexpand(True)

        # Model: document icon, mimetype, current filename, suggested filename (if needed), accept suggestion, filepath
        self.store = Gtk.TreeStore(Pixbuf, str, bool, str, str, str, str)
        self.treeview = MiAZTreeView(self.app)
        self.treeview.set_model(self.store)

        # ~ self.update()

        # Icon
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

        # Mimetype
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Mimetype', renderer, text=1)
        renderer.set_property('background', '#F0E3E3')
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        column.set_sort_column_id(1)
        self.treeview.append_column(column)

        # Checkbox
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.__clb_row_toggled)
        column = Gtk.TreeViewColumn('Accept change', renderer, active=2)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        column.set_expand(False)
        column.set_clickable(True)
        column.set_sort_indicator(False)
        column.set_property('spacing', 50)
        self.treeview.append_column(column)

        # Current filename
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn('Current filename', renderer, markup=3)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(3)
        self.treeview.append_column(column)


        # Suggested filename
        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        renderer.set_property('editable', True)
        renderer.connect('edited', self.edit_filename)

        column = Gtk.TreeViewColumn('Suggest filename', renderer, markup=4)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.set_sort_column_id(4)
        self.treeview.append_column(column)

        # Filepath
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Document path', renderer, markup=5)
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        self.treeview.append_column(column)

        # Internal Row Type
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Row Type', renderer, text=6)
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        self.treeview.append_column(column)


        # Treeview filtering
        self.treefilter = self.store.filter_new()
        # ~ self.treefilter.set_visible_func(self.clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)
        self.sorted_model.set_sort_func(0, self.clb_sort_function, 1)
        self.sorted_model.set_sort_column_id(1, Gtk.SortType.DESCENDING)
        self.treeview.set_model(self.sorted_model)

        self.treeview.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.treeview)

        # ~ self.append(toolbar)
        self.append(self.scrwin)

        self.backend.connect('source-updated', self.update)

    def on_entry_filename_changed(self, *args):
        self.treefilter.refilter()

    def double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        filepath = self.sorted_model[treeiter][5]
        if os.path.exists(filepath):
            os.system("xdg-open '%s'" % filepath)

    def update(self, *args):
        self.log.debug("Got signal 'source-updated'")
        # ~ self.log.debug(args)
        self.store.clear()
        repocnf = self.backend.get_repo_config_file()
        repodct = json_load(repocnf)
        icon_ko = self.app.icman.get_pixbuf_by_name('miaz-cancel', 24)
        icon_ok = self.app.icman.get_pixbuf_by_name('miaz-ok', 24)
        ndocs = 0
        # ~ self.log.debug(repocnf)
        for filepath in repodct:
            # ~ self.log.debug(filepath)
            document = os.path.basename(filepath)
            mimetype = get_file_mimetype(filepath)
            icon = self.app.icman.get_pixbuf_mimetype_from_file(filepath, 36, 36)
            self.log.debug("Update with: %s", filepath)
            valid, reasons = repodct[filepath]['valid']
            if not valid:
                ndocs += 1
                node = self.store.insert_with_values(None, -1, (0, 1, 2, 3, 4, 5, 6), (icon, mimetype, False, "<b>%s</b>" % document, document, filepath, "FILE"))
                for reason in reasons:
                    passed, message = reason
                    if passed:
                        self.store.insert_with_values(node, -1, (0, 3, 6), (icon_ok, "<i>%s</i>" % message, "REASON"))
                    else:
                        self.store.insert_with_values(node, -1, (0, 3, 6), (icon_ko, "<i>%s</i>" % message, "REASON"))


        # ~ try:
            # ~ source_path = self.config.get('source')
        # ~ except KeyError:
            # ~ return None

        # ~ documents = get_documents(source_path)
        # ~ icon = Pixbuf.new_from_file(ENV['FILE']['APPICON'])
        # ~ icon_ko = self.app.icman.get_pixbuf_by_name('miaz-cancel', 24)
        # ~ icon_ok = self.app.icman.get_pixbuf_by_name('miaz-ok', 24)
        # ~ ndocs = 0
        # ~ for filepath in documents:
            # ~ document = os.path.basename(filepath)
            # ~ mimetype = get_file_mimetype(filepath)
            # ~ icon = self.app.icman.get_pixbuf_mimetype_from_file(filepath, 36, 36)
            # ~ valid, reasons = valid_filename(filepath)
            # ~ if not valid:
                # ~ ndocs += 1
                # ~ node = self.store.insert_with_values(None, -1, (0, 1, 2, 3, 4, 5, 6), (icon, mimetype, False, "<b>%s</b>" % document, document, filepath, "FILE"))
                # ~ for reason in reasons:
                    # ~ passed, message = reason
                    # ~ if passed:
                        # ~ self.store.insert_with_values(node, -1, (0, 3, 6), (icon_ok, "<i>%s</i>" % message, "REASON"))
                    # ~ else:
                        # ~ self.store.insert_with_values(node, -1, (0, 3, 6), (icon_ko, "<i>%s</i>" % message, "REASON"))
            # ~ else:
                # ~ self.log.debug("Document '%s' is valid", document)
        # ~ self.log.debug("Nº Invalid Documents: %d", ndocs)

    def edit_filename(self, widget, path, target):
        treeiter = self.sorted_model.get_iter(path)
        source = self.sorted_model[treeiter][4]
        filepath = self.sorted_model[treeiter][5]
        self.log.debug("Source: %s", source)
        self.log.debug("Target: %s", target)
        folder = os.path.dirname(filepath)
        source_path = os.path.join(folder, source)
        target_path = os.path.join(folder, target)
        if not os.path.exists(target_path):
            shutil.move(source_path, target_path)
            # ~ self.update()

    def edit_filename_finished(self, widget, path, target):
        print("edit_filename_finished")
        treeiter = self.sorted_model.get_iter(path)
        filename = self.sorted_model[treeiter][4]
        # ~ print(filename)

    def clb_sort_function(self, model, row1, row2, sort_column=0):
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        if value1 < value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    def clb_visible_function(self, model, itr, data):
        item_name = model.get(itr, 3)[0]
        row_type = model.get(itr, 6)[0]
        sbentry = self.app.get_searchbar_entry()
        filter_text = sbentry.get_text()

        if row_type == 'FOLDER' or row_type == 'REASON':
            return True

        match = filter_text.upper() in item_name.upper()

        if match:
            return True
        else:
            return False

    def __clb_row_toggled(self, cell, path):
        model = self.sorted_model.get_model()
        rpath = self.sorted_model.convert_path_to_child_path(Gtk.TreePath(path))
        model[rpath][2] = not model[rpath][2]

    def filter_view(self):
        self.treefilter.refilter()
