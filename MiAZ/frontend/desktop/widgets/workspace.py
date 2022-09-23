#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
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
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, gui):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.gui = gui
        self.config = self.gui.config
        self.set_vexpand(True)
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_vexpand(True)

        # Model: document icon, mimetype, current filename, suggested filename (if needed), accept suggestion, filepath
        self.store = Gtk.TreeStore(Pixbuf, str, bool, str, str, str)
        self.tree = MiAZTreeView(self.gui)
        self.tree.set_model(self.store)

        self.refresh_view()

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
        self.tree.append_column(column)

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
        self.tree.append_column(column)

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
        self.tree.append_column(column)

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
        self.tree.append_column(column)


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
        self.tree.append_column(column)

        # Filepath
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Document path', renderer, markup=5)
        column.set_visible(False)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        self.tree.append_column(column)

        # Treeview filtering
        self.treefilter = self.store.filter_new()
        self.treefilter.set_visible_func(self.__clb_visible_function)

        # TreeView sorting
        self.sorted_model = Gtk.TreeModelSort(model=self.treefilter)

        self.tree.connect('row-activated', self.double_click)

        self.scrwin.set_child(self.tree)
        self.append(self.scrwin)

    def double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        filepath = self.sorted_model[treeiter][5]
        if os.path.exists(filepath):
            os.system("xdg-open '%s'" % filepath)

    def refresh_view(self):
        import os
        from MiAZ.backend.controller import get_documents, valid_filename
        self.store.clear()
        try:
            source_path = self.config.get('source')
        except KeyError:
            return
        # ~ print("Get documents from %s" % source_path)
        documents = get_documents(source_path)
        icon = Pixbuf.new_from_file(ENV['FILE']['APPICON'])
        icon_stop = self.gui.icman.get_pixbuf_by_name('process-stop', 24)
        INVALID = self.store.insert_with_values(None, -1, (0, 1, 2, 3, 4, 5), (icon, "", False, "File name not valid", "", ""))
        VALID = self.store.insert_with_values(None, -1, (0, 1, 2, 3, 4, 5), (icon, "", False, "File name valid", "", ""))
        for filepath in documents:
            document = os.path.basename(filepath)
            mimetype = get_file_mimetype(filepath)
            icon = self.gui.icman.get_pixbuf_mimetype_from_file(filepath)
            valid, reasons = valid_filename(filepath)
            if not valid:
                node = self.store.insert_with_values(INVALID, -1, (0, 1, 2, 3, 4, 5), (icon, mimetype, False, "<b>%s</b>" % document, document, filepath))
                for reason in reasons:
                    self.store.insert_with_values(node, -1, (0, 3), (icon_stop, "<i>%s</i>" % reason))
            else:
                self.store.insert_with_values(VALID, -1, (0, 1, 3, 5), (icon, mimetype, document, filepath))

    def edit_filename(self, widget, path, target):
        treeiter = self.sorted_model.get_iter(path)
        filename = self.sorted_model[treeiter][4]
        # ~ print(filename)
        # ~ print(target)

    def edit_filename_finished(self, widget, path, target):
        treeiter = self.sorted_model.get_iter(path)
        filename = self.sorted_model[treeiter][4]
        # ~ print(filename)

    def __clb_visible_function(self, model, itr, data):
        return True

    def __clb_row_toggled(self, cell, path):
        model = self.sorted_model.get_model()
        rpath = self.sorted_model.convert_path_to_child_path(Gtk.TreePath(path))
        model[rpath][2] = not model[rpath][2]
