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
from MiAZ.backend.util import json_load, json_save
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
    idr = {} # Internal Dictionary of rows
    update_mode = False

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

        self.create_menu_selection_single()
        self.create_menu_selection_multiple()
        toolbar = self.setup_toolbar()
        view = self.setup_view()
        self.append(toolbar)
        self.append(view)

    def setup_toolbar(self):
        # Toolbar
        toolbar = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        frmFilters = Gtk.Frame()
        frmFilters.set_margin_top(margin=3)
        frmFilters.set_margin_end(margin=3)
        frmFilters.set_margin_bottom(margin=3)
        frmFilters.set_margin_start(margin=3)
        frmFilters.set_hexpand(False)
        frmFilters.set_vexpand(False)
        lblFrameTitle = self.factory.create_label('<big><b>Filters</b></big>')
        frmFilters.set_label_widget(lblFrameTitle)
        frmFilters.set_label_align(0.5)

        tlbFilters = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        tlbFilters.set_margin_top(margin=6)
        tlbFilters.set_margin_end(margin=6)
        tlbFilters.set_margin_bottom(margin=6)
        tlbFilters.set_margin_start(margin=6)
        tlbFilters.set_hexpand(False)
        tlbFilters.set_vexpand(False)

        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        self.ent_sb.connect('changed', self. on_filter_selected)
        box = self.factory.create_box_filter('Free search', self.ent_sb)
        tlbFilters.append(box)

        self.cmbCountries = self.factory.create_combobox_countries()
        self.cmbCountries.connect('changed', self.on_filter_selected)
        box = self.factory.create_box_filter('Country', self.cmbCountries)
        tlbFilters.append(box)

        self.cmbCollections = self.factory.create_combobox_text('collections')
        self.cmbCollections.connect('changed', self.on_filter_selected)
        box = self.factory.create_box_filter('Collection', self.cmbCollections)
        tlbFilters.append(box)

        self.cmbFrom = self.factory.create_combobox_text_from()
        self.cmbFrom.connect('changed', self.on_filter_selected)
        box = self.factory.create_box_filter('From', self.cmbFrom)
        tlbFilters.append(box)

        self.cmbPurposes = self.factory.create_combobox_text('purposes')
        self.cmbPurposes.connect('changed', self.on_filter_selected)
        box = self.factory.create_box_filter('Purpose', self.cmbPurposes)
        tlbFilters.append(box)

        self.cmbTo = self.factory.create_combobox_text_to()
        self.cmbTo.connect('changed', self.on_filter_selected)
        box = self.factory.create_box_filter('To', self.cmbTo)
        tlbFilters.append(box)

        frmFilters.set_child(tlbFilters)
        toolbar.append(frmFilters)

        frmReview = Gtk.Frame()
        frmReview.set_margin_top(margin=3)
        frmReview.set_margin_end(margin=3)
        frmReview.set_margin_bottom(margin=3)
        frmReview.set_margin_start(margin=3)
        frmReview.set_hexpand(False)
        frmReview.set_vexpand(True)
        # ~ lblFrameTitle = self.factory.create_label('<big><b>Filters</b></big>')
        # ~ frmReview.set_label_widget(lblFrameTitle)
        # ~ frmReview.set_label_align(0.5)
        status = Adw.StatusPage()
        # ~ status.set_icon_name('miaz-mime-exec')
        status.set_title('Warning!')
        status.get_style_context().add_class(class_name='error')
        status.set_description('There are  documents pending of review')
        btnCheck = self.factory.create_button('miaz-mime-exec', 'Check now!', self.on_show_review)
        status.set_child(btnCheck)
        # ~ label = self.factory.create_label('Hola!')
        # ~ status.set_child(label)

        frmReview.set_child(status)
        toolbar.append(frmReview)

        self.backend.connect('source-configuration-updated', self.update)
        return toolbar

    def setup_view_toolbar(self):
        boxViewToolbar = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        frmToolbar = Gtk.Frame()
        frmToolbar.set_margin_top(margin=3)
        frmToolbar.set_margin_end(margin=3)
        frmToolbar.set_margin_bottom(margin=3)
        frmToolbar.set_margin_start(margin=3)
        btnBack = self.factory.create_button('miaz-ok', 'Back')
        boxToolbar = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        boxToolbar.append(btnBack)
        frmToolbar.set_child(boxToolbar)
        boxViewToolbar.append(frmToolbar)
        return boxViewToolbar

    def setup_view_body(self):
        boxViewBody = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        frmViewBody = Gtk.Frame()
        frmViewBody.set_margin_top(margin=3)
        frmViewBody.set_margin_end(margin=3)
        frmViewBody.set_margin_bottom(margin=3)
        frmViewBody.set_margin_start(margin=3)
        boxViewBody.append(frmViewBody)
        scrwin = Gtk.ScrolledWindow()
        scrwin.set_vexpand(True)
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_margin_top(margin=3)
        self.flowbox.set_margin_end(margin=3)
        self.flowbox.set_margin_bottom(margin=3)
        self.flowbox.set_margin_start(margin=3)
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(1)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode (Gtk.SelectionMode.SINGLE)
        self.flowbox.set_filter_func(self.clb_visible_function)
        self.flowbox.set_sort_func(self.clb_sort_function)
        scrwin.set_child(self.flowbox)
        frmViewBody.set_child(scrwin)
        return boxViewBody

    def setup_view(self):
        boxView = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        boxViewToolbar = self.setup_view_toolbar()
        boxViewBody = self.setup_view_body()

        boxView.append(boxViewToolbar)
        boxView.append(boxViewBody)

        return boxView


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
        self.flowbox.invalidate_filter()
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        who = self.app.get_config('organizations')
        for filepath in repodct:
            try:
                row = self.idr[filepath]
            except Exception as error:
                dot = filepath.rfind('.')
                doc = filepath[:dot]
                ext = filepath[dot+1:]
                row = MiAZFlowBoxRow(self.app, filepath, repodct[filepath])
                self.flowbox.append(row)
                self.idr[filepath] = row
                self.update_title()
                # ~ self.log.debug("F[%s] <<===| R[%s]", filepath, row)
        # ~ page = self.app.get_stack_page_by_name('workspace')
        # ~ page.set_badge_number(len(repodct))
        self.log.debug("Workspace ready!")

    def update_title(self):
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        header = self.app.get_header()
        title = header.get_title_widget()
        if title is not None:
            header.remove(title)
        wdgTitle = Adw.WindowTitle()
        wdgTitle.set_title('MiAZ')
        wdgTitle.set_subtitle("Displaying %d of %d documents" % (self.displayed, len(repodct)))
        header.set_title_widget(wdgTitle)

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

    def cond_matches_freetext(self, row):
        filepath = row.get_filepath()
        fileanot = row.get_explain()
        left = self.ent_sb.get_text()
        right = filepath+fileanot
        if left.upper() in right.upper():
            return True
        return False

    def cond_matches_country(self, code_row):
        treeiter = self.cmbCountries.get_active_iter()
        model = self.cmbCountries.get_model()
        code_chosen = model[treeiter][1]
        if len(code_chosen) == 0:
            return True
        return code_chosen == code_row

    def cond_matches_collection(self, code_row):
        treeiter = self.cmbCollections.get_active_iter()
        model = self.cmbCollections.get_model()
        code_chosen = model[treeiter][0]
        if len(code_chosen) == 0:
            return True
        return code_chosen == code_row

    def cond_matches_from(self, code_row):
        treeiter = self.cmbFrom.get_active_iter()
        model = self.cmbFrom.get_model()
        code_chosen = model[treeiter][0]
        if len(code_chosen) == 0:
            return True
        return code_chosen == code_row

    def cond_matches_purposes(self, code_row):
        treeiter = self.cmbPurposes.get_active_iter()
        model = self.cmbPurposes.get_model()
        code_chosen = model[treeiter][0]
        if len(code_chosen) == 0:
            return True
        return code_chosen == code_row

    def cond_matches_to(self, code_row):
        treeiter = self.cmbTo.get_active_iter()
        model = self.cmbTo.get_model()
        code_chosen = model[treeiter][0]
        if len(code_chosen) == 0:
            return True
        return code_chosen == code_row

    def clb_visible_function(self, flowboxchild):
        row = flowboxchild.get_child()
        filepath = row.get_filepath()
        filedict = row.get_filedict()
        valid = filedict['valid']

        display = False
        if self.show_dashboard:
            if valid:
                c0 = self.cond_matches_freetext(row)
                c1 = self.cond_matches_country(filedict['fields'][1])
                c2 = self.cond_matches_collection(filedict['fields'][2])
                c3 = self.cond_matches_from(filedict['fields'][3])
                c4 = self.cond_matches_purposes(filedict['fields'][4])
                c6 = self.cond_matches_to(filedict['fields'][6])
                display = c0 and c1 and c2 and c3 and c4 and c6
        else:
            if not valid:
                display = self.cond_matches_freetext(row)

        if display:
            self.displayed += 1

        return display

    def clb_sort_function(self, flowboxchild1, flowboxchild2):
        row1 = flowboxchild1.get_child()
        row2 = flowboxchild2.get_child()
        value1 = row1.get_date()
        value2 = row2.get_date()
        if value1 < value2:
            return 1
        elif value1 == value2:
            return 0
        else:
            return -1

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
        row = data
        source = row.get_filepath()
        repocnf = self.backend.get_repo_source_config_file()
        repodct = json_load(repocnf)
        target = repodct[source]['suggested'].split('-')
        dialog = MiAZRenameDialog(self.app, row, source, target)
        dialog.connect('response', self.on_response_rename)
        dialog.show()

    def on_response_rename(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            row = dialog.get_row()
            source = dialog.get_filepath_source()
            target = os.path.join(os.path.dirname(source), dialog.get_filepath_target())
            # Before renaming, check all fields and add values to
            # configuration files if they are missing
            basename = os.path.basename(target)
            doc = basename[:basename.rfind('.')]
            fields = doc.split('-')
            collection = fields[2]
            org_from = fields[3]
            purpose = fields[4]
            concept = fields[5]
            org_to = fields[6]

            cnf_col = self.app.get_config('collections')
            cnf_who = self.app.get_config('organizations')
            cnf_pur = self.app.get_config('purposes')
            cnf_cpt = self.app.get_config('concepts')

            if not cnf_col.exists(collection) and len(collection) > 0:
                cnf_col.list_add(collection)

            if not cnf_pur.exists(purpose) and len(purpose) > 0:
                cnf_pur.list_add(purpose)

            if not cnf_cpt.exists(concept) and len(concept) > 0:
                cnf_cpt.list_add(concept)

            if not cnf_who.exists(org_from) and len(org_from) > 0:
                cnf_who.dict_add(org_from, '')

            if not cnf_who.exists(org_to) and len(org_to) > 0:
                cnf_who.dict_add(org_to, '')

            # Then, rename it:
            shutil.move(source, target)
            self.log.debug("Rename document from '%s' to '%s'", os.path.basename(source), os.path.basename(target))
            self.flowbox.remove(row)
            del(self.idr[source])
            s_repocnf = self.backend.get_repo_source_config_file()
            s_repodct = json_load(s_repocnf)
            valid, reasons = self.backend.validate_filename(target)
            s_repodct[target] = {}
            s_repodct[target]['valid'] = valid
            s_repodct[target]['reasons'] = reasons
            if not valid:
                s_repodct[target]['suggested'] = self.backend.suggest_filename(target)
            else:
                s_repodct[target]['suggested'] = None
                s_repodct[target]['fields'] = self.backend.get_fields(target)
            json_save(s_repocnf, s_repodct)
            self.log.debug("Source repository - Emitting signal 'source-configuration-updated'")
            self.backend.emit('source-configuration-updated')


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

    # ~ def on_rename_file(self, *args):
        # ~ dialog = self.factory.create_dialog(self.app.win, 'Rename file', Gtk.Label())
        # ~ dialog.show()

    def on_show_dashboard(self, *args):
        self.displayed = 0
        self.show_dashboard = True
        self.flowbox.invalidate_filter()
        self.update_title()

    def on_show_review(self, *args):
        self.displayed = 0
        self.show_dashboard = False
        self.flowbox.invalidate_filter()
        self.update_title()

    def on_filter_selected(self, *args):
        self.displayed = 0
        self.flowbox.invalidate_filter()
        self.update_title()
