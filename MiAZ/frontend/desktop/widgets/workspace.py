#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime

import humanize

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load
from MiAZ.backend.models import File, Collection, Person, Country, Purpose, Concept, SentBy, SentTo
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, RowIcon, RowTitle
from MiAZ.frontend.desktop.factory import MenuHeader


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True
    displayed = 0
    switched = set()
    dfilter = {}
    signals = set()
    num_review = 0

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
        self.config = self.app.get_config('App')
        self.set_vexpand(False)
        self.set_margin_top(margin=6)
        self.set_margin_end(margin=6)
        self.set_margin_bottom(margin=6)
        self.set_margin_start(margin=6)
        frmView = self._setup_workspace()
        self.append(frmView)

    def spinner_start(self, *args):
        self.spinner.start()
        self.spinner.set_spinning(True)
        self.log.debug("Spinner started")

    def spinner_stop(self, *args):
        self.spinner.stop()
        self.spinner.set_spinning(False)
        self.log.debug("Spinner stopped")

    def _setup_toolbar_filters(self):
        widget = self.factory.create_box_horizontal(hexpand=True, vexpand=False)
        body = self.factory.create_box_horizontal(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.set_homogeneous(True)
        body.set_margin_top(margin=6)
        widget.append(body)

        # FIXME: Do NOT fill dropdowns here.
        self.dropdown = {}
        for item_type in [Country, Collection, SentBy, Purpose, SentTo]:
            title = item_type.__gtype_name__
            dropdown = self.factory.create_dropdown_generic(item_type)
            self.actions.dropdown_populate(dropdown, item_type)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            # ~ self.signals.add ((dropdown, sigid))
            boxDropdown = self.factory.create_box_filter(title, dropdown)
            body.append(boxDropdown)
            self.dropdown[title] = dropdown
        self.backend.connect('source-configuration-updated', self.update)
        return widget

    def _on_factory_setup_collection(self, factory, list_item):
        box = RowTitle()
        list_item.set_child(box)

    def _on_factory_bind_collection(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        collection = self.repodct[item.id]['fields'][2]
        label.set_markup(collection)

    def _on_factory_setup_date(self, factory, list_item):
        box = RowTitle()
        list_item.set_child(box)

    def _on_factory_bind_date(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        date = item.date_dsc
        label.set_markup(date)

    def _on_factory_setup_sentby(self, factory, list_item):
        box = RowTitle()
        list_item.set_child(box)

    def _on_factory_bind_sentby(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.sentby_dsc)

    def _on_factory_setup_sentto(self, factory, list_item):
        box = RowTitle()
        list_item.set_child(box)

    def _on_factory_bind_sentto(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        label.set_markup(item.sentto_dsc)

    def _on_factory_setup_purpose(self, factory, list_item):
        box = RowTitle()
        list_item.set_child(box)

    def _on_factory_bind_purpose(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        label = box.get_first_child()
        purpose = self.repodct[item.id]['fields'][4]
        label.set_markup(purpose)

    def _on_factory_setup_flag(self, factory, list_item):
        box = RowIcon()
        list_item.set_child(box)

    def _on_factory_bind_flag(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        icon = box.get_first_child()
        code = self.repodct[item.id]['fields'][1]
        flag = os.path.join(ENV['GPATH']['FLAGS'], "%s.svg" % code)
        if not os.path.exists(flag):
            flag = os.path.join(ENV['GPATH']['FLAGS'], "__.svg")
        icon.set_from_file(flag)
        icon.set_pixel_size(32)



    def _on_action_rename(self, action, data, item_type):
        title = item_type.__gtype_name__
        self.log.debug("Rename %s for:", title)
        box = self.factory.create_box_vertical()
        label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(self.selected_items), title))
        dropdown = self.factory.create_dropdown_generic(item_type)
        self.actions.dropdown_populate(dropdown, item_type, any_value=False)
        # ~ self.actions.dropdown_populate(dropdown, item_type, conf)
        box.append(label)
        box.append(dropdown)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box)
        dialog.show()
        # ~ for item in self.selected_items:
            # ~ self.log.debug("\t%s", item.id)



    def _on_explain_toggled(self, button, data=None):
        active = button.get_active()
        self.view.column_title.set_visible(not active)
        self.view.column_subtitle.set_visible(active)
        self.column_collection.set_visible(active)
        self.column_purpose.set_visible(active)
        self.column_flag.set_visible(active)
        self.column_sentby.set_visible(active)
        self.column_sentto.set_visible(active)
        self.column_date.set_visible(active)

    def _on_filters_toggled(self, button, data=None):
        active = button.get_active()
        self.toolbar_filters.set_visible(active)

    def _on_selection_changed(self, selection, position, n_items):
        self.selected_items = []
        model = selection.get_model()
        bitset = selection.get_selection()
        for index in range(bitset.get_size()):
            pos = bitset.get_nth(index)
            item = model.get_item(pos)
            self.selected_items.append(item)
        self.btnDocsSel.set_label("%d of %d documents selected" % (len(self.selected_items), len(self.repodct)))

    def _setup_toolbar_top(self):
        toolbar_top = Gtk.CenterBox()
        toolbar_top.set_hexpand(True)
        toolbar_top.set_vexpand(True)

        # Centerbox Start Wiget
        cbws = self.factory.create_box_horizontal(margin=0, spacing=3)

        self.mnuSelMulti = self.create_menu_selection_multiple()
        # Documents selected
        boxDocsSelected = Gtk.CenterBox()
        self.lblDocumentsSelected = "No documents selected"
        self.btnDocsSel = Gtk.MenuButton(css_classes=['flat'])
        self.btnDocsSel.set_label(self.lblDocumentsSelected)
        self.popDocsSel = Gtk.PopoverMenu.new_from_model(self.mnuSelMulti)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_valign(Gtk.Align.CENTER)
        self.btnDocsSel.set_hexpand(False)
        self.btnDocsSel.set_sensitive(True)
        boxDocsSelected.set_center_widget(self.btnDocsSel)

        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        # ~ self.ent_sb.set_width_chars(41)
        self.ent_sb.connect('changed', self._on_filter_selected)
        self.ent_sb.set_hexpand(False)

        cbws.append(boxDocsSelected)
        # ~ cbws.append(self.ent_sb)

        cbwe = self.factory.create_box_horizontal(margin=0, spacing=3)

        boxEmpty = self.factory.create_box_horizontal(hexpand=False)
        btnSelectAll = self.factory.create_button('miaz-select-all', callback=self._on_select_all)
        btnSelectNone = self.factory.create_button('miaz-select-none', callback=self._on_select_none, css_classes=['flat'])
        sep = Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL)
        self.tgbExplain = self.factory.create_button_toggle('miaz-magic', callback=self._on_explain_toggled, css_classes=['flat'])
        self.tgbFilters = self.factory.create_button_toggle('miaz-filters', callback=self._on_filters_toggled, css_classes=['flat'])
        self.tgbFilters.set_active(False)

        cbwe.append(self.tgbExplain)
        cbwe.append(self.tgbFilters)
        cbwe.append(sep)
        cbwe.append(btnSelectNone)
        cbwe.append(btnSelectAll)

        toolbar_top.set_start_widget(cbws)
        toolbar_top.set_center_widget(self.ent_sb)
        toolbar_top.set_end_widget(cbwe)
        return toolbar_top

    def _setup_columnview(self):
        # ColumnView
        self.view = MiAZColumnView(self.app)

        # ~ # Custom factory for ColumViewColumn collection
        # ~ factory_collection = Gtk.SignalListItemFactory()
        # ~ factory_collection.connect("setup", self._on_factory_setup_collection)
        # ~ factory_collection.connect("bind", self._on_factory_bind_collection)
        # ~ self.column_collection = Gtk.ColumnViewColumn.new("Collection", factory_collection)
        # ~ self.column_collection.set_sorter(self.view.prop_collection_sorter)

        # ~ # Custom factory for ColumViewColumn SentBy
        # ~ factory_sentby = Gtk.SignalListItemFactory()
        # ~ factory_sentby.connect("setup", self._on_factory_setup_sentby)
        # ~ factory_sentby.connect("bind", self._on_factory_bind_sentby)
        # ~ self.column_sentby = Gtk.ColumnViewColumn.new("Sent by", factory_sentby)
        #self.column_sentby.set_sorter(self.view.prop_from_sorter)

        # ~ # Custom factory for ColumViewColumn purpose
        # ~ factory_purpose = Gtk.SignalListItemFactory()
        # ~ factory_purpose.connect("setup", self._on_factory_setup_purpose)
        # ~ factory_purpose.connect("bind", self._on_factory_bind_purpose)
        # ~ self.column_purpose = Gtk.ColumnViewColumn.new("Purpose", factory_purpose)
        # ~ self.column_purpose.set_sorter(self.view.prop_purpose_sorter)

        # ~ # Custom factory for ColumViewColumn SentTo
        # ~ factory_sentto = Gtk.SignalListItemFactory()
        # ~ factory_sentto.connect("setup", self._on_factory_setup_sentto)
        # ~ factory_sentto.connect("bind", self._on_factory_bind_sentto)
        # ~ self.column_sentto = Gtk.ColumnViewColumn.new("Sent to", factory_sentto)
        #self.column_sentto.set_sorter(self.view.prop_to_sorter)

         # ~ # Custom factory for ColumViewColumn to
        # ~ factory_date = Gtk.SignalListItemFactory()
        # ~ factory_date.connect("setup", self._on_factory_setup_date)
        # ~ factory_date.connect("bind", self._on_factory_bind_date)
        # ~ self.column_date = Gtk.ColumnViewColumn.new("Date", factory_date)
        #self.column_date.set_sorter(self.view.prop_date_sorter)

        # ~ # Custom factory for ColumViewColumn flag
        # ~ factory_flag = Gtk.SignalListItemFactory()
        # ~ factory_flag.connect("setup", self._on_factory_setup_flag)
        # ~ factory_flag.connect("bind", self._on_factory_bind_flag)
        # ~ self.column_flag = Gtk.ColumnViewColumn.new("Flag", factory_flag)
        # ~ self.column_flag.set_sorter(self.view.prop_country_sorter)

        self.view.cv.append_column(self.view.column_icon_type)
        self.view.cv.append_column(self.view.column_purpose)
        self.view.cv.append_column(self.view.column_sentby)
        self.view.cv.append_column(self.view.column_title)
        self.view.column_title.set_header_menu(self.mnuSelMulti)
        self.view.cv.append_column(self.view.column_subtitle)
        self.view.column_subtitle.set_header_menu(self.mnuSelMulti)
        self.view.cv.append_column(self.view.column_sentto)
        self.view.cv.append_column(self.view.column_date)
        self.view.cv.append_column(self.column_collection)
        self.view.cv.append_column(self.view.column_flag)
        self.view.cv.set_single_click_activate(False)
        # ~ view.cv.append_column(view.column_active)
        self.view.column_title.set_expand(True)
        self.view.column_subtitle.set_expand(True)
        self.view.cv.sort_by_column(self.view.column_title, Gtk.SortType.DESCENDING)
        self.view.set_filter(self._do_filter_view)
        self.view.select_first_item()
        frmView = self.factory.create_frame(hexpand=True, vexpand=True)
        frmView.set_child(self.view)
        return frmView

    # ~ def _setup_statusbar(self):
        # ~ statusbar = Gtk.Statusbar()
        # ~ self.sbcid = statusbar.get_context_id('MiAZ')
        # ~ return statusbar

    def _setup_statusbar(self):
        hbox = self.factory.create_box_horizontal(margin=0, hexpand=True)
        frm = self.factory.create_frame(margin=0, hexpand=True)
        self.infobar = Gtk.InfoBar()
        self.infobar.set_revealed(True)
        self.infobar.set_hexpand(True)
        self.infobar.set_show_close_button(False)
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        self.message_label = Gtk.Label()
        self.message_label.set_markup('There are still documents pending of review')
        boxEmpty = self.factory.create_box_horizontal(hexpand=True)
        hbox.append(self.message_label)
        hbox.append(boxEmpty)
        self.btnReview = self.factory.create_button('miaz-rename', callback=self.display_review)
        self.btnDashboard = self.factory.create_button('miaz-dashboard-ok', title='Back to the AZ', callback=self.display_dashboard)
        self.btnDashboard.set_visible(False)
        hbox.append(self.btnReview)
        hbox.append(self.btnDashboard)
        self.infobar.add_child(hbox)
        frm.set_child(self.infobar)
        # ~ self.infobar.connect('response', self.infobar_response)
        # ~ self.append(self.infobar)
        # ~ self.infobar_message()
        # ~ self.statusbar = Gtk.Statusbar()
        # ~ self.sbcid = self.statusbar.get_context_id('MiAZ')

        # ~
        self.spinner = Gtk.Spinner()
        # ~ self.spinner.set_spinning(True)
        # ~ hbox.append(self.infobar)
        # ~ hbox.append(boxEmpty)

        return frm

    def _setup_workspace(self):
        widget = self.factory.create_box_vertical(margin=0, spacing=6, hexpand=True, vexpand=True)
        head = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True)
        body = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        foot = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True)
        widget.append(head)
        widget.append(body)
        widget.append(foot)

        toolbar_top = self._setup_toolbar_top()
        self.toolbar_filters = self._setup_toolbar_filters()
        frmView = self._setup_columnview()
        self.statusbar = self._setup_statusbar()
        head.append(toolbar_top)
        head.append(self.toolbar_filters)
        body.append(frmView)
        foot.append(self.statusbar)

        if self.num_review == 0:
            self.statusbar.set_visible(False)

        # Connect signals
        selection = self.view.get_selection()

        # Trigger events
        self._on_signal_filter_connect()
        self._on_filters_toggled(self.tgbFilters)
        # ~ self.statusbar.push(self.sbcid, 'MiAZ')

        # ~ frmView.set_child(self.view)
        # ~ return frmView
        return widget

    def create_menu_selection_multiple(self):
        self.menu_workspace_multiple = Gio.Menu.new()
        # ~ {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}
        fields = [Country, Collection, SentBy, Purpose, Concept, SentTo]
        # ~ item_fake = Gio.MenuItem.new()
        # ~ item_fake.set_attribute_value('use-markup', GLib.Variant.new_boolean(True))
        # ~ icon = Gio.ThemedIcon.new('MiAZ')
        # ~ item_fake.set_icon(icon)
        # ~ item_fake.set_label('&lt;b&gt;Multiple selection&lt;/b&gt;')
        # ~ action = Gio.SimpleAction.new('fake', None)
        # ~ item_fake.set_detailed_action(detailed_action='fake')
        # ~ self.menu_workspace_multiple.append_item(item_fake)
        # ~ self.menu_workspace_multiple.append_item(MenuHeader("Multiple selection", 'MiAZ'))

        # Submenu for mass renaming
        submenu_rename_root = Gio.Menu.new()
        submenu_rename = Gio.MenuItem.new_submenu(
            label='Mass renaming of...',
            submenu=submenu_rename_root,
        )
        self.menu_workspace_multiple.append_item(submenu_rename)

        for item_type in fields:
            title = item_type.__gtype_name__
            menuitem = Gio.MenuItem.new()
            menuitem.set_label(label='... %s' % title.lower())
            action = Gio.SimpleAction.new('rename_%s' % title.lower(), None)
            callback = 'self._on_action_rename'
            action.connect('activate', eval(callback), item_type)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.rename_%s' % title.lower())
            submenu_rename_root.append_item(menuitem)

        # Submenu for mass adding
        # ~ submenu_add_root = Gio.Menu.new()
        # ~ submenu_add = Gio.MenuItem.new_submenu(
            # ~ label='Mass adding of...',
            # ~ submenu=submenu_add_root,
        # ~ )
        # ~ self.menu_workspace_multiple.append_item(submenu_add)

        # ~ for item in fields:
            # ~ menuitem = Gio.MenuItem.new()
            # ~ menuitem.set_label(label='... %s' % item)
            # ~ action = Gio.SimpleAction.new('add_%s' % item, None)
            # ~ callback = 'self.action_add'
            # ~ action.connect('activate', eval(callback), item)
            # ~ self.app.add_action(action)
            # ~ menuitem.set_detailed_action(detailed_action='app.add_%s' % item)
            # ~ submenu_add_root.append_item(menuitem)

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
        self.spinner_start()
        self._on_explain_toggled(self.tgbExplain)
        repocnf = self.backend.get_repo_source_config_file()
        self.repodct = json_load(repocnf)
        who = self.app.get_config('Person')
        items = []
        for path in self.repodct:
            # ~ self.log.debug(self.repodct[])
            valid = self.repodct[path]['valid']
            fields = self.repodct[path]['fields']
            try:
                adate = datetime.strptime(fields[0], "%Y%m%d")
                date_dsc = humanize.naturaldate(adate)
            except:
                date_dsc = ''
            items.append(File(  id=path,
                                date=fields[0],
                                date_dsc = date_dsc,
                                country=fields[1],
                                collection=fields[2],
                                purpose=fields[4],
                                sentby_id=fields[3],
                                sentby_dsc=who.get(fields[3]),
                                title=os.path.basename(path),
                                subtitle=fields[5],
                                sentto_id=fields[6],
                                sentto_dsc=who.get(fields[6]),
                                valid=valid))
        self.view.update(items)
        self._on_filter_selected()
        self.update_title()
        if self.show_dashboard:
            self.tgbExplain.set_active(True)
        self.lblDocumentsSelected = "0 of %d documents selected" % len(self.repodct)
        self.spinner_stop()

    # ~ def update_filters(self, item, ival):
        # ~ n = 0
        # ~ for field in ['date', 'country', 'collection', 'from', 'purpose', 'concept', 'to']:
            # ~ try:
                # ~ values = self.dfilter[field]
                # ~ values.add(ival[n])
            # ~ except Exception as error:
                # ~ values = set()
                # ~ values.add(ival[n])
                # ~ self.dfilter[field] = values
            # ~ n += 1

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
        if not item.valid:
            self.num_review += 1

        display = False
        if self.show_dashboard:
            if item.valid:
                c0 = self._do_eval_cond_matches_freetext(item.id)
                c1 = self._do_eval_cond_matches(self.dropdown['Country'], item.country)
                c2 = self._do_eval_cond_matches(self.dropdown['Collection'], item.collection)
                c3 = self._do_eval_cond_matches(self.dropdown['SentBy'], item.sentby_id)
                c4 = self._do_eval_cond_matches(self.dropdown['Purpose'], item.purpose)
                c6 = self._do_eval_cond_matches(self.dropdown['SentTo'], item.sentto_id)
                display = c0 and c1 and c2 and c3 and c4 and c6
        else:
            if not item.valid:
                display = self._do_eval_cond_matches_freetext(item.id)

        if display:
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
        self.num_review = 0
        self.dfilter = {}
        self.view.refilter()
        self.update_title()
        if self.num_review > 0:
            self.statusbar.set_visible(True)
        else:
            self.display_dashboard()
            self.statusbar.set_visible(False)

    def _on_select_all(self, *args):
        selection = self.view.get_selection()
        selection.select_all()

    def _on_select_none(self, *args):
        selection = self.view.get_selection()
        selection.unselect_all()

    def display_dashboard(self, *args):
        self.log.debug("Dashboard")
        self.displayed = 0
        self.num_review = 0
        self.dfilter = {}
        self.show_dashboard = True
        self.view.refilter()
        self.update_title()
        self.tgbExplain.set_active(True)
        self.tgbExplain.set_visible(True)
        self.tgbFilters.set_visible(True)
        if self.num_review > 0:
            self.statusbar.set_visible(True)
            self.message_label.set_markup('There are new documents pending of review')
            self.infobar.set_message_type(Gtk.MessageType.ERROR)
            self.btnReview.set_visible(True)
            self.btnDashboard.set_visible(False)
        else:
            self.statusbar.set_visible(True)

    def display_review(self, *args):
        self.log.debug("Review documents")
        self.displayed = 0
        self.dfilter = {}
        self.show_dashboard = False
        self.view.refilter()
        self.update_title()
        self.btnDashboard.set_visible(True)
        self.btnReview.set_visible(False)
        self.tgbExplain.set_active(False)
        self.tgbExplain.set_visible(False)
        self.tgbFilters.set_visible(False)
        self.statusbar.set_visible(True)
        self.message_label.set_markup('<b>Review finished?</b>')
        self.infobar.set_message_type(Gtk.MessageType.INFO)
        # ~ btnBack = self.infobar.add_button('Back to AZ', Gtk.ResponseType.CANCEL)


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
        item = self.get_item()
        self.actions.document_rename(item)

    def get_selected(self, *args):
        selection = self.get_selection()
        model = self.get_model_filter()
        selected = selection.get_selection()
        pos = selected.get_nth(0)
        item = model.get_item(pos)
        return item
