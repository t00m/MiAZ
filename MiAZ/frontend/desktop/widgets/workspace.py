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

        self.setup_toolbar()
        self.setup_view()
        self.append(self.scrwin)

    def setup_toolbar(self):
        # Toolbar
        frame = Gtk.Frame()
        frame.set_margin_top(margin=6)
        frame.set_margin_end(margin=6)
        frame.set_margin_bottom(margin=6)
        frame.set_margin_start(margin=6)

        toolbar = Gtk.CenterBox()
        toolbar.set_margin_top(margin=6)
        toolbar.set_margin_end(margin=6)
        toolbar.set_margin_bottom(margin=6)
        toolbar.set_margin_start(margin=6)

        ## Filter box (left side)
        boxFilters = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        boxFilters.append(self.ent_sb)
        toolbar.set_start_widget(boxFilters)

        frame.set_child(toolbar)
        self.append(frame)

        # ~ self.controller = Gtk.EventControllerKey()
        # ~ self.controller.connect('key-released', self.on_key_released)
        # ~ self.add_controller(self.controller)

        self.backend.connect('source-configuration-updated', self.update)

    def setup_view(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_has_frame(False)
        self.scrwin.set_vexpand(True)
        self.listbox = Gtk.ListBox.new()
        self.listbox.set_show_separators(False)
        self.listbox.set_selection_mode(mode=Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_margin_top(margin=0)
        self.listbox.set_margin_end(margin=6)
        self.listbox.set_margin_bottom(margin=6)
        self.listbox.set_margin_start(margin=6)
        self.listbox.get_style_context().add_class(class_name='boxed-list')
        # ~ self.listbox.set_filter_func(self.clb_visible_function)

        # Row for displaying when there is no documents available
        self.nodata = Adw.ActionRow.new()
        self.nodata.set_title(title='<b>No documents found for review</b>')
        self.listbox.set_placeholder(self.nodata)
        self.scrwin.set_child(self.listbox)

    def update(self, *args):
        self.log.debug("Got signal 'target-configuration-updated'")
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        # ~ who = self.app.get_config('organizations')
        # ~ icon_ko = self.app.icman.get_pixbuf_by_name('miaz-cancel', 24)
        # ~ icon_ok = self.app.icman.get_pixbuf_by_name('miaz-ok', 24)
        for filename in repodct:
            dot = filename.rfind('.')
            doc = filename[:dot]
            ext = filename[dot+1:]
            icon = self.app.icman.get_icon_mimetype_from_file(filename, 96, 96)
            row = Adw.ActionRow.new()

            # ~ row.connect('activated', self.on_row_activated)
            # ~ row.connect('activate', self.on_row_activated)
            # ~ explain = "<span color='blue'>%s</span>" % filename
            explain = filename
            row.set_title(title=os.path.basename(doc))
            row.add_prefix(icon)
            row.set_subtitle(subtitle=filename)

            self.listbox.append(child=row)
        page = self.app.get_stack_page_by_name('workspace')
        page.set_badge_number(len(repodct))

    def clb_visible_function(self, row):
        title = row.get_title()
        # ~ sbentry = self.app.get_searchbar_entry()
        filter_text = self.ent_sb.get_text()
        if filter_text.upper() in title.upper():
            return True
        else:
            return False

    def on_key_released(self, widget, keyval, keycode, state):
        self.filter_view()
        # ~ keyname = Gdk.keyval_name(keyval)
        # ~ if Gdk.ModifierType.CONTROL_MASK & state and keyname == 'f':
        #       ....

    def on_row_activated(self, *args):
        self.log.debug(args)

    def __create_trvreasons(self, *args):
        scrreasons = Gtk.ScrolledWindow()
        trvreasons = Gtk.TreeView()
        trvreasons.set_vexpand(True)
        trvreasons.set_hexpand(False)
        trvreasons.set_headers_visible(False)
        model = Gtk.ListStore(Pixbuf, str)
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn('Type', renderer, pixbuf=0)
        renderer.set_alignment(0.0, 0.5)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_visible(True)
        trvreasons.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Reason', renderer, text=1)
        column.set_visible(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)
        column.set_clickable(False)
        column.set_sort_indicator(False)
        trvreasons.append_column(column)

        for reason in repodct[filename]['reasons']:
            passed, message = reason
            if passed:
                model.insert_with_values(-1, (0, 1), (icon_ok, message))
            else:
                model.insert_with_values(-1, (0, 1), (icon_ko, message))
        trvreasons.set_model(model)
        height = trvreasons.get_height()
        scrreasons.set_child(trvreasons)
        scrreasons.set_min_content_height(240)
        self.log.debug(height)
        scrreasons.set_vexpand(True)
        scrreasons.set_propagate_natural_height(True)
        row.add_row(scrreasons)
        row.set_vexpand(True)
