#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
# ~ from MiAZ.backend.util import json_load
# ~ from MiAZ.backend.util import get_filename_details
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, ColIcon, ColLabel
from MiAZ.frontend.desktop.factory import MenuHeader
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepoSettings
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.menu import MiAZ_MENU_WORKSPACE_REPO
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewWorkspace, MiAZColumnViewMassRename

# Conversion Item type to Field Number
Field = {}
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True
    displayed = 0
    switched = set()
    dfilter = {}
    signals = set()
    num_review = 0
    selected_items = []

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
        self.config = self.backend.conf
        self.util = self.backend.util
        self.set_vexpand(False)
        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        frmView = self._setup_workspace()
        self.append(frmView)

        conf = self.config['Country']
        countries = conf.load(conf.used)
        if len(countries) == 0:
            self.log.debug("Execute Country Selector Assistant")
            assistant = MiAZAssistantRepoSettings(self.app)
            assistant.set_transient_for(self.app.win)
            assistant.set_modal(True)
            assistant.present()

    def _on_import_directory(self, *args):
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Import a directory',
                    target = 'FOLDER',
                    callback = self.actions.add_directory_to_repo
                    )
        filechooser.show()

    def _on_import_file(self, *args):
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Import a single file',
                    target = 'FILE',
                    callback = self.actions.add_file_to_repo
                    )
        filechooser.show()

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
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            title = item_type.__gtype_name__
            dropdown = self.factory.create_dropdown_generic(item_type)
            self.actions.dropdown_populate(dropdown, item_type)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            # ~ self.signals.add ((dropdown, sigid))
            boxDropdown = self.factory.create_box_filter(title, dropdown)
            body.append(boxDropdown)
            self.dropdown[title] = dropdown
            # ~ name = item_type.__gtype_name__
            # ~ config = self.config[name].connect('repo-settings-updated-countries', self.update_countries)
        self.backend.connect('source-configuration-updated', self.update)
        self.config['Country'].connect('repo-settings-updated-countries-used', self.update_dropdown, Country)
        self.config['Group'].connect('repo-settings-updated-groups-used', self.update_dropdown, Group)
        self.config['SentBy'].connect('repo-settings-updated-sentby', self.update_dropdown, SentBy)
        self.config['Purpose'].connect('repo-settings-updated-purposes', self.update_dropdown, Purpose)
        self.config['SentTo'].connect('repo-settings-updated-sentto', self.update_dropdown, SentTo)
        return widget

    def enable_filtering(self, enable=True):
        if enable:
            self.view.set_filter(self._do_filter_view)
        else:
            self.view.set_filter(None)

    def update_dropdown(self, config, item_type):
        title = item_type.__gtype_name__
        self.enable_filtering(False)
        self.actions.dropdown_populate(self.dropdown[title], item_type)
        self.enable_filtering(True)


    def _on_action_rename(self, action, data, item_type):
        title = item_type.__gtype_name__
        self.log.debug("Rename %s for:", title)
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(self.selected_items), title))
        dropdown = self.factory.create_dropdown_generic(item_type)
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        dropdown.connect("notify::selected-item", self._on_mass_renaming_change, cv, item_type)
        self.actions.dropdown_populate(dropdown, item_type, any_value=False)
        frame.set_child(cv)
        box.append(label)
        box.append(dropdown)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=1024, height=600)
        dialog.connect('response', self._on_mass_renaming, dropdown, item_type)
        dialog.show()

    def _on_mass_renaming_change(self, dropdown, item, columnview, item_type):
        title = item_type.__gtype_name__
        citems = []
        for item in self.selected_items:
            source = item.id
            self.log.debug("Renaming: %s", source)
            name, ext = self.util.get_filename_details(source)
            self.log.debug("N[%s] E[%s]", name, ext)
            n = Field[item_type]
            self.log.debug("Field to change: %d (%s)", n, title)
            tmpfile = name.split('-')
            tmpfile[n] = dropdown.get_selected_item().id
            self.log.debug("Built raw name: %s", tmpfile)
            filename = "%s.%s" % ('-'.join(tmpfile), ext)
            self.log.debug("Target name: %s", filename)
            target = os.path.join(os.path.dirname(source), filename)
            self.log.debug("Target filepath: %s", target)
            txtId = "<small>%s</small>" % os.path.basename(source)
            txtTitle = "<small>%s</small>" % os.path.basename(target)
            citems.append(File(id=txtId, title=txtTitle))
            # ~ self.log.debug("Mass %s renaming: %s > %s", title, os.path.basename(source) , os.path.basename(target))
        columnview.update(citems)


    def _on_mass_renaming(self, dialog, response, dropdown, item_type):
        # ~ util = self.backend.get_util()
        title = item_type.__gtype_name__
        if response == Gtk.ResponseType.ACCEPT:
            for item in self.selected_items:
                source = item.id
                name, ext = self.util.get_filename_details(source)
                n = Field[item_type]
                tmpfile = name.split('-')
                tmpfile[n] = dropdown.get_selected_item().id
                filename = "%s.%s" % ('-'.join(tmpfile), ext)
                target = os.path.join(os.path.dirname(source), filename)
                shutil.move(source, target)
                self.log.debug("Mass %s renaming: %s > %s", title, os.path.basename(source) , os.path.basename(target))
        dialog.destroy()


    def _on_explain_toggled(self, button, data=None):
        active = button.get_active()
        self.view.column_title.set_visible(not active)
        try:
            self.view.column_subtitle.set_visible(active)
            self.view.column_subtitle.set_expand(True)
            self.view.column_group.set_visible(active)
            self.view.column_purpose.set_visible(active)
            self.view.column_flag.set_visible(active)
            self.view.column_sentby.set_visible(active)
            self.view.column_sentto.set_visible(active)
            self.view.column_date.set_visible(active)
        except:
            pass

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

        ## Import buttons
        listbox = Gtk.ListBox.new()
        listbox.set_activate_on_single_click(False)
        listbox.unselect_all()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        vbox = self.factory.create_box_vertical()
        vbox.append(child=listbox)
        btnImportFiles = self.factory.create_button('miaz-import-document', callback=self._on_import_file)
        rowImportDoc = self.factory.create_actionrow(title='Import document', subtitle='Import one or more documents', suffix=btnImportFiles)
        listbox.append(child=rowImportDoc)
        btnImportDir = self.factory.create_button('miaz-import-folder', callback=self._on_import_directory)
        rowImportDir = self.factory.create_actionrow(title='Import directory', subtitle='Import all documents from a directory', suffix=btnImportDir)
        listbox.append(child=rowImportDir)
        popover = Gtk.Popover()
        popover.set_child(vbox)
        popover.present()
        btnImport = Gtk.MenuButton(child=Adw.ButtonContent(label='Import...', icon_name='miaz-import'), css_classes=['success'])
        # ~ button.get_style_context().add_class(class_name='success')
        btnImport.set_popover(popover)
        cbws.append(btnImport)

        ## Documents selected
        self.mnuSelMulti = self.create_menu_selection_multiple()
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
        sep = Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL)
        btnSelectAll = self.factory.create_button('miaz-select-all', callback=self._on_select_all, css_classes=['flat'])
        btnSelectNone = self.factory.create_button('miaz-select-none', callback=self._on_select_none, css_classes=['flat'])
        cbws.append(boxDocsSelected)
        cbws.append(sep)
        cbws.append(btnSelectNone)
        cbws.append(btnSelectAll)

        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        # ~ self.ent_sb.set_width_chars(41)
        self.ent_sb.connect('changed', self._on_filter_selected)
        self.ent_sb.set_hexpand(False)


        # ~ cbws.append(self.ent_sb)

        cbwe = self.factory.create_box_horizontal(margin=0, spacing=3)

        # ~ boxEmpty = self.factory.create_box_horizontal(hexpand=False)

        sep = Gtk.Separator.new(orientation=Gtk.Orientation.VERTICAL)
        self.tgbExplain = self.factory.create_button_toggle('miaz-magic', callback=self._on_explain_toggled, css_classes=['flat'])
        self.tgbFilters = self.factory.create_button_toggle('miaz-filters', callback=self._on_filters_toggled, css_classes=['flat'])
        self.tgbFilters.set_active(False)

        btnRepoSettings = MiAZMenuButton(MiAZ_MENU_WORKSPACE_REPO, 'repo-menu', css_classes=['flat'], child=Adw.ButtonContent(icon_name='document-properties'))
        # ~ btnRepoSettings = Gtk.MenuButton(css_classes=['flat'], child=Adw.ButtonContent(icon_name='document-properties'))
        # ~ popRepoSettings = Gtk.PopoverMenu.new_from_model(self.mnuSelMulti)
        # ~ btnRepoSettings.set_popover(popover=popRepoSettings)
        btnRepoSettings.set_valign(Gtk.Align.CENTER)

        # and create actions to handle menu actions
        for action, shortcut in [('repo_settings', [''])]:
            self.factory.create_menu_action(action, self.menu_repo_handler, shortcut)

        cbwe.append(self.tgbExplain)
        cbwe.append(self.tgbFilters)
        cbwe.append(sep)
        cbwe.append(btnRepoSettings)
        # ~ cbwe.append(btnSelectAll)

        toolbar_top.set_start_widget(cbws)
        toolbar_top.set_center_widget(self.ent_sb)
        toolbar_top.set_end_widget(cbwe)
        return toolbar_top

    def menu_repo_handler(self, action, state):
        name = action.get_name()
        if name == 'repo_settings':
            self.log.debug("Execute Settings Assistant")
            assistant = MiAZAssistantRepoSettings(self.app)
            assistant.set_transient_for(self.app.win)
            assistant.set_modal(True)
            assistant.present()

    def _setup_columnview(self):
        self.view = MiAZColumnViewWorkspace(self.app)
        self.view.factory_icon_type.connect("bind", self._on_factory_bind_icon_type)
        self.view.get_style_context().add_class(class_name='caption')
        self.view.set_filter(self._do_filter_view)
        frmView = self.factory.create_frame(hexpand=True, vexpand=True)
        frmView.set_child(self.view)
        return frmView

    def _on_factory_bind_icon_type(self, factory, list_item):
        box = list_item.get_child()
        button = box.get_first_child()
        popover = button.get_popover()
        item = list_item.get_item()
        if item.valid:
            mimetype, val = Gio.content_type_guess('filename=%s' % item.id)
            gicon = Gio.content_type_get_icon(mimetype)
            icon_name = gicon.get_names()[0]
            child=Adw.ButtonContent(label='', icon_name=icon_name)
        else:
            child=Adw.ButtonContent(label='', icon_name='miaz-rename')
        widget = self._setup_item_valid_popover(item)
        popover.set_child(widget)
        popover.present()
        button.set_child(child)

    # ~ def _setup_statusbar(self):
        # ~ statusbar = Gtk.Statusbar()
        # ~ self.sbcid = statusbar.get_context_id('MiAZ')
        # ~ return statusbar

    def _setup_item_valid_popover(self, item):
        listbox = Gtk.ListBox.new()
        listbox.set_activate_on_single_click(False)
        listbox.unselect_all()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        vbox = self.factory.create_box_vertical()
        vbox.append(child=listbox)
        doc = item.id
        valid = self.repodct[doc]['valid']
        reasons = self.repodct[doc]['reasons']
        items = []
        for rc, reason in reasons:
            if rc:
                icon_name = 'miaz-ok'
            else:
                icon_name = 'miaz-ko'
            row = self.factory.create_box_horizontal()
            button = self.factory.create_button(icon_name=icon_name)
            label = Gtk.Label()
            label.set_markup(reason)
            label.get_style_context().add_class(class_name='caption')
            row.append(button)
            row.append(label)
            listbox.append(child=row)
        return vbox

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
        # ~ foot = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=False, vexpand=False)
        widget.append(head)
        widget.append(body)
        # ~ widget.append(foot)

        toolbar_top = self._setup_toolbar_top()
        self.toolbar_filters = self._setup_toolbar_filters()
        frmView = self._setup_columnview()
        # ~ self.statusbar = self._setup_statusbar()
        head.append(toolbar_top)
        head.append(self.toolbar_filters)
        body.append(frmView)
        # ~ foot.append(self.statusbar)

        # ~ if self.num_review == 0:
            # ~ self.statusbar.set_visible(False)

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
        # ~ {timestamp}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}
        fields = [Country, Group, SentBy, Purpose, Concept, SentTo]

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
        self._on_explain_toggled(self.tgbExplain)
        repo = self.backend.repo_config()
        repocnf = repo['cnf_file']
        self.repodct = self.util.json_load(repocnf)
        sentby = self.app.get_config('SentBy')
        sentto = self.app.get_config('SentTo')
        items = []
        for path in self.repodct:
            valid = self.repodct[path]['valid']
            fields = self.repodct[path]['fields']
            try:
                adate = datetime.strptime(fields[0], "%Y%m%d")
                date_dsc = adate.strftime("%Y.%m.%d")
            except:
                date_dsc = ''
            items.append(MiAZItem
                                (
                                    id=path,
                                    date=fields[0],
                                    date_dsc = date_dsc,
                                    country=fields[1],
                                    group=fields[2],
                                    sentby_id=fields[3],
                                    sentby_dsc=sentby.get(fields[3]),
                                    purpose=fields[4],
                                    title=os.path.basename(path),
                                    subtitle=fields[5].replace('_', ' '),
                                    sentto_id=fields[6],
                                    sentto_dsc=sentto.get(fields[6]),
                                    valid=valid)
                                )
        self.view.update(items)
        self._on_filter_selected()
        self.update_title()
        if self.show_dashboard:
            self.tgbExplain.set_active(True)
        self.lblDocumentsSelected = "0 of %d documents selected" % len(self.repodct)

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
        c0 = self._do_eval_cond_matches_freetext(item.id)
        c1 = self._do_eval_cond_matches(self.dropdown['Country'], item.country)
        c2 = self._do_eval_cond_matches(self.dropdown['Group'], item.group)
        c4 = self._do_eval_cond_matches(self.dropdown['SentBy'], item.sentby_id)
        c5 = self._do_eval_cond_matches(self.dropdown['Purpose'], item.purpose)
        c6 = self._do_eval_cond_matches(self.dropdown['SentTo'], item.sentto_id)
        return c0 and c1 and c2 and c4 and c5 and c6

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
        self.display_dashboard()

    def _on_select_all(self, *args):
        selection = self.view.get_selection()
        selection.select_all()

    def _on_select_none(self, *args):
        selection = self.view.get_selection()
        selection.unselect_all()

    def display_dashboard(self, *args):
        self.displayed = 0
        self.num_review = 0
        self.dfilter = {}
        self.show_dashboard = True
        self.view.column_subtitle.set_title('Concept')
        self.view.column_subtitle.set_expand(True)
        self.view.refilter()
        self.update_title()
        self.tgbExplain.set_active(True)
        self.tgbExplain.set_visible(True)
        self.tgbFilters.set_visible(True)

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
