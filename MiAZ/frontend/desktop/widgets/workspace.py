#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from datetime import timedelta

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension
from MiAZ.frontend.desktop.util import get_file_mimetype
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, ColIcon, ColLabel, ColButton
from MiAZ.frontend.desktop.factory import MenuHeader
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepoSettings
from MiAZ.frontend.desktop.widgets.menu import MiAZ_MENU_WORKSPACE_REPO
from MiAZ.frontend.desktop.widgets.columnviews import MiAZColumnViewWorkspace, MiAZColumnViewMassRename, MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo

# Conversion Item type to Field Number
Field = {}
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Date'] = Gtk.Calendar()


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
    show_dashboard = True
    signals = set()
    selected_items = []
    dates = {}

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

    def _setup_toolbar_filters(self):
        widget = self.factory.create_box_horizontal(hexpand=True, vexpand=False)
        body = self.factory.create_box_horizontal(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.set_homogeneous(True)
        body.set_margin_top(margin=6)
        widget.append(body)

        # FIXME: Do NOT fill dropdowns here.
        self.dropdown = {}
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            dropdown = self.factory.create_dropdown_generic(item_type=item_type, dropdown_search_function=None)
            self.actions.dropdown_populate(dropdown, item_type, none_value=True)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            boxDropdown = self.factory.create_box_filter(i_title, dropdown)
            body.append(boxDropdown)
            self.dropdown[i_type] = dropdown
        self.backend.connect('source-configuration-updated', self._on_workspace_update)
        self.config['Country'].connect('country-used', self.update_dropdown, Country)
        self.config['Group'].connect('group-used', self.update_dropdown, Group)
        self.config['SentBy'].connect('sentby-used', self.update_dropdown, SentBy)
        self.config['Purpose'].connect('purpose-used', self.update_dropdown, Purpose)
        self.config['SentTo'].connect('sentto-used', self.update_dropdown, SentTo)
        return widget

    def _on_workspace_update(self, *args):
        GLib.idle_add(self.update)

    def _on_search_dropdown_changed(self, search_entry):
        # FIXME
        self.search_text_widget = search_entry.get_text()

    def update_dropdown(self, config, item_type):
        title = item_type.__gtype_name__
        self.actions.dropdown_populate(self.dropdown[title], item_type)

    def _on_mass_action_rename(self, action, data, item_type):
        def update_dropdown(config, dropdown, item_type, any_value):
            title = item_type.__gtype_name__
            self.actions.dropdown_populate(dropdown, item_type, any_value=any_value)
            dropdown.set_selected(0)

        i_type = item_type.__gtype_name__
        i_title = item_type.__title__
        self.log.debug("Rename %s for:", i_title)
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(self.selected_items), i_title))
        dropdown = self.factory.create_dropdown_generic(item_type)
        btnManage = self.factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', self.on_resource_manage, Configview[i_type](self.app))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        dropdown.connect("notify::selected-item", self._on_mass_renaming_change, cv, item_type)
        self.config[i_type].connect('%s-used' % i_type.lower(), update_dropdown, dropdown, item_type, False)
        self.actions.dropdown_populate(dropdown, item_type, any_value=False)
        frame.set_child(cv)
        box.append(label)
        hbox = self.factory.create_box_horizontal()
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=1024, height=600)
        dialog.connect('response', self._on_mass_renaming, dropdown, item_type)
        dialog.show()

    def on_resource_manage(self, widget: Gtk.Widget, selector: Gtk.Widget):
        box = self.factory.create_box_vertical(spacing=0, vexpand=True, hexpand=True)
        box.append(selector)
        config_for = selector.get_config_for()
        selector.set_vexpand(True)
        selector.update()
        dialog = self.factory.create_dialog(self.app.win, 'Manage %s' % config_for, box, 800, 600)
        dialog.show()

    def _on_mass_renaming_change(self, dropdown, item, columnview, item_type):
        i_type = item_type.__gtype_name__
        i_title = item_type.__title__
        citems = []
        for item in self.selected_items:
            try:
                source = item.id
                name, ext = self.util.filename_details(source)
                n = Field[item_type]
                tmpfile = name.split('-')
                tmpfile[n] = dropdown.get_selected_item().id
                filename = "%s.%s" % ('-'.join(tmpfile), ext)
                target = os.path.join(os.path.dirname(source), filename)
                txtId = "<small>%s</small>" % os.path.basename(source)
                txtTitle = "<small>%s</small>" % os.path.basename(target)
                citems.append(File(id=txtId, title=txtTitle))
            except:
                # FIXME: AtributeError: 'NoneType' object has no attribute 'id'
                # It happens when managing resources from inside the dialog
                pass
        columnview.update(citems)

    def _on_mass_action_delete(self, *args):
        self.log.debug("Mass deletion")
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label('Delete the following documents')
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassDelete(self.app)
        cv.get_style_context().add_class(class_name='monospace')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in self.selected_items:
            citems.append(File(id=item.id, title=os.path.basename(item.id)))
        cv.update(citems)
        frame.set_child(cv)
        box.append(label)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, 'Mass deletion', box, width=1024, height=600)
        dialog.connect('response', self._on_mass_delete)
        dialog.show()

    def _on_mass_delete(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            for item in self.selected_items:
                self.util.filename_delete(item.id)
        dialog.destroy()

    def _on_mass_renaming(self, dialog, response, dropdown, item_type):
        if response == Gtk.ResponseType.ACCEPT:
            title = item_type.__title__
            for item in self.selected_items:
                source = item.id
                name, ext = self.util.filename_details(source)
                n = Field[item_type]
                tmpfile = name.split('-')
                tmpfile[n] = dropdown.get_selected_item().id
                target = "%s.%s" % ('-'.join(tmpfile), ext)
                self.util.filename_rename(source, target)
        dialog.destroy()


    def _on_explain_toggled(self, button, data=None):
        active = button.get_active()
        self.view.column_title.set_visible(not active)
        try:
            self.view.column_title.set_visible(False)
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
        label = self.btnDocsSel.get_child()
        docs = self.util.get_files()
        label.set_markup("<small>%d</small> / %d / <big>%d</big>" % (len(self.selected_items), len(model), len(docs)))
        if len(self.selected_items) == 1:
            self.btnItemEdit.set_sensitive(True)
            self.btnItemDelete.set_sensitive(True)
        else:
            self.btnItemEdit.set_sensitive(False)
            self.btnItemDelete.set_sensitive(False)

    def _setup_toolbar_top(self):
        toolbar_top = Gtk.CenterBox()
        toolbar_top.get_style_context().add_class(class_name='flat')
        toolbar_top.set_hexpand(True)
        toolbar_top.set_vexpand(False)

        # Left widget
        hbox = self.factory.create_box_horizontal()
        toolbar_top.set_start_widget(hbox)

        ## Import button
        widgets = []
        btnImportFiles = self.factory.create_button('miaz-import-document', callback=self.actions.on_import_file)
        rowImportDoc = self.factory.create_actionrow(title='Import document', subtitle='Import one or more documents', suffix=btnImportFiles)
        widgets.append(rowImportDoc)
        btnImportDir = self.factory.create_button('miaz-import-folder', callback=self.actions.on_import_directory)
        rowImportDir = self.factory.create_actionrow(title='Import directory', subtitle='Import all documents from a directory', suffix=btnImportDir)
        widgets.append(rowImportDir)
        button = self.factory.create_button_popover(icon_name='miaz-import', css_classes=[''], widgets=widgets)
        hbox.append(button)


        # Center
        hbox = self.factory.create_box_horizontal(spacing=0)
        hbox.get_style_context().add_class(class_name='linked')
        toolbar_top.set_center_widget(hbox)

        ## Filters
        self.tgbFilters = self.factory.create_button_toggle('miaz-filters', callback=self._on_filters_toggled)
        self.tgbFilters.set_active(False)
        hbox.append(self.tgbFilters)

        ## Searchbox
        self.ent_sb = Gtk.SearchEntry(placeholder_text="Type here")
        self.ent_sb.set_hexpand(False)
        hbox.append(self.ent_sb)

        ## Date dropdown
        self.dd_date = self.factory.create_dropdown_generic(item_type=Date, ellipsize=False)
        model = self.dd_date.get_model()
        model.remove_all()
        items = []
        model.append(Date(id='0', title='This month'))
        model.append(Date(id='1', title='Last six months'))
        model.append(Date(id='2', title='This year'))
        model.append(Date(id='3', title='Last two years'))
        model.append(Date(id='4', title='Last five years'))
        model.append(Date(id='5', title='All documents'))
        self.dd_date.set_selected(2)
        self.dd_date.connect("notify::selected-item", self._on_filter_selected)
        hbox.append(self.dd_date)

        now = datetime.now()
        this_month = now-timedelta(days=30)
        six_months = now-timedelta(days=180)
        this_year = datetime.strptime("%d0101" % now.year, "%Y%m%d")
        two_years = datetime.strptime("%d0101" % (now.year - 1), "%Y%m%d")
        five_years = datetime.strptime("%d0101" % (now.year - 5), "%Y%m%d")
        alltimes = datetime.strptime("00010101", "%Y%m%d")
        self.dates['0'] = this_month
        self.dates['1'] = six_months
        self.dates['2'] = this_year
        self.dates['3'] = two_years
        self.dates['4'] = five_years
        self.dates['5'] = alltimes

        # Right
        hbox = self.factory.create_box_horizontal(spacing=0)
        hbox.get_style_context().add_class(class_name='linked')
        toolbar_top.set_end_widget(hbox)

        ## More stuff
        # ~ self.btnItemInfo = self.factory.create_button(icon_name='miaz-info')
        self.btnItemEdit = self.factory.create_button(icon_name='miaz-res-manage')
        self.btnItemEdit.connect('clicked', self.document_rename)
        self.btnItemDelete = self.factory.create_button(icon_name='miaz-entry-delete')
        self.btnItemDelete.connect('clicked', self.document_delete)
        hbox.append(self.btnItemEdit)
        hbox.append(self.btnItemDelete)

        ## Documents selected
        self.mnuSelMulti = self.create_menu_selection_multiple()
        label = Gtk.Label()
        label.get_style_context().add_class(class_name='caption')
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_child(label)
        self.popDocsSel = Gtk.PopoverMenu.new_from_model(self.mnuSelMulti)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_valign(Gtk.Align.CENTER)
        self.btnDocsSel.set_hexpand(False)
        self.btnDocsSel.set_sensitive(True)
        hbox.append(self.btnDocsSel)

        # Repo settings button
        btnRepoSettings = self.factory.create_button_menu(MiAZ_MENU_WORKSPACE_REPO, 'repo-menu', child=Adw.ButtonContent(icon_name='document-properties'))
        btnRepoSettings.set_valign(Gtk.Align.CENTER)
        for action, shortcut in [('repo_settings', [''])]:
            self.factory.create_menu_action(action, self._on_handle_menu_repo, shortcut)
        hbox.append(btnRepoSettings)

        return toolbar_top

    def _on_handle_menu_repo(self, action, state):
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
        # ~ popover = button.get_popover()
        item = list_item.get_item()
        if item.valid:
            mimetype, val = Gio.content_type_guess('filename=%s' % item.id)
            gicon = Gio.content_type_get_icon(mimetype)
            icon_name = self.app.icman.choose_icon(gicon.get_names())
            # ~ child=Adw.ButtonContent(label='', icon_name=icon_name)
            # ~ widget = self._setup_item_valid_popover(item)
        else:
            icon_name='miaz-rename'
            # ~ widget = self._setup_item_invalid_popover(item)
            # ~ child=Adw.ButtonContent(label='', icon_name='miaz-rename')
        child=Adw.ButtonContent(label='', icon_name=icon_name)
        # ~ popover.set_child(widget)
        # ~ popover.present()
        button.set_child(child)

    def _setup_item_valid_popover(self, item):
        vbox = self.factory.create_box_vertical()
        doc = item.id

        # ~ row = self.factory.create_actionrow(icon_name = 'miaz-res-manage', title='Rename document')

        separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        btnDel = self.factory.create_button(icon_name='miaz-entry-delete', title="Delete this document", css_classes=['flat'])
        btnDel.connect('clicked', self.document_delete, item.id)
        vbox.append(separator)
        vbox.append(btnDel)
        return vbox

    def _setup_item_invalid_popover(self, item):
        listbox = Gtk.ListBox.new()
        listbox.set_activate_on_single_click(False)
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        vbox = self.factory.create_box_vertical()
        doc = item.id
        valid = self.repodct[doc]['valid']
        reasons = self.repodct[doc]['reasons']
        items = []
        for rc, gtype, value, reason in reasons:
            item_type = eval(gtype)
            item_title = item_type.__title__
            icon_name = "miaz-res-%s" % gtype.lower()
            if rc:
                icon_name = 'miaz-ok'
            else:
                icon_name = 'miaz-ko'
            row = self.factory.create_actionrow(icon_name=icon_name, subtitle=reason)
            listbox.append(child=row)
        vbox.append(listbox)
        separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        btnDel = self.factory.create_button(icon_name='miaz-entry-delete', title="Delete this document", css_classes=['flat'])
        btnDel.connect('clicked', self.document_delete, item.id)
        vbox.append(child=separator)
        vbox.append(child=btnDel)
        return vbox

    def _setup_workspace(self):
        widget = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        head = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True)
        body = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        # ~ foot = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=False, vexpand=False)
        widget.append(head)
        widget.append(body)
        # ~ widget.append(foot)

        toolbar_top = self._setup_toolbar_top()
        self.toolbar_filters = self._setup_toolbar_filters()
        frmView = self._setup_columnview()
        head.append(toolbar_top)
        head.append(self.toolbar_filters)
        body.append(frmView)

        self.view.column_title.set_visible(False)
        self.view.column_subtitle.set_visible(True)
        self.view.column_subtitle.set_expand(True)
        self.view.column_group.set_visible(True)
        self.view.column_purpose.set_visible(True)
        self.view.column_flag.set_visible(True)
        self.view.column_sentby.set_visible(True)
        self.view.column_sentto.set_visible(True)
        self.view.column_date.set_visible(True)

        # Connect signals
        selection = self.view.get_selection()

        # Trigger events
        self._on_signal_filter_connect()
        self._on_filters_toggled(self.tgbFilters)
        return widget

    def create_menu_selection_multiple(self):
        self.menu_workspace_multiple = Gio.Menu.new()
        # ~ {timestamp}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}
        fields = [Country, Group, SentBy, Purpose, SentTo] # , Concept

        # Submenu for mass renaming
        submenu_rename_root = Gio.Menu.new()
        submenu_rename = Gio.MenuItem.new_submenu(
            label='Mass renaming of...',
            submenu=submenu_rename_root,
        )
        self.menu_workspace_multiple.append_item(submenu_rename)
        for item_type in fields:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            menuitem = Gio.MenuItem.new()
            menuitem.set_label(label='... %s' % i_title.lower())
            action = Gio.SimpleAction.new('rename_%s' % i_type.lower(), None)
            callback = 'self._on_mass_action_rename'
            action.connect('activate', eval(callback), item_type)
            self.app.add_action(action)
            menuitem.set_detailed_action(detailed_action='app.rename_%s' % i_type.lower())
            submenu_rename_root.append_item(menuitem)

        # ~ item_force_update = Gio.MenuItem.new()
        # ~ item_force_update.set_label(label='Force update')
        # ~ action = Gio.SimpleAction.new('workspace_update', None)
        # ~ action.connect('activate', self.update)
        # ~ self.app.add_action(action)
        # ~ item_force_update.set_detailed_action(detailed_action='app.workspace_update')
        # ~ self.menu_workspace_multiple.append_item(item_force_update)

        item_delete = Gio.MenuItem.new()
        item_delete.set_label(label='Mass deletion')
        action = Gio.SimpleAction.new('workspace_delete', None)
        action.connect('activate', self._on_mass_action_delete)
        self.app.add_action(action)
        item_delete.set_detailed_action(detailed_action='app.workspace_delete')
        self.menu_workspace_multiple.append_item(item_delete)
        return self.menu_workspace_multiple

    def get_model_filter(self):
        return self.model_filter

    def get_selection(self):
        return self.selection

    def get_item(self):
        selection = self.view.get_selection()
        selected = selection.get_selection()
        model = self.view.get_model_filter()
        pos = selected.get_nth(0)
        return model.get_item(pos)

    def update(self, *args):
        # ~ self._on_explain_toggled(self.tgbExplain)
        docs = self.util.get_files()
        sentby = self.app.get_config('SentBy')
        sentto = self.app.get_config('SentTo')
        items = []
        invalid = []
        for filename in docs:
            doc, ext = self.util.filename_details(filename)
            fields = doc.split('-')
            if self.util.filename_validate(doc):
                date_dsc = fields[0]
                # ~ try:
                    # ~ adate = datetime.strptime(fields[0], "%Y%m%d")
                    # ~ date_dsc = adate.strftime("%Y.%m.%d")
                # ~ except:
                    # ~ date_dsc = ''
                items.append(MiAZItem
                                    (
                                        id=filename,
                                        date=fields[0],
                                        date_dsc = date_dsc,
                                        country=fields[1],
                                        group=fields[2],
                                        sentby_id=fields[3],
                                        sentby_dsc=sentby.get(fields[3]),
                                        purpose=fields[4],
                                        title=doc,
                                        subtitle=fields[5].replace('_', ' '),
                                        sentto_id=fields[6],
                                        sentto_dsc=sentto.get(fields[6])
                                    )
                            )
            else:
                invalid.append(filename)
        self.view.update(items)
        self._on_filter_selected()
        label = self.btnDocsSel.get_child()
        self.view.select_first_item()
        self.log.debug("Workspace updated")
        for filename in invalid:
            target = self.util.filename_normalize(filename)
            self.util.filename_rename(filename, target)

    def _do_eval_cond_matches_freetext(self, path):
        left = self.ent_sb.get_text()
        right = path
        if left.upper() in right.upper():
            return True
        return False

    def _do_eval_cond_matches(self, dropdown, id):
        item = dropdown.get_selected_item()
        if item is None:
            return True

        if item.id == 'Any':
            return True
        elif item.id == 'None':
            if len(id) == 0:
                return True
        else:
            return item.id == id

    def _do_eval_cond_matches_date(self, item):
        try:
            if item.date is None:
                return True

            period = self.dd_date.get_selected_item().id
            try:
                item_date = self.dates[item.date]
            except KeyError:
                item_date = datetime.strptime(item.date, "%Y%m%d")
                self.dates[item.date] = item_date

            if item_date > self.dates[period]:
                return True

            return False
        except Exception as error:
            # time data '' does not match format '%Y%m%d'
            # Display documents without date
            return True

    def _do_filter_view(self, item, filter_list_model):
        c0 = self._do_eval_cond_matches_freetext(item.id)
        cd = self._do_eval_cond_matches_date(item)
        c1 = self._do_eval_cond_matches(self.dropdown['Country'], item.country)
        c2 = self._do_eval_cond_matches(self.dropdown['Group'], item.group)
        c4 = self._do_eval_cond_matches(self.dropdown['SentBy'], item.sentby_id)
        c5 = self._do_eval_cond_matches(self.dropdown['Purpose'], item.purpose)
        c6 = self._do_eval_cond_matches(self.dropdown['SentTo'], item.sentto_id)
        return c0 and c1 and c2 and c4 and c5 and c6 and cd

    def _on_signal_filter_connect(self):
        # ~ ent_sb = self.app.header.get_title_widget()
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
        self.view.refilter()
        model = self.view.cv.get_model()
        label = self.btnDocsSel.get_child()
        docs = self.util.get_files()
        label.set_markup("<small>%d</small> / %d / <big>%d</big>" % (len(self.selected_items), len(model), len(docs)))

    def _on_select_all(self, *args):
        selection = self.view.get_selection()
        selection.select_all()

    def _on_select_none(self, *args):
        selection = self.view.get_selection()
        selection.unselect_all()

    def display_dashboard(self, *args):
        self.show_dashboard = True
        self.view.column_subtitle.set_title('Concept')
        self.view.column_subtitle.set_expand(True)
        self.view.refilter()
        # ~ self.tgbExplain.set_active(True)
        # ~ self.tgbExplain.set_visible(True)
        self.tgbFilters.set_visible(True)

    def document_display(self, *args):
        item = self.get_item()
        self.actions.document_display(item.id)

    def document_delete(self, *args):
        item = self.get_item()
        self.actions.document_delete(item.id)

    def document_rename(self, *args):
        # Get item from selected row in Columnview
        item = self.get_item()
        self.actions.document_rename(item)

    def document_rename_bis(self, button, item):
        # Get item from actionrow in helper popover
        self.actions.document_rename(item)
