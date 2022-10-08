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

        self.create_menu_selection_single()
        self.create_menu_selection_multiple()
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

        # Documents selected
        boxDocsSelected = Gtk.CenterBox()
        self.lblDocumentsSelected = "No documents selected"
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_label(self.lblDocumentsSelected)
        self.popDocsSel = Gtk.PopoverMenu.new_from_model(self.create_menu_selection_multiple())
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_valign(Gtk.Align.CENTER)
        self.btnDocsSel.set_hexpand(False)
        boxDocsSelected.set_center_widget(self.btnDocsSel)
        toolbar.set_end_widget(boxDocsSelected)

        # Views (right side)
        # ~ boxMassActionsButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # ~ self.btnMassActions = Gtk.MenuButton()
        # ~ self.btnMassActions.set_label('Mass actions')
        # ~ self.btnMassActions.set_sensitive(False)
        # ~ self.btnMassActions.set_icon_name('miaz-rename')
        # ~ popover = Gtk.PopoverMenu.new_from_model(self.create_menu_selection_multiple())
        # ~ self.btnMassActions.set_popover(popover=popover)
        # ~ self.btnMassActions.set_valign(Gtk.Align.CENTER)
        # ~ self.btnMassActions.set_hexpand(False)
        # ~ boxMassActionsButton.append(self.btnMassActions)
        # ~ toolbar.set_end_widget(boxMassActionsButton)
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
        self.listbox.connect('selected-rows-changed', self.on_selected_rows_changed)
        self.listbox.set_show_separators(False)
        self.listbox.set_selection_mode(mode=Gtk.SelectionMode.MULTIPLE)
        self.listbox.set_activate_on_single_click(False)
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
        self.clear()
        self.log.debug("Got signal 'target-configuration-updated'")
        repocnf = self.backend.get_repo_source_config_file()
        self.repodct = json_load(repocnf)
        for filepath in self.repodct:
            dot = filepath.rfind('.')
            doc = filepath[:dot]
            ext = filepath[dot+1:]
            icon = self.app.icman.get_icon_mimetype_from_file(filepath, 36, 36)
            icon.set_icon_size(Gtk.IconSize.INHERIT)
            row = Adw.ActionRow.new()

            boxFileDisplayButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            btnFileDisplay = button = Gtk.Button()
            btnFileDisplay.set_child(icon)
            btnFileDisplay.connect('clicked', self.on_display_document, filepath)
            btnFileDisplay.set_valign(Gtk.Align.CENTER)
            btnFileDisplay.set_hexpand(False)
            row.add_prefix(btnFileDisplay)

            boxButtons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['linked'])
            boxFileInfoButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            btnFileInfo = Gtk.MenuButton()
            btnFileInfo.set_icon_name('miaz-reasons-info')
            popover = self.__create_popover_fileinfo(filepath)
            btnFileInfo.set_popover(popover)
            btnFileInfo.set_valign(Gtk.Align.CENTER)
            btnFileInfo.set_hexpand(False)

            # ~ boxFileSelectButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            # ~ btnFileSelect = Gtk.ToggleButton()
            # ~ btnFileSelect.connect('toggled', self.on_selected_rows_changed)
            # ~ btnFileSelect.set_icon_name('miaz-edit')
            # ~ btnFileSelect.set_valign(Gtk.Align.CENTER)
            # ~ btnFileSelect.set_hexpand(False)


            # ~ boxFileEditButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            # ~ btnFileEdit = Gtk.MenuButton()
            # ~ btnFileEdit.set_icon_name('miaz-rename')
            # ~ popover = Gtk.PopoverMenu.new_from_model(self.create_menu_selection_single(filepath))
            # ~ btnFileEdit.set_popover(popover=popover)
            # ~ btnFileEdit.set_valign(Gtk.Align.CENTER)
            # ~ btnFileEdit.set_hexpand(False)

            boxButtons.append(btnFileInfo)
            # ~ boxButtons.append(btnFileSelect)
            # ~ boxButtons.append(btnFileEdit)
            # ~ boxRow = row.get_child()
            # ~ boxRow.append(boxButtons)

            row.set_title(title="<b>%s</b>" % os.path.basename(doc))
            row.set_subtitle(subtitle=filepath)
            row.add_suffix(boxButtons)

            self.listbox.append(child=row)
        page = self.app.get_stack_page_by_name('workspace')
        page.set_badge_number(len(self.repodct))

    def __show_file_info(self, button, filepath):
        # ~ self.log.debug(args)
        treeview = self.__create_trvreasons(filepath)
        popover = Gtk.Popover()
        popover.set_child(treeview)
        popover.show()

    def __create_popover_fileinfo(self, filepath):
        # ~ self.log.debug(args)
        treeview = self.__create_trvreasons(filepath)
        popover = Gtk.Popover()
        popover.set_child(treeview)
        return popover

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

    def __create_trvreasons(self, filepath):
        # ~ scrreasons = Gtk.ScrolledWindow()
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
        icon_ko = self.app.icman.get_pixbuf_by_name('miaz-ko', 32)
        icon_ok = self.app.icman.get_pixbuf_by_name('miaz-ok', 32)

        for reason in self.repodct[filepath]['reasons']:
            passed, message = reason
            if passed:
                model.insert_with_values(-1, (0, 1), (icon_ok, message))
            else:
                model.insert_with_values(-1, (0, 1), (icon_ko, message))
        trvreasons.set_model(model)
        return trvreasons
        # ~ scrreasons.set_child(trvreasons)
        # ~ scrreasons.set_min_content_height(240)
        # ~ self.log.debug(height)
        # ~ scrreasons.set_vexpand(True)
        # ~ scrreasons.set_propagate_natural_height(True)


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
        action = Gio.SimpleAction.new('rename_manually', None)
        action.connect('activate', self.action_rename_manually)
        self.app.add_action(action)
        item_rename_manual.set_detailed_action(detailed_action='app.rename_manually')
        self.menu_workspace_single.append_item(item_rename_manual)

        return self.menu_workspace_single

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
            action.connect('activate', eval(callback), item)
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
            action.connect('activate', eval(callback), item)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.add_%s' % item)
            submenu_add_root.append_item(menuitem)

        item_force_update = Gio.MenuItem.new()
        item_force_update.set_label(label='Force update')
        action = Gio.SimpleAction.new('workspace_update', None)
        action.connect('activate', self.update)
        self.app.add_action(action)
        item_force_update.set_detailed_action(detailed_action='app.workspace_update')
        self.menu_workspace_multiple.append_item(item_force_update)

        item_delete = Gio.MenuItem.new()
        item_delete.set_label(label='Delete documents')
        action = Gio.SimpleAction.new('workspace_delete', None)
        action.connect('activate', self.noop)
        self.app.add_action(action)
        item_delete.set_detailed_action(detailed_action='app.workspace_delete')
        self.menu_workspace_multiple.append_item(item_delete)
        return self.menu_workspace_multiple


    def action_rename_manually(self, *args):
        # Filename format: {timestamp}-{country}-{collection}-{from}-{purpose}-{concept}-{to}.{extension}
        fields = ['date', 'country', 'collection', 'from', 'purpose', 'concept', 'to']

        row = self.listbox.get_selected_row()
        filepath = row.get_subtitle()
        doc = os.path.basename(filepath)
        suggested = self.repodct[filepath]['suggested'].split('-')
        self.log.debug(suggested)

        boxMain = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        boxFields = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        boxFields.set_margin_top(margin=6)
        boxFields.set_margin_end(margin=6)
        boxFields.set_margin_bottom(margin=6)
        boxFields.set_margin_start(margin=6)
        n = 0
        for item in fields:
            box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            box.set_hexpand(False)
            label = Gtk.Label()
            label.set_markup('<b>%s</b>' % item.title())
            label.set_xalign(0.0)
            box.append(label)
            entry = Gtk.Entry()
            entry.set_has_frame(True)
            entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'miaz-res-%s' % item)
            entry.set_text(suggested[n])
            box.append(entry)
            boxFields.append(box)
            n += 1

        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(False)
        label = Gtk.Label()
        label.set_markup('<b>Extension</b>')
        label.set_xalign(0.0)
        box.append(label)
        ext = filepath[filepath.rfind('.')+1:]
        lblExt = Gtk.Label()
        lblExt.set_text('.%s' % ext)
        lblExt.set_xalign(0.0)
        lblExt.set_yalign(0.5)
        lblExt.set_vexpand(True)
        box.append(lblExt)
        boxFields.append(box)

        self.lblSuggestedFilename = Gtk.Label()
        self.lblSuggestedFilename.set_markup("<i>Suggested filename: </i>%s.%s" % ('-'.join(suggested), ext))
        self.lblSuggestedFilename.set_selectable(True)

        boxMain.append(boxFields)
        boxMain.append(self.lblSuggestedFilename)

        dialog = self.app.create_dialog(self.app.win, 'Renaming %s' % doc, boxMain, -1, -1)
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        btnAccept = dialog.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        btnAccept.get_style_context().add_class(class_name='success')
        btnCancel = dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        btnCancel.get_style_context().add_class(class_name='error')
        dialog.show()

    def action_rename(self, *args):
        self.log.debug(args)

    def action_add(self, *args):
        self.log.debug(args)

    def noop(self, *args):
        self.log.debug(args)

    def clear(self, *args):
        rows = []
        for row in self.listbox:
            rows.append(row)
        for row in rows:
            self.listbox.remove(row)

    def on_selected_rows_changed(self, listbox):
        selected_rows = listbox.get_selected_rows()

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

    def on_display_document(self, button, filepath):
        os.system("xdg-open '%s'" % filepath)

    def on_rename_file(self, *args):
        dialog = self.app.create_dialog(self.app.win, 'Rename file', Gtk.Label())
        dialog.show()