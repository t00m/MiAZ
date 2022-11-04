#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio
from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load
from MiAZ.backend.models import File, Collection, Person, Country, Purpose, Concept
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.widgets.row import MiAZListViewRow


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True
    displayed = 0
    switched = set()

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
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
        toolbar = self.factory.create_box_vertical(spacing=0, margin=0, vexpand=True)
        frmFilters = self.factory.create_frame(title='<big><b>Filters</b></big>', hexpand=False, vexpand=True)
        tlbFilters = self.factory.create_box_vertical()
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        self.ent_sb.connect('changed', self._on_filter_selected)
        box = self.factory.create_box_filter('Free search', self.ent_sb)
        tlbFilters.append(box)

        self.dropdown = {}
        for title, item_type, conf in [('Country', Country, 'countries'),
                                   ('Collection', Collection, 'collections'),
                                   ('From', Person, 'organizations'),
                                   ('Purpose', Purpose, 'purposes'),
                                   ('To', Person, 'organizations'),
                            ]:
            dropdown = self.factory.create_dropdown_generic(item_type)
            self.actions.dropdown_populate(dropdown, item_type, conf)
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
        self.filter = Gtk.CustomFilter.new(self._do_filter_listview, self.model_filter)
        self.model_filter.set_filter(self.filter)

        # Sorting
        self.model_sort = Gtk.SortListModel(model=self.model_filter)

        # Selection
        self.selection = Gtk.SingleSelection.new(self.model_sort)

        # Set up the factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        # Setup the view widget
        self.view = Gtk.ListView(model=self.selection, factory=factory, hexpand=True)
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
        box = MiAZListViewRow(self.app)
        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        miazboxrow = list_item.get_child()
        item = list_item.get_item()

        boxRow = miazboxrow.get_first_child()

        # Box Start
        boxStart = boxRow.get_first_child()
        btnMime = boxStart.get_first_child()
        imgMime = btnMime.get_first_child()
        mimetype = get_file_mimetype(item.id)
        gicon = self.app.icman.get_gicon_from_file_mimetype(mimetype)
        imgMime.set_from_gicon(gicon)
        # ~ imgMime.set_pixel_size(36)

        btnEdit = boxStart.get_last_child()
        imgEdit = btnEdit.get_first_child()
        imgEdit.set_from_icon_name('miaz-edit')
        # ~ imgEdit.set_pixel_size(36)

        # Box Center
        boxCenter = boxStart.get_next_sibling()
        label = boxCenter.get_first_child()
        label.set_markup("%s" % os.path.basename(item.id))

        # Box End
        boxEnd = boxCenter.get_next_sibling()
        switch = boxEnd.get_first_child()

    def _on_selected_item_notify(self, listview, _):
        self.log.debug("%s > %s", listview, type(listview))
        path = listview.get_selected_item()
        self.log.debug(path)

    def _on_activated_item(self, listview, position):
        item = self.model_filter.get_item(position)
        self.log.debug(item.id)

    def get_model_filter(self):
        return self.model_filter

    def get_selection(self):
        return self.selection

    def get_switched(self):
        return self.switched

    def get_item(self):
        selection = self.get_selection()
        selected = selection.get_selection()
        model = self.get_model_filter()
        pos = selected.get_nth(0)
        return model.get_item(pos)

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
        self.switched = set()

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

    def _on_filter_selected(self, *args):
        self.displayed = 0
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()

    def show_dashboard(self, *args):
        self.displayed = 0
        self.show_dashboard = True
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()

    def show_review(self, *args):
        self.displayed = 0
        self.show_dashboard = False
        self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()

    def foreach(self):
        last = self.model_filter.get_n_items()
        for pos in range(0, last):
            item = self.model_filter.get_item(pos)
            self.log.debug(item.id)

    def document_display(self, *args):
        item = self.get_selected()
        self.actions.document_display(item.id)

    def document_switch(self, switch, activated):
        selection = self.get_selection()
        selected = selection.get_selection()
        model = self.get_model_filter()
        switched = self.get_switched()
        pos = selected.get_nth(0)
        item = model.get_item(pos)
        if activated:
            switched.add(item.id)
        else:
            switched.remove(item.id)
        self.log.debug(switched)

    def document_rename(self, *args):
        source = self.get_item().id
        self.actions.document_rename(source)

    def get_selected(self, *args):
        selection = self.get_selection()
        model = self.get_model_filter()
        selected = selection.get_selection()
        pos = selected.get_nth(0)
        item = model.get_item(pos)
        return item
