#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from abc import abstractmethod

import gi
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions as Ext


class MiAZDocBrowser(Gtk.Box):
    """ MiAZ Doc Browser Widget"""

    def __init__(self, app):
        super(MiAZDocBrowser, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZDocBrowser')
        self.app = app
        self.config = self.app.get_config('app')
        self.set_vexpand(True)

        self.setup_toolbar()
        self.setup_view_listbox()
        self.setup_stack()


        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}

    def setup_stack(self):
        self.stack = Adw.ViewStack()
        self.append(self.stack)

        page = self.stack.add_named(self.listbox, 'view-list')
        page.set_icon_name('miaz-view-list')

        view_grid = Gtk.Label.new('grid')
        page = self.stack.add_named(view_grid, 'view-grid')
        page.set_icon_name('miaz-view-grid')
        page.set_visible(False)

        view_tree = Gtk.Label.new('tree')
        page = self.stack.add_named(view_tree, 'view-tree')
        page.set_icon_name('miaz-view-tree')
        page.set_visible(False)

    def setup_toolbar(self):
        # https://gist.github.com/Afacanc38/76ce9b3260307bea64ebf3506b485147
        # Toolbar
        toolbar = Gtk.CenterBox()
        toolbar.set_margin_top(margin=6)
        toolbar.set_margin_end(margin=6)
        toolbar.set_margin_bottom(margin=6)
        toolbar.set_margin_start(margin=6)

        ## Filter box (left side)
        boxFilters = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        boxFilters.append(self.ent_sb)
        self.cmbCountry = Gtk.ComboBox()
        boxFilters.append(self.cmbCountry)
        toolbar.set_start_widget(boxFilters)

        # Views (right side)
        boxViews = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        boxViews.get_style_context().add_class(class_name='linked')
        # ~ button = self.app.create_button('miaz-view-list', '', self.show_view_list)
        # ~ boxViews.append(button)
        # ~ button = self.app.create_button('miaz-view-grid', '', self.show_view_grid)
        # ~ boxViews.append(button)
        # ~ button = self.app.create_button('miaz-view-tree', '', self.show_view_tree)
        # ~ boxViews.append(button)
        toolbar.set_end_widget(boxViews)

        self.append(toolbar)

        self.controller = Gtk.EventControllerKey()
        self.controller.connect('key-released', self.on_key_released)
        self.add_controller(self.controller)

    def nop(self, *args):
        self.log.debug(args)

    def show_view_list(self, *args):
        self.stack.set_visible_child_name('view-list')

    def show_view_grid(self, *args):
        self.stack.set_visible_child_name('view-grid')

    def show_view_tree(self, *args):
        self.stack.set_visible_child_name('view-tree')

    def setup_view_listbox(self):
        self.listbox = Gtk.ListBox.new()
        self.listbox.set_show_separators(True)
        self.listbox.set_selection_mode(mode=Gtk.SelectionMode.MULTIPLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_margin_top(margin=0)
        self.listbox.set_margin_end(margin=6)
        self.listbox.set_margin_bottom(margin=6)
        self.listbox.set_margin_start(margin=6)
        self.listbox.get_style_context().add_class(class_name='boxed-list')
        self.listbox.set_filter_func(self.clb_visible_function)
        # ~ self.append(child=self.listbox)

        # Row for displaying when there is no documents available
        self.nodata = Adw.ExpanderRow.new()
        # ~ self.nodata.set_icon_name(icon_name='MiAZ-big')
        self.nodata.set_title(title='<b>No documents found</b>')
        self.nodata.set_enable_expansion(False)
        self.nodata.set_show_enable_switch(False)
        self.listbox.set_placeholder(self.nodata)


        row = Adw.ExpanderRow.new()
        row.set_icon_name(icon_name='edit-find-symbolic')
        row.set_title(title='<big><b>Libadwaita uno</b></big>')
        row.set_subtitle(subtitle='Subtitle uno')
        row.get_style_context().add_class(class_name='error')
        self.listbox.append(child=row)

        row = Adw.ExpanderRow.new()
        row.set_icon_name(icon_name='edit-find-symbolic')
        row.set_title(title='Libadwaita dos')
        row.set_subtitle(subtitle='Subtitle dos')
        row.get_style_context().add_class(class_name='success')
        self.listbox.append(child=row)



    def clb_visible_function(self, row):
        title = row.get_title()
        # ~ sbentry = self.app.get_searchbar_entry()
        filter_text = self.ent_sb.get_text()
        if filter_text.upper() in title.upper():
            return True
        else:
            return False

    def filter_view(self):
        self.listbox.invalidate_filter()
        # ~ print("Re-filtering")

    def update(self):
        pass
        # ~ self.flowbox = Gtk.FlowBox.new()

    def on_key_released(self, widget, keyval, keycode, state):
        # ~ self.log.debug("Active window: %s", self.app.get_active_window())
        keyname = Gdk.keyval_name(keyval)
        # ~ self.log.debug("Key: %s", keyname)
        self.filter_view()
        # ~ if Gdk.ModifierType.CONTROL_MASK & state and keyname == 'f':
            # ~ if self.searchbar.get_search_mode():
                # ~ self.searchbar.set_search_mode(False)
            # ~ else:
                # ~ self.searchbar.set_search_mode(True)
        # ~ stack = self.stack.get_visible_child_name()
        # ~ if stack == 'workspace':
            # ~ self.workspace.filter_view()
        # ~ elif stack == 'browser':
            # ~ self.docbrowser.filter_view()
