#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from datetime import timedelta

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension, Project
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, ColIcon, ColLabel, ColButton
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepoSettings
from MiAZ.frontend.desktop.widgets.menu import MiAZ_MENU_REPO
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace, MiAZColumnViewMassRename, MiAZColumnViewMassDelete, MiAZColumnViewMassProject
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo, MiAZProjects

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
Configview['Project'] = MiAZProjects
Configview['Date'] = Gtk.Calendar


class MiAZWorkspace(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """
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

        self.dropdown = {}
        for item_type in [Project, Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            dropdown = self.factory.create_dropdown_generic(item_type=item_type, dropdown_search_function=None)
            self.actions.dropdown_populate(self.config[i_type], dropdown, item_type, none_value=True)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            boxDropdown = self.factory.create_box_filter(i_title, dropdown)
            body.append(boxDropdown)
            self.dropdown[i_type] = dropdown
            self.config[i_type].connect('used-updated', self.update_dropdown_filter, item_type)
        self.backend.connect('source-configuration-updated', self._on_workspace_update)

        return widget

    def _on_workspace_update(self, *args):
        GLib.idle_add(self.update)

    def update_dropdown_filter(self, config, item_type):
        title = item_type.__gtype_name__
        self.actions.dropdown_populate(config, self.dropdown[title], item_type)

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
            self.popDocsSel.set_menu_model(self.mnuSelSingle)
        else:
            self.popDocsSel.set_menu_model(self.mnuSelMulti)

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
        btnImportFiles = self.factory.create_button('miaz-import-document', callback=self.actions.import_file)
        rowImportDoc = self.factory.create_actionrow(title='Import document', subtitle='Import one or more documents', suffix=btnImportFiles)
        widgets.append(rowImportDoc)
        btnImportDir = self.factory.create_button('miaz-import-folder', callback=self.actions.import_directory)
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

        # Menu Single and Multiple
        self.mnuSelSingle = self._setup_menu_selection_single()
        self.mnuSelMulti = self._setup_menu_selection_multiple()

        label = Gtk.Label()
        label.get_style_context().add_class(class_name='caption')
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_has_frame(True)
        self.btnDocsSel.set_always_show_arrow(True)
        self.btnDocsSel.set_child(label)
        self.popDocsSel = Gtk.PopoverMenu.new_from_model(self.mnuSelSingle)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_valign(Gtk.Align.CENTER)
        self.btnDocsSel.set_hexpand(False)
        self.btnDocsSel.set_sensitive(True)
        hbox.append(self.btnDocsSel)

        # Repo settings button
        btnRepoSettings = self.factory.create_button_menu(MiAZ_MENU_REPO, 'repo-menu', child=Adw.ButtonContent(icon_name='document-properties'))
        btnRepoSettings.set_valign(Gtk.Align.CENTER)
        for action, shortcut in [('repo_settings', [''])]:
            self.factory.create_menu_action(action, self._on_handle_menu_repo, shortcut)
        hbox.append(btnRepoSettings)

        return toolbar_top

    def _on_handle_menu_repo(self, action, state):
        name = action.get_name()
        if name == 'repo_settings':
            self.log.debug("Execute Settings Assistant")
            self.app.show_stack_page_by_name('settings_repo')

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
        item = list_item.get_item()
        mimetype, val = Gio.content_type_guess('filename=%s' % item.id)
        gicon = Gio.content_type_get_icon(mimetype)
        icon_name = self.app.icman.choose_icon(gicon.get_names())
        child=Adw.ButtonContent(label='', icon_name=icon_name)
        button.set_child(child)

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
        self._do_connect_filter_signals()
        self._on_filters_toggled(self.tgbFilters)

        return widget

    def _setup_menu_selection_single(self):
        # Setup main menu and sections
        menu_workspace_single = Gio.Menu.new()
        section_common_in = Gio.Menu.new()
        section_common_out = Gio.Menu.new()
        section_danger = Gio.Menu.new()
        menu_workspace_single.append_section(None, section_common_in)
        menu_workspace_single.append_section(None, section_common_out)
        menu_workspace_single.append_section(None, section_danger)

        # Actions in
        menuitem = self.factory.create_menuitem('view', 'View document', self._on_handle_menu_single, None, ["<Control>d", "<Control>D"])
        section_common_in.append_item(menuitem)
        menuitem = self.factory.create_menuitem('rename', 'Rename document', self._on_handle_menu_single, None, ["<Control>r", "<Control>R"])
        section_common_in.append_item(menuitem)
        menuitem = self.factory.create_menuitem('project', 'Assign project', self._on_handle_menu_single, None, [])
        section_common_in.append_item(menuitem)
        menuitem = self.factory.create_menuitem('annotate', 'Annotate document', self._on_handle_menu_single, None, [])
        section_common_in.append_item(menuitem)

        # Actions out
        menuitem = self.factory.create_menuitem('clipboard', 'Copy filename', self._on_handle_menu_single, None, [])
        section_common_out.append_item(menuitem)
        menuitem = self.factory.create_menuitem('export', 'Export document', self._on_handle_menu_single, None, [])
        section_common_out.append_item(menuitem)

        # Dangerous actions
        menuitem = self.factory.create_menuitem('delete', 'Delete document', self._on_handle_menu_single, None, [])
        section_danger.append_item(menuitem)
        return menu_workspace_single

    def _setup_menu_selection_multiple(self):
        # Setup main menu and sections
        menu_workspace_multiple = Gio.Menu.new()
        section_common_in = Gio.Menu.new()
        section_common_out = Gio.Menu.new()
        section_danger = Gio.Menu.new()
        menu_workspace_multiple.append_section(None, section_common_in)
        menu_workspace_multiple.append_section(None, section_common_out)
        menu_workspace_multiple.append_section(None, section_danger)

        # Section -in
        # ~ # New mass renaming
        # ~ menuitem = self.factory.create_menuitem('rename', 'Mass rename', self._on_handle_menu_multiple, None, [])
        # ~ section_common_in.append_item(menuitem)

        ## Submenu for mass renaming
        submenu_rename = Gio.Menu.new()
        menu_rename = Gio.MenuItem.new_submenu(
            label='Mass renaming of...',
            submenu=submenu_rename,
        )
        section_common_in.append_item(menu_rename)
        fields = [Date, Country, Group, SentBy, Purpose, SentTo]
        for item_type in fields:
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            menuitem = self.factory.create_menuitem('rename_%s' % i_type.lower(), '...%s' % i_title.lower(), self._on_handle_menu_multiple, item_type, [])
            submenu_rename.append_item(menuitem)

        ## Assign to Project
        menuitem = self.factory.create_menuitem('project', 'Assign project', self._on_handle_menu_multiple, Project, [])
        section_common_in.append_item(menuitem)

        # Section -out
        menuitem = self.factory.create_menuitem('export', 'Export documents', self._on_handle_menu_multiple, None, [])
        section_common_out.append_item(menuitem)

        # Danger section
        menuitem = self.factory.create_menuitem('delete', 'Delete documents', self._on_handle_menu_multiple, None, [])
        section_danger.append_item(menuitem)

        return menu_workspace_multiple

    def get_item(self):
        selection = self.view.get_selection()
        selected = selection.get_selection()
        model = self.view.get_model_filter()
        pos = selected.get_nth(0)
        return model.get_item(pos)

    def update(self, *args):
        self.selected_items = []
        docs = self.util.get_files()
        sentby = self.app.get_config('SentBy')
        sentto = self.app.get_config('SentTo')
        countries = self.app.get_config('Country')
        items = []
        invalid = []
        for filename in docs:
            doc, ext = self.util.filename_details(filename)
            fields = doc.split('-')
            if self.util.filename_validate(doc):
                date_dsc = fields[0]
                try:
                    adate = datetime.strptime(fields[0], "%Y%m%d")
                    date_dsc = adate.strftime("%A, %B %d %Y")
                except:
                    date_dsc = ''
                items.append(MiAZItem
                                    (
                                        id=filename,
                                        date=fields[0],
                                        date_dsc = date_dsc,
                                        country=fields[1],
                                        country_dsc=countries.get(fields[1]),
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

    def _do_eval_cond_matches_project(self, doc):
        matches = False
        try:
            project = self.dropdown['Project'].get_selected_item().id
        except AttributeError:
            # Raised when managing projects from selector
            # Workaround: do not filter
            return True

        if project is 'Any':
            matches = True
        elif project is 'None':
            projects = self.backend.projects.assigned_to(doc)
            if len(projects) == 0:
                matches = True
        else:
            matches = self.backend.projects.exists(project, doc)
        return matches

    def _do_filter_view(self, item, filter_list_model):
        c0 = self._do_eval_cond_matches_freetext(item.id)
        cd = self._do_eval_cond_matches_date(item)
        c1 = self._do_eval_cond_matches(self.dropdown['Country'], item.country)
        c2 = self._do_eval_cond_matches(self.dropdown['Group'], item.group)
        c4 = self._do_eval_cond_matches(self.dropdown['SentBy'], item.sentby_id)
        c5 = self._do_eval_cond_matches(self.dropdown['Purpose'], item.purpose)
        c6 = self._do_eval_cond_matches(self.dropdown['SentTo'], item.sentto_id)
        cp = self._do_eval_cond_matches_project(item.id)
        return c0 and c1 and c2 and c4 and c5 and c6 and cd and cp

    def _do_connect_filter_signals(self):
        self.ent_sb.connect('changed', self._on_filter_selected)
        for dropdown in self.dropdown:
            self.dropdown[dropdown].connect("notify::selected-item", self._on_filter_selected)
        selection = self.view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def _on_filter_selected(self, *args):
        self.view.refilter()
        model = self.view.cv.get_model() # nº items in current view
        label = self.btnDocsSel.get_child()
        docs = self.util.get_files() # nº total items
        label.set_markup("<small>%d</small> / %d / <big>%d</big>" % (len(self.selected_items), len(model), len(docs)))

    def _on_select_all(self, *args):
        selection = self.view.get_selection()
        selection.select_all()

    def _on_select_none(self, *args):
        selection = self.view.get_selection()
        selection.unselect_all()

    def _on_handle_menu_single(self, action, *args):
        name = action.props.name
        item = self.get_item()
        if name == 'view':
            self.actions.document_display(item.id)
        elif name == 'rename':
            self.actions.document_rename_single(item.id)
        elif name == 'project':
            self.actions.project_assignment(Project, [item.id])
        elif name == 'annotate':
            self.log.debug("FIXME: annotate document")
        elif name == 'clipboard':
            self.log.debug("FIXME: copy filename to clipboard")
        elif name == 'export':
            self.actions.document_export([item])
        elif name == 'delete':
            self.actions.document_delete([item])

    def _on_handle_menu_multiple(self, action, data, item_type):
        name = action.props.name
        items = self.selected_items
        if name.startswith('rename_'):
            self.actions.document_rename_multiple(item_type, items)
        # ~ elif name == 'rename':
            # ~ self.actions.document_rename(items)
        elif name == 'project':
            self.actions.project_assignment(item_type, items)
        elif name == 'export':
            self.actions.document_export(items)
        elif name == 'delete':
            self.actions.document_delete(items)

    def display_dashboard(self, *args):
        self.view.column_subtitle.set_title('Concept')
        self.view.column_subtitle.set_expand(True)
        self.view.refilter()
        self.tgbFilters.set_visible(True)
