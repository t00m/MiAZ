#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil

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
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.row import MiAZFlowBoxRow


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
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
        self.ent_sb.connect('changed', self. on_change_search)
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
        self.btnDocsSel.set_sensitive(False)
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

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(5)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode (Gtk.SelectionMode.SINGLE)
        self.flowbox.set_filter_func(self.clb_visible_function)
        self.flowbox.set_sort_func(self.clb_sort_function)

        self.scrwin.set_child(self.flowbox)

        # Key events controller
        # ~ evk = Gtk.EventControllerKey.new()
        # ~ evk.connect("key-pressed", self.on_key_press)
        # ~ self.treeview.add_controller(evk)

    def on_key_press(self, event, keyval, keycode, state):
        self.log.debug("%s > %s > %s > %s", event, keyval, keycode, state)
        if keyval == Gdk.KEY_q: # and state & Gdk.ModifierType.CONTROL_MASK:   # Add Gdk to your imports. i.e. from gi import Gdk
            self.app.quit()
        elif keyval == Gdk.KEY_f:
            self.ent_sb.grab_focus()

    def update(self, *args):
        self.log.debug("Got signal 'target-configuration-updated'")
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        who = self.app.get_config('organizations')
        for filepath in repodct:
            dot = filepath.rfind('.')
            doc = filepath[:dot]
            ext = filepath[dot+1:]
            row = MiAZFlowBoxRow(self.app, filepath, repodct[filepath])
            self.flowbox.append(row)
        page = self.app.get_stack_page_by_name('workspace')
        page.set_badge_number(len(repodct))
        self.log.debug("Workspace ready!")

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

    def clb_visible_function(self, flowboxchild):
        row = flowboxchild.get_child()
        filepath = row.get_filepath()
        filedict = row.get_filedict()
        doc = os.path.basename(filepath)
        valid = filedict['valid']
        freefilter = self.ent_sb.get_text().upper() in filepath.upper()
        display = False
        if self.show_dashboard:
            if valid:
                if freefilter:
                    display = True
        else:
            if not valid:
                if freefilter:
                    display = True
        return display


        # ~ self.log.debug("%s - Valid[%s] Dashboard[%s] => Display[%s]", doc, valid, self.show_dashboard, display)
        if display:
            return True
        else:
            return False

    def clb_sort_function(self, flowboxchild1, flowboxchild2):
        row1 = flowboxchild1.get_child()
        row2 = flowboxchild2.get_child()
        value1 = row1.get_date()
        value2 = row2.get_date()
        # ~ self.log.debug("%s > %s", value1, value2)
        if value1 < value2:
            return 1
        elif value1 == value2:
            return 0
        else:
            return -1

    # ~ def clb_visible_function(self, model, itr, data):
        # ~ item_name = model.get(itr, 3)[0]
        # ~ row_type = model.get(itr, 6)[0]
        # ~ sbentry = self.app.get_searchbar_entry()
        # ~ filter_text = sbentry.get_text()

        # ~ if row_type == 'FOLDER' or row_type == 'REASON':
            # ~ return True

        # ~ match = filter_text.upper() in item_name.upper()

        # ~ if match:
            # ~ return True
        # ~ else:
            # ~ return False

    def on_key_released(self, widget, keyval, keycode, state):
        self.filter_view()
        # ~ keyname = Gdk.keyval_name(keyval)
        # ~ if Gdk.ModifierType.CONTROL_MASK & state and keyname == 'f':
        #       ....

    def on_row_activated(self, *args):
        self.log.debug(args)



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
        action = Gio.SimpleAction.new('rename_ws_manually', None)
        action.connect('activate', self.action_rename_manually)
        self.app.add_action(action)
        item_rename_manual.set_detailed_action(detailed_action='app.rename_ws_manually')
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


    def action_rename_manually(self, button, data):
        source = data
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        target = repodct[source]['suggested'].split('-')
        dialog = MiAZRenameDialog(self.app, source, target)
        dialog.connect('response', self.on_response_rename)
        dialog.show()

    def on_response_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            source = dialog.get_filepath_source()
            target = os.path.join(os.path.dirname(source), dialog.get_filepath_target())
            shutil.move(source, target)
            self.log.debug("Rename document from '%s' to '%s'", os.path.basename(source), os.path.basename(target))

    def on_double_click(self, treeview, treepath, treecolumn):
        treeiter = self.sorted_model.get_iter(treepath)
        filename = self.sorted_model[treeiter][0]
        repodir = self.app.get_config('app').get('source')
        filepath = os.path.join(repodir, filename)
        self.log.debug(filepath)
        if os.path.exists(filepath):
            os.system("xdg-open '%s'" % filepath)

    def action_rename(self, *args):
        self.log.debug(args)

    def action_add(self, *args):
        self.log.debug(args)

    def noop(self, *args):
        self.log.debug(args)

    def on_change_selection(self, selection):
        model, selected_rows = selection.get_selected_rows()
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
        dialog = self.factory.create_dialog(self.app.win, 'Rename file', Gtk.Label())
        dialog.show()

    def on_show_dashboard(self, *args):
        self.show_dashboard = True
        self.flowbox.invalidate_filter()

    def on_show_review(self, *args):
        self.show_dashboard = False
        self.flowbox.invalidate_filter()

    def on_change_search(self, *args):
        self.flowbox.invalidate_filter()


