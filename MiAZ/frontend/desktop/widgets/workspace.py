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
from gi.repository import Gdk
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
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU


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

        self.create_actions()
        self.create_menu()

        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_has_frame(True)
        self.scrwin.set_vexpand(True)

        # ~ self.viewport = Gtk.Viewport()

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
        renderer.connect('edited', self.on_edit_filename)

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
        self.treeview.connect('row-activated', self.on_double_click)

        # Selection type
        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        # Gestures controller / Right click
        self.evk = Gtk.GestureClick.new()
        self.evk.set_button(0)  # 0 for all buttons
        self.evk.connect("pressed", self.on_right_click)
        self.treeview.add_controller(self.evk)

        # ~ self.viewport.set_child(self.treeview)
        # ~ self.scrwin.set_child(self.viewport)
        # ~ self.viewport.set_child()
        self.scrwin.set_child(self.treeview)
        self.append(self.scrwin)

        self.backend.connect('source-configuration-updated', self.update)

    def create_actions(self):
        action = Gio.SimpleAction.new("something", None)
        action.connect("activate", self.noop)
        self.app.win.add_action(action)

    def create_menu(self):
        self.menu = Gio.Menu.new()
        self.menu.append("Do Something", "app.win.something")


    def on_entry_filename_changed(self, *args):
        self.treefilter.refilter()

    def on_double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        filepath = self.sorted_model[treeiter][5]
        if os.path.exists(filepath):
            os.system("xdg-open '%s'" % filepath)

    def update(self, *args):
        self.log.debug("Got signal 'source-configuration-updated'")
        self.store.clear()
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        icon_ko = self.app.icman.get_pixbuf_by_name('miaz-cancel', 24)
        icon_ok = self.app.icman.get_pixbuf_by_name('miaz-ok', 24)
        ndocs = 0
        for filepath in repodct:
            try:
                document = os.path.basename(filepath)
                suggested = repodct[filepath]['suggested']
                mimetype = get_file_mimetype(filepath)
                icon = self.app.icman.get_pixbuf_mimetype_from_file(filepath, 36, 36)
                node = self.store.insert_with_values(None, -1, (0, 1, 2, 3, 4, 5, 6), (icon, mimetype, False, "<b>%s</b>" % document, suggested, filepath, "FILE"))
                for reason in repodct[filepath]['reasons']:
                    passed, message = reason
                    if passed:
                        self.store.insert_with_values(node, -1, (0, 3, 6), (icon_ok, "<i>%s</i>" % message, "REASON"))
                    else:
                        self.store.insert_with_values(node, -1, (0, 3, 6), (icon_ko, "<i>%s</i>" % message, "REASON"))
            except KeyError:
                self.log.warning("Perhaps the document '%s' was moved to target folder?")
        page = self.app.get_stack_page_by_name('workspace')
        page.set_badge_number(len(repodct))

    def on_edit_filename(self, widget, path, target):
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
            self.log.info("%s renamed to %s", os.path.basename(source), os.path.basename(target))

    def on_edit_filename_finished(self, widget, path, target):
        print("on_edit_filename_finished")
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

    def on_right_click(self, gesture, n_press, x, y):
        right_click = self.evk.get_current_button() == 3
        if right_click:
            selection = self.treeview.get_selection()
            model, rows = selection.get_selected_rows()
            for row in rows:
                self.log.debug(row)
            rect = Gdk.Rectangle()
            rect.x = x = int(x)
            rect.y = y = int(y)
            self.popover = Gtk.PopoverMenu()
            self.popover.set_pointing_to(rect)
            self.popover.set_parent(self.treeview)
            self.popover.set_has_arrow(True)

            menu = self.create_menu()
            self.popover.set_menu_model(menu)

            # ~ box = self.build_popover()
            # ~ self.popover.set_child(self.app.create_button('miaz-remove', 'Delete document'))
            self.popover.popup()
        return True

    def build_popover(self):
        # ~ listbox.set_selection_mode(mode=Gtk.SelectionMode.SINGLE)
        # ~ listbox.set_activate_on_single_click(True)
        # ~ listbox.set_margin_top(margin=6)
        # ~ listbox.set_margin_end(margin=6)
        # ~ listbox.set_margin_bottom(margin=6)
        # ~ listbox.set_margin_start(margin=6)
        # ~ listbox.get_style_context().add_class(class_name='boxed-list')
        # ~ row = Adw.ActionRow.new()
        # ~ row.set_title(title='Change field country')
        # ~ listbox.append(row)
        # ~ row = Adw.ActionRow.new()
        # ~ row.set_title(title='Change field collection')
        # ~ listbox.append(row)

        box = Gtk.Box(spacing = 3, orientation=Gtk.Orientation.VERTICAL)
        button = self.app.create_button('miaz-res-countries', 'Change field country', self.noop)
        box.append(button)
        button = self.app.create_button('miaz-res-collections', 'Change field collection', self.noop)
        box.append(button)
        button = self.app.create_button('miaz-res-who', 'Change field <i>From</i>', self.noop)
        box.append(button)
        button = self.app.create_button('miaz-res-purposes', 'Change field <i>purpose</i>', self.noop)
        box.append(button)
        button = self.app.create_button('miaz-res-languages', 'Change field <i>concept</i>', self.noop)
        box.append(button)
        button = self.app.create_button('miaz-res-who', 'Change field <i>to</i>', self.noop)
        box.append(button)
        return box

    def noop(self, *args):
        selection = self.treeview.get_selection()
        model, rows = selection.get_selected_rows()
        try:
            start = rows[0]
        except:
            return
        end = rows[-1]
        ns = len(rows)
        self.log.debug("Number of rows selected: %d", ns)

    def create_menu(self):
        gio_menu_workspace = Gio.Menu.new()
        items = [
                    ('Rename document', 'app.rename', 'rename'),
                    ('Delete document', 'app.delete', 'delete')
                ]
        for item_label, item_action, simple in items:
            item = Gio.MenuItem.new()
            item.set_label(item_label)
            action = Gio.SimpleAction.new(simple, None)
            action.connect("activate", self.noop)
            self.app.add_action(action)
            item.set_detailed_action(detailed_action=item_action)
            gio_menu_workspace.append_item(item)
        return gio_menu_workspace
