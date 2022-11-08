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
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView


# ~ class MiAZWSColumnView(MiAZColumnView):
    # ~ __gtype_name__ = 'MiAZWSColumnView'



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
        frmToolbar = self._setup_toolbar()
        frmView = self._setup_view()
        self.append(frmToolbar)
        self.append(frmView)

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

    def _setup_view(self):
        frmView = self.factory.create_frame(title='<big><b>Documents</b></big>', hexpand=True, vexpand=True)
        self.view = MiAZColumnView(self.app)
        self.view.cv.append_column(self.view.column_icon)
        self.view.cv.append_column(self.view.column_title)
        # ~ view.cv.append_column(view.column_active)
        self.view.column_title.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.DESCENDING)
        self.view.set_filter(self._do_filter_listview)
        self.view.select_first_item()
        frmView.set_child(self.view)

        return frmView

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
        selection = self.view.get_selection()
        selected = selection.get_selection()
        model = self.view.get_model_filter()
        pos = selected.get_nth(0)
        return model.get_item(pos)

    def update(self, *args):
        # FIXME: Get dict from backend
        repocnf = self.backend.get_repo_source_config_file()
        self.repodct = json_load(repocnf)
        items = []
        for path in self.repodct:
            items.append(File(id=path, title=os.path.basename(path)))
        self.view.update(items)
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
        self.view.refilter()
        # ~ self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.update_title()

    def show_dashboard(self, *args):
        self.displayed = 0
        self.show_dashboard = True
        # ~ self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.view.refilter()
        self.update_title()

    def show_review(self, *args):
        self.displayed = 0
        self.show_dashboard = False
        # ~ self.filter.emit('changed', Gtk.FilterChange.DIFFERENT)
        self.view.refilter()
        self.update_title()

    def foreach(self):
        last = self.model_filter.get_n_items()
        for pos in range(0, last):
            item = self.model_filter.get_item(pos)
            self.log.debug(item.id)

    def document_display(self, *args):
        item = self.get_item()
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
