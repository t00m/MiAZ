#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load
from MiAZ.backend.models import File, Collection, Person, Country, Purpose, Concept
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, RowIcon


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True
    displayed = 0
    switched = set()
    dfilter = {}
    signals = set()

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
        widget = self.factory.create_box_vertical(hexpand=False, vexpand=True)
        head = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True)
        body = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        widget.append(head)
        widget.append(body)

        actionbar = Gtk.ActionBar.new()
        actionbar.set_hexpand(True)
        actionbar.set_vexpand(True)
        lblToolbar = self.factory.create_label('<big><b>Filters</b></big>')
        boxEmpty = self.factory.create_box_horizontal(hexpand=True)
        btnClear = self.factory.create_button('miaz-entry-clear')
        actionbar.pack_start(lblToolbar)
        actionbar.pack_start(boxEmpty)
        actionbar.pack_end(btnClear)
        head.append(actionbar)



        # ~ toolbar = self.factory.create_box_vertical(spacing=0, margin=0, vexpand=True)
        # ~ frmFilters = self.factory.create_frame(title=, hexpand=False, vexpand=True)
        # ~ frmFilters.set_label_align(0.0)
        # ~ tlbFilters = self.factory.create_box_vertical()
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        self.ent_sb.connect('changed', self._on_filter_selected)
        boxEntry = self.factory.create_box_filter('Free search', self.ent_sb)
        body.append(boxEntry)
        # ~ tlbFilters.append(box)

        # FIXME: Do NOT fill dropdowns here.
        self.dropdown = {}
        for title, item_type, conf in [('Country', Country, 'countries'),
                                   ('Collection', Collection, 'collections'),
                                   ('From', Person, 'organizations'),
                                   ('Purpose', Purpose, 'purposes'),
                                   ('To', Person, 'organizations'),
                            ]:
            dropdown = self.factory.create_dropdown_generic(item_type)
            self.actions.dropdown_populate(dropdown, item_type, conf)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            # ~ self.signals.add ((dropdown, sigid))
            boxDropdown = self.factory.create_box_filter(title, dropdown)
            body.append(boxDropdown)
            self.dropdown[title.lower()] = dropdown
            self.log.debug(title)

        # ~ frmFilters.set_child(tlbFilters)
        # ~ toolbar.append(frmFilters)
        self.backend.connect('source-configuration-updated', self.update)
        return widget

    def _on_factory_setup_icon(self, factory, list_item):
        box = RowIcon()
        list_item.set_child(box)

    def _on_factory_bind_icon(self, factory, list_item):
        """To be subclassed"""
        box = list_item.get_child()
        item = list_item.get_item()
        icon = box.get_first_child()
        mimetype, val = Gio.content_type_guess('filename=%s' % item.id)
        gicon = Gio.content_type_get_icon(mimetype)
        icon.set_from_gicon(gicon)
        icon.set_pixel_size(32)

    def _on_selection_changed(self, selection, position, n_items):
        self.selected_items = []
        model = selection.get_model()
        bitset = selection.get_selection()
        for index in range(bitset.get_size()):
            pos = bitset.get_nth(index)
            item = model.get_item(pos)
            self.selected_items.append(item)
        self.btnDocsSel.set_label("%d documents selected" % len(self.selected_items))

    def _setup_view(self):
        widget = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        head = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True)
        body = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        widget.append(head)
        widget.append(body)

        mnuSelMulti = self.create_menu_selection_multiple()
        # Documents selected
        boxDocsSelected = Gtk.CenterBox()
        self.lblDocumentsSelected = "No documents selected"
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_label(self.lblDocumentsSelected)
        self.popDocsSel = Gtk.PopoverMenu.new_from_model(mnuSelMulti)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_valign(Gtk.Align.CENTER)
        self.btnDocsSel.set_hexpand(False)
        self.btnDocsSel.set_sensitive(True)
        boxDocsSelected.set_center_widget(self.btnDocsSel)
        lblFrmView = self.factory.create_label('<big><b>Documents</b></big>')
        # ~ lblFrmView.set_extra_menu(mnuSelMulti)
        # ~ hbox =
        lblFrmView.set_xalign(0.0)
        lblFrmView.set_hexpand(True)
        lblFrmView.set_vexpand(True)
        actionbar = Gtk.ActionBar.new()
        actionbar.set_hexpand(True)
        actionbar.set_vexpand(True)
        boxEmpty = self.factory.create_box_horizontal(hexpand=True)
        btnSelectAll = self.factory.create_button('miaz-select-all')
        btnSelectNone = self.factory.create_button('miaz-select-none')
        actionbar.pack_start(child=boxDocsSelected) #lblFrmView)
        actionbar.pack_start(child=boxEmpty)
        actionbar.pack_end(child=btnSelectAll)
        actionbar.pack_end(child=btnSelectNone)
        head.append(actionbar)
        # ~ frmView = self.factory.create_frame(hexpand=True, vexpand=True)
        # ~ frmView.set_label_widget(hbox)
        # ~ label_widget = frmView.get_label_widget()
        # ~ label_widget.set_hexpand(True)
        # ~ label_widget.set_vexpand(True)
        # ~ self.app.update_title(boxDocsSelected)



        # ColumnView
        self.view = MiAZColumnView(self.app)

        # Custom factory for ColumViewColumn icon
        factory_icon = Gtk.SignalListItemFactory()
        factory_icon.connect("setup", self._on_factory_setup_icon)
        factory_icon.connect("bind", self._on_factory_bind_icon)
        self.view.column_icon.set_factory(factory_icon)
        self.view.column_icon.set_title("Type")
        self.view.cv.append_column(self.view.column_icon)
        self.view.cv.append_column(self.view.column_title)
        self.view.cv.set_single_click_activate(False)
        # ~ view.cv.append_column(view.column_active)
        self.view.column_title.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.DESCENDING)
        self.view.set_filter(self._do_filter_view)
        self.view.select_first_item()
        # ~ frmView.set_child(self.view)
        body.append(self.view)

        # Connect signals
        selection = self.view.get_selection()
        self._on_signal_filter_connect()

        return widget

    def create_menu_selection_multiple(self):
        self.menu_workspace_multiple = Gio.Menu.new()

        fields = ['date', 'country', 'collection', 'purpose']
        item_fake = Gio.MenuItem.new()
        item_fake.set_label('Multiple selection')
        action = Gio.SimpleAction.new('fake', None)
        item_fake.set_detailed_action(detailed_action='fake')
        self.menu_workspace_multiple.append_item(item_fake)

        # Submenu for mass renaming
        submenu_rename_root = Gio.Menu.new()
        submenu_rename = Gio.MenuItem.new_submenu(
            label='Mass renaming of...',
            submenu=submenu_rename_root,
        )
        self.menu_workspace_multiple.append_item(submenu_rename)

        for item in fields:
            menuitem = Gio.MenuItem.new()
            menuitem.set_label(label='... %s' % item)
            action = Gio.SimpleAction.new('rename_%s' % item, None)
            callback = 'self.action_rename'
            # ~ action.connect('activate', eval(callback), item)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.rename_%s' % item)
            submenu_rename_root.append_item(menuitem)

        # Submenu for mass adding
        submenu_add_root = Gio.Menu.new()
        submenu_add = Gio.MenuItem.new_submenu(
            label='Mass adding of...',
            submenu=submenu_add_root,
        )
        self.menu_workspace_multiple.append_item(submenu_add)

        for item in fields:
            menuitem = Gio.MenuItem.new()
            menuitem.set_label(label='... %s' % item)
            action = Gio.SimpleAction.new('add_%s' % item, None)
            callback = 'self.action_add'
            # ~ action.connect('activate', eval(callback), item)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.add_%s' % item)
            submenu_add_root.append_item(menuitem)

        item_force_update = Gio.MenuItem.new()
        item_force_update.set_label(label='Force update')
        action = Gio.SimpleAction.new('workspace_update', None)
        # ~ action.connect('activate', self.update)
        self.app.add_action(action)
        item_force_update.set_detailed_action(detailed_action='app.workspace_update')
        self.menu_workspace_multiple.append_item(item_force_update)

        item_delete = Gio.MenuItem.new()
        item_delete.set_label(label='Delete documents')
        action = Gio.SimpleAction.new('workspace_delete', None)
        # ~ action.connect('activate', self.noop)
        self.app.add_action(action)
        item_delete.set_detailed_action(detailed_action='app.workspace_delete')
        self.menu_workspace_multiple.append_item(item_delete)
        return self.menu_workspace_multiple

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
        # ~ self._on_signal_filter_disconnect()
        repocnf = self.backend.get_repo_source_config_file()
        self.repodct = json_load(repocnf)
        items = []
        for path in self.repodct:
            items.append(File(id=path, title=os.path.basename(path)))
        self.view.update(items)
        self._on_filter_selected()
        self.update_title()
        # ~ self.actions.dropdown_populate(self.dropdown['country'], Country, 'countries', True, self.dfilter['country'])
        # ~ self._on_signal_filter_connect()

    def update_filters(self, item, ival):
        n = 0
        for field in ['date', 'country', 'collection', 'from', 'purpose', 'concept', 'to']:
            try:
                values = self.dfilter[field]
                values.add(ival[n])
            except Exception as error:
                values = set()
                values.add(ival[n])
                self.dfilter[field] = values
            n += 1

    def update_title(self):
        # ~ label = self.factory.create_label(text= "Displaying %d of %d documents" % (self.displayed, len(self.repodct)))
        # ~ self.app.update_title(label)
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

    def _do_filter_view(self, item, filter_list_model):
        valid = self.repodct[item.id]['valid']
        fields = self.repodct[item.id]['fields']
        display = False
        if self.show_dashboard:
            if valid:
                c0 = self._do_eval_cond_matches_freetext(item.id)
                c1 = self._do_eval_cond_matches(self.dropdown['country'], fields[1])
                c2 = self._do_eval_cond_matches(self.dropdown['collection'], fields[2])
                c3 = self._do_eval_cond_matches(self.dropdown['from'], fields[3])
                c4 = self._do_eval_cond_matches(self.dropdown['purpose'], fields[4])
                c6 = self._do_eval_cond_matches(self.dropdown['to'], fields[6])
                display = c0 and c1 and c2 and c3 and c4 and c6
        else:
            if not valid:
                display = self._do_eval_cond_matches_freetext(item.id)

        if display:
            self.update_filters(item, fields)
            self.displayed += 1

        return display

    def _on_signal_filter_disconnect(self):
        disconnected = self.signals.copy()
        for widget, sigid in self.signals:
            widget.disconnect(sigid)
        self.signals -= disconnected

    def _on_signal_filter_connect(self):
        self.signals = set()
        sigid = self.ent_sb.connect('changed', self._on_filter_selected)
        self.signals.add((self.ent_sb, sigid))
        for dropdown in self.dropdown:
            sigid = self.dropdown[dropdown].connect("notify::selected-item", self._on_filter_selected)
            self.signals.add((self.dropdown[dropdown], sigid))
        selection = self.view.get_selection()
        sigid = selection.connect('selection-changed', self._on_selection_changed)
        self.signals.add((selection, sigid))


    def _on_filter_selected(self, *args):
        self.displayed = 0
        self.dfilter = {}
        self.view.refilter()
        self.update_title()
        # FIXME:
        # ~ self.log.debug(self.dfilter)
        # ~
                                   # ~ ('Collection', Collection, 'collections'),
                                   # ~ ('From', Person, 'organizations'),
                                   # ~ ('Purpose', Purpose, 'purposes'),
                                   # ~ ('To', Person, 'organizations'),
                            # ~ ]:
            # ~ self.actions.dropdown_populate(self.dropdown[title], item_type, conf)
        # ~ self._on_signal_filter_connect()

    def show_dashboard(self, *args):
        self.displayed = 0
        self.dfilter = {}
        self.show_dashboard = True
        self.view.refilter()
        self.update_title()

    def show_review(self, *args):
        self.displayed = 0
        self.dfilter = {}
        self.show_dashboard = False
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
