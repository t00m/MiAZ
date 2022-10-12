#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil

import gi
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.util import json_load
from MiAZ.backend.util import fuzzy_date_from_timestamp
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.widgets.treeview import MiAZTreeView
from MiAZ.backend.config.settings import MiAZConfigSettingsExtensions as Ext
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog


class MiAZDocBrowser(Gtk.Box):
    """ MiAZ Doc Browser Widget"""

    def __init__(self, app):
        super(MiAZDocBrowser, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZDocBrowser')
        self.app = app
        self.backend = self.app.get_backend()
        self.config = self.app.get_config('app')
        self.set_vexpand(True)

        self.setup_toolbar()
        self.setup_view()
        self.setup_stack()
        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}

    def setup_stack(self):
        self.stack = Adw.ViewStack()
        self.append(self.stack)

        page = self.stack.add_named(self.scrwin, 'view-list')
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

        boxDocsSelected = Gtk.CenterBox()
        self.lblDocumentsSelected = "No documents selected"
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_label(self.lblDocumentsSelected)
        self.popDocsSel = Gtk.PopoverMenu.new_from_model(self.create_menu_selection_single())
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_valign(Gtk.Align.CENTER)
        self.btnDocsSel.set_hexpand(False)
        self.btnDocsSel.set_sensitive(False)
        boxDocsSelected.set_center_widget(self.btnDocsSel)
        boxViews.append(boxDocsSelected)
        toolbar.set_end_widget(boxViews)


        # ~ toolbar.set_end_widget(boxDocsSelected)


        frame.set_child(toolbar)
        self.append(frame)

        self.controller = Gtk.EventControllerKey()
        self.controller.connect('key-released', self.on_key_released)
        self.add_controller(self.controller)

        self.backend.connect('target-configuration-updated', self.update)

    def action_rename_manually(self, *args):
        row = self.listbox.get_selected_row()
        basename = row.get_subtitle()
        config = self.app.get_config('app')
        source = os.path.join(config.get('target'), basename)
        doc = basename[:basename.rfind('.')]
        target = doc.split('-')
        dialog = MiAZRenameDialog(self.app, source, target)
        dialog.connect('response', self.on_response_rename)
        dialog.show()

    def create_menu_selection_single(self) -> Gio.Menu:
        self.menu_workspace_single = Gio.Menu.new()

        # Fake item for menu title
        item_fake = Gio.MenuItem.new()
        item_fake.set_label('Single selection')
        action = Gio.SimpleAction.new('fake', None)
        item_fake.set_detailed_action(detailed_action='fake')
        self.menu_workspace_single.append_item(item_fake)

        item_rename_manual = Gio.MenuItem.new()
        item_rename_manual.set_label('Rename manually')
        action = Gio.SimpleAction.new('rename_db_manually', None)
        action.connect('activate', self.action_rename_manually)
        self.app.add_action(action)
        item_rename_manual.set_detailed_action(detailed_action='app.rename_db_manually')
        self.menu_workspace_single.append_item(item_rename_manual)

        return self.menu_workspace_single

    def noop(self, *args):
        self.log.debug(args)

    def show_view_list(self, *args):
        self.stack.set_visible_child_name('view-list')

    def show_view_grid(self, *args):
        self.stack.set_visible_child_name('view-grid')

    def show_view_tree(self, *args):
        self.stack.set_visible_child_name('view-tree')

    def setup_view(self):
        self.scrwin = Gtk.ScrolledWindow()
        self.scrwin.set_has_frame(False)
        self.scrwin.set_vexpand(True)
        self.listbox = Gtk.ListBox.new()
        self.listbox.set_show_separators(True)
        self.listbox.set_selection_mode(mode=Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_margin_top(margin=0)
        self.listbox.set_margin_end(margin=6)
        self.listbox.set_margin_bottom(margin=6)
        self.listbox.set_margin_start(margin=6)
        self.listbox.get_style_context().add_class(class_name='boxed-list')
        self.listbox.set_filter_func(self.clb_visible_function)
        self.listbox.connect('selected-rows-changed', self.on_selected_rows_changed)
        self.listbox.connect('row-selected', self.on_row_selected)

        # Row for displaying when there is no documents available
        self.nodata = Adw.ActionRow.new()
        self.nodata.set_title(title='<b>No documents found for review</b>')
        self.listbox.set_placeholder(self.nodata)
        self.scrwin.set_child(self.listbox)

    def on_selected_rows_changed(self, listbox):
        selected_rows = listbox.get_selected_rows()
        # ~ self.log.debug("Selected rows: %d", len(selected_rows))
        if len(selected_rows) > 1:
            self.btnDocsSel.set_label("%d documents selected" % len(selected_rows))
            self.popDocsSel.set_menu_model(self.menu_workspace_multiple)
            self.btnDocsSel.set_sensitive(True)
        elif len(selected_rows) == 1:
            self.btnDocsSel.set_label("%d documents selected" % len(selected_rows))
            self.popDocsSel.set_menu_model(self.menu_workspace_single)
            self.btnDocsSel.set_sensitive(True)
        else:
            self.btnDocsSel.set_label("No documents selected")
            self.popDocsSel.set_menu_model(None)
            self.btnDocsSel.set_sensitive(False)

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

    def update(self, *args):
        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}
        self.log.debug("Got signal 'target-configuration-updated'")
        repocnf = self.backend.get_repo_target_config_file()
        repodct = json_load(repocnf)
        who = self.app.get_config('organizations')
        for filepath in repodct:
            dot = filepath.rfind('.')
            doc = filepath[:dot]
            ext = filepath[dot+1:]
            row = Adw.ActionRow.new()
            # ~ row.connect('activated', self.on_row_activated, filepath)
            # ~ row.connect('activate', self.on_row_activated, filepath)
            fields = doc.split('-')
            explain = "<span color='blue'>#%s</span> <b>%s from %s about %s to %s</b>" % (fields[2], fields[4].title(), who.get(fields[3]), fields[5], who.get(fields[6]))
            row.set_title(title=explain)
            row.set_subtitle(subtitle=filepath)

            icon = self.app.icman.get_icon_mimetype_from_file(filepath, 48, 48)
            icon.set_icon_size(Gtk.IconSize.LARGE)
            boxPrefix = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            # ~ btnFileDisplay = button = Gtk.Button()
            # ~ btnFileDisplay.set_child(icon)
            # ~ btnFileDisplay.connect('clicked', self.on_display_document, filepath)
            # ~ btnFileDisplay.set_valign(Gtk.Align.CENTER)
            # ~ btnFileDisplay.set_hexpand(False)
            flag = self.app.icman.get_flag(fields[1], 48, 48)
            boxPrefix.append(flag)
            boxPrefix.append(icon)
            row.add_prefix(boxPrefix)


            # ~ row.add_prefix(flag)
            fuzzy_date = Gtk.Label()
            fuzzy_date.set_markup(fuzzy_date_from_timestamp(fields[0]))
            row.add_suffix(fuzzy_date)
            # ~ row.get_style_context().add_class(class_name='error')

            # ~ subrow = self.app.create_button('miaz-mime-web', 'Link to this resource', None, data=row)
            # ~ row.add_row(subrow)
            self.listbox.append(child=row)
        self.do_needs_attention()

    def on_display_document(self, button, filepath):
        os.system("xdg-open '%s'" % filepath)

    def on_key_released(self, widget, keyval, keycode, state):
        self.filter_view()
        # ~ keyname = Gdk.keyval_name(keyval)
        # ~ if Gdk.ModifierType.CONTROL_MASK & state and keyname == 'f':
        #       ....

    def on_response_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            source = dialog.get_filepath_source()
            target = os.path.join(os.path.dirname(source), dialog.get_filepath_target())
            shutil.move(source, target)
            self.log.debug("Rename document from '%s' to '%s'", os.path.basename(source), os.path.basename(target))

    def on_row_selected(self, listbox, row):
        self.log.debug("On row selected: %s", row.get_subtitle())


    def doesnt_need_attention(self, *args):
        page = self.app.get_stack_page_by_name('browser')
        page.set_needs_attention(False)

    def do_needs_attention(self, *args):
        page = self.app.get_stack_page_by_name('browser')
        page.set_needs_attention(True)
