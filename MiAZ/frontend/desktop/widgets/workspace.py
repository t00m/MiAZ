#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
# ~ from datetime import datetime


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
from MiAZ.backend.util import json_load, json_save
from MiAZ.backend.models import File, Collection, Person, Country, Purpose, Concept
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.frontend.desktop.widgets.menu import MiAZ_APP_MENU
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.row import MiAZFlowBoxRow


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True
    displayed = 0

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.config = self.app.get_config('app')
        self.set_vexpand(False)
        self.set_margin_top(margin=6)
        self.set_margin_end(margin=6)
        self.set_margin_bottom(margin=6)
        self.set_margin_start(margin=6)
        toolbar = self._setup_toolbar()
        view = self._setup_view()
        self.append(toolbar)
        self.append(view)

    def _setup_toolbar(self):
        # Toolbar
        toolbar = self.factory.create_box_vertical(spacing=0, margin=0, vexpand=True)
        # ~ toolbar = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3, vexpand=True)
        frmFilters = self.factory.create_frame(title='<big><b>Filters</b></big>', hexpand=False, vexpand=True)
        tlbFilters = self.factory.create_box_vertical()
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        self.ent_sb.connect('changed', self._on_filter_selected)
        box = self.factory.create_box_filter('Free search', self.ent_sb)
        tlbFilters.append(box)

        self.dropdown = {}
        for title, model, item in [('Country', Country, 'countries'),
                                   ('Collection', Collection, 'collections'),
                                   ('From', Person, 'organizations'),
                                   ('Purpose', Purpose, 'purposes'),
                                   ('To', Person, 'organizations'),
                            ]:
            dropdown = self.factory.create_dropdown_generic(model, item)
            dropdown.connect("notify::selected-item", self._on_filter_selected)
            box = self.factory.create_box_filter(title, dropdown)
            tlbFilters.append(box)
            self.dropdown[title] = dropdown

        frmFilters.set_child(tlbFilters)
        toolbar.append(frmFilters)
        self.backend.connect('source-configuration-updated', self.update)
        return toolbar

    def _setup_view_body(self):
        boxViewBody = self.factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=True)
        frmViewBody = self.factory.create_frame(title='<big><b>Documents</b></big>', hexpand=True, vexpand=True)
        boxViewBody.append(frmViewBody)
        scrwin = self.factory.create_scrolledwindow()

        # Setup the model
        self.model = Gio.ListStore(item_type=File)

        # Filtering
        self.model_filter = Gtk.FilterListModel.new(self.model)
        self.model_filter.connect('items-changed', self._on_items_changed)
        self.filter = Gtk.CustomFilter.new(self._do_filter_listview, self.model_filter)
        self.model_filter.set_filter(self.filter)

        # Sorting
        self.model_sort = Gtk.SortListModel(model=self.model_filter)

        # Selection
        selection = Gtk.SingleSelection.new(self.model_sort)

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        # Setup the view widget
        self.view = Gtk.ListView(model=Gtk.SingleSelection.new(selection), factory=factory, hexpand=True)
        self.view.set_single_click_activate(True)
        self.view.connect('activate', self._on_activated_item)
        self.view.connect("notify::selected-item", self._on_selected_item_notify)

        scrwin.set_child(self.view)
        frmViewBody.set_child(scrwin)
        return boxViewBody

    def _setup_view(self):
        boxView = self.factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=True)
        boxViewBody = self._setup_view_body()
        boxView.append(boxViewBody)
        return boxView

    def _on_factory_setup(self, factory, list_item):
        box = MiAZFlowBoxRow()
        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        box = list_item.get_child()
        wdgIcon = box.get_first_child()
        wdgLabel = box.get_last_child()
        row = list_item.get_item()
        mimetype = get_file_mimetype(row.id)
        gicon = self.app.icman.get_gicon_from_file_mimetype(mimetype)
        wdgLabel.set_text(os.path.basename(row.id))
        wdgIcon.set_from_gicon(gicon)
        wdgIcon.set_pixel_size(36)

    def _on_selected_item_notify(self, listview, _):
        path = listview.get_selected_item()
        self.log.debug(path)

    def _on_items_changed(self, model_filter, position, removed, added):
        pass # keep?

    def _on_activated_item(self, listview, position):
        item = self.model_filter.get_item(position)
        self.log.debug(item.id)

    def update(self, *args):
        # FIXME: Get dict from backend
        repocnf = self.backend.get_repo_source_config_file()
        self.repodct = json_load(repocnf)
        self.model.remove_all()
        for path in self.repodct:
            self.model.append(File(id=path, name=os.path.basename(path)))
        self.update_title()

    def update_title(self):
        self.app.update_title(self.displayed, len(self.repodct))

    def _do_eval_cond_matches_freetext(self, path):
        left = self.ent_sb.get_text()
        right = path
        if left.upper() in right.upper():
            return True
        return False

    def _do_eval_cond_matches(self, dropdown, id):
        item = dropdown.get_selected_item()
        if item.id == 'Any':
            return True
        return item.id == id

    def _do_filter_listview(self, item, filter_list_model):
        valid = self.repodct[item.id]['valid']
        fields = self.repodct[item.id]['fields']
        display = False
        if self.show_dashboard:
            if valid:
                c0 = self._do_eval_cond_matches_freetext(item.id)
                c1 = self._do_eval_cond_matches(self.dropdown['Country'], fields[1])
                c2 = self._do_eval_cond_matches(self.dropdown['Collection'], fields[2])
                c3 = self._do_eval_cond_matches(self.dropdown['From'], fields[3])
                c4 = self._do_eval_cond_matches(self.dropdown['Purpose'], fields[4])
                c6 = self._do_eval_cond_matches(self.dropdown['To'], fields[6])
                display = c0 and c1 and c2 and c3 and c4 and c6
        else:
            if not valid:
                display = self._do_eval_cond_matches_freetext(item.id)

        if display:
            self.displayed += 1

        return display

    def action_rename_manually(self, button, data):
        row = data
        source = row.get_filepath()
        if self.repodct[source]['valid']:
            basename = os.path.basename(source)
            filename = basename[:basename.rfind('.')]
            target = filename.split('-')
        else:
            target = self.repodct[source]['suggested'].split('-')
        dialog = MiAZRenameDialog(self.app, row, source, target)
        dialog.connect('response', self._on_response_rename)
        dialog.show()

    def _on_response_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            row = dialog.get_row()
            source = dialog.get_filepath_source()
            target = os.path.join(os.path.dirname(source), dialog.get_filepath_target())
            shutil.move(source, target)
            self.log.debug("Rename document from '%s' to '%s'", os.path.basename(source), os.path.basename(target))
            self.backend.check_source()

    def action_rename(self, *args):
        self.log.debug(args)

    def action_add(self, *args):
        self.log.debug(args)

    def noop(self, *args):
        self.log.debug(args)

    def document_display(self, button, filepath):
        self.log.debug("Displaying %s", filepath)
        os.system("xdg-open '%s'" % filepath)

    def on_show_dashboard(self, *args):
        self.displayed = 0
        self.show_dashboard = True
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()

    def on_show_review(self, *args):
        self.displayed = 0
        self.show_dashboard = False
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()

    def _on_filter_selected(self, *args):
        self.displayed = 0
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()
