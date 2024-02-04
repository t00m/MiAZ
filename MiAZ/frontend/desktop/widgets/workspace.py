#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: workspace.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The central place to manage the AZ
"""

import os
from datetime import datetime
from datetime import timedelta
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
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
    __gtype_name__ = 'MiAZWorkspace'
    """Workspace"""
    __gsignals__ = {
        "extend-menu":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "extend-toolbar-top":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    selected_items = []
    dates = {}
    # ~ dropdown = {}
    cache = {}
    uncategorized = False

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = get_logger('MiAZWorkspace')
        self.app = app
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.config = self.backend.conf
        self.util = self.app.get_service('util')
        self.util.connect('filename-renamed', self._on_filename_renamed)
        self.util.connect('filename-deleted', self._on_filename_deleted)
        for node in self.config:
            self.config[node].connect('used-updated', self._on_config_used_updated)
        self.set_vexpand(False)
        self.set_margin_top(margin=3)
        self.set_margin_end(margin=3)
        self.set_margin_bottom(margin=3)
        self.set_margin_start(margin=3)
        self.app.add_widget('ws-dropdowns', {})
        frmView = self._setup_workspace()
        self.append(frmView)

        # Initialize caches
        # Runtime cache for datetime objects to avoid errors such as:
        # 'TypeError: Object of type date is not JSON serializable'
        self.datetimes = {}

        # Rest of caches
        repo = self.backend.repo_config()
        dir_conf = repo['dir_conf']
        self.fcache = os.path.join(dir_conf, 'cache.json')
        try:
            self.cache = self.util.json_load(self.fcache)
            self.log.debug("Loading cache from %s", self.fcache)
        except:
            self._initialize_caches()

        self.check_first_time()

        # Allow plug-ins to make their job
        self.app.connect('start-application-completed', self._finish_configuration)

    def _initialize_caches(self):
        self.cache = {}
        for cache in ['date', 'country', 'group', 'people', 'purpose']:
            self.cache[cache] = {}
        # ~ self.util.json_save(self.fcache, self.cache)
        # ~ self.log.debug("Caches initialized (%s)", self.fcache)

    def check_first_time(self):
        conf = self.config['Country']
        countries = conf.load(conf.used)
        if len(countries) == 0:
            self.log.debug("Execute Country Selector Assistant")
            assistant = MiAZAssistantRepoSettings(self.app)
            assistant.set_transient_for(self.app.win)
            assistant.set_modal(True)
            assistant.present()

    def _on_config_used_updated(self, *args):
        # FIXME
        # Right now, there is no way to know which config item has been
        # updated, therefore, the whole cache must be invalidated :/
        self._initialize_caches()
        # ~ self.log.debug("Config changed")

    def _on_filename_renamed(self, util, source, target):
        srvprj = self.backend.projects
        source = os.path.basename(source)
        target = os.path.basename(target)
        projects = srvprj.assigned_to(source)
        self.log.debug("%s found in these projects: %s", source, ', '.join(projects))
        for project in projects:
            srvprj.remove(project, source)
            srvprj.add(project, target)
            self.log.debug("P[%s]: %s -> %s", project, source, target)

    def _on_filename_deleted(self, util, target):
        self.backend.projects.remove(project='', doc=os.path.basename(target))

    def _finish_configuration(self, *args):
        self.log.debug("Finish loading workspace")
        # ~ self.app.load_plugins()
        self.emit('extend-menu')
        self.emit('extend-toolbar-top')

    def _setup_toolbar_filters(self):
        widget = self.factory.create_box_horizontal(hexpand=True, vexpand=False)
        body = self.factory.create_box_horizontal(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.set_homogeneous(True)
        body.set_margin_top(margin=6)
        widget.append(body)

        dropdowns = self.app.get_widget('ws-dropdowns')
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = self.factory.create_dropdown_generic(item_type=item_type)
            self.actions.dropdown_populate(self.config[i_type], dropdown, item_type, none_value=True)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            boxDropdown = self.factory.create_box_filter(i_title, dropdown)
            body.append(boxDropdown)
            dropdowns[i_type] = dropdown
            self.config[i_type].connect('used-updated', self.update_dropdown_filter, item_type)
        self.app.set_widget('ws-dropdowns', dropdowns)
        self.backend.connect('repository-updated', self._on_workspace_update)
        self.backend.connect('repository-switched', self._update_dropdowns)

        return widget

    def _update_dropdowns(self, *args):
        dropdowns = self.app.get_widget('ws-dropdowns')
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            config = self.config[i_type]
            self.actions.dropdown_populate(config, dropdowns[i_type], item_type, True, True)


    def _on_workspace_update(self, *args):
        GLib.idle_add(self.update)

    def update_dropdown_filter(self, config, item_type):
        dropdowns = self.app.get_widget('ws-dropdowns')
        i_type = item_type.__gtype_name__
        self.actions.dropdown_populate(config, dropdowns[i_type], item_type)
        self.log.debug("Dropdown %s updated", i_type)

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
        # ~ if len(self.selected_items) == 1:
            # ~ menu = self.app.get_widget('workspace-menu-single')
            # ~ self.popDocsSel.set_menu_model(menu)
        # ~ else:
            # ~ menu = self.app.get_widget('workspace-menu-selection')
            # ~ self.popDocsSel.set_menu_model(menu)

    def _setup_toolbar_top(self):
        hbox_tt = self.factory.create_box_horizontal(hexpand=True, vexpand=False)
        toolbar_top = Gtk.CenterBox()
        hbox_tt.append(toolbar_top)
        toolbar_top.get_style_context().add_class(class_name='toolbar')
        toolbar_top.set_hexpand(True)
        toolbar_top.set_vexpand(False)

        # Left widget
        hbox = self.app.add_widget('workspace-toolbar-top-left', self.factory.create_box_horizontal())
        hbox.get_style_context().add_class(class_name='linked')
        hbox.set_hexpand(True)
        toolbar_top.set_start_widget(hbox)

        button = self.factory.create_button(title='Pending of review')
        button.get_style_context().add_class(class_name='suggested-action')
        self.app.add_widget('workspace-button-uncategorized', button)
        button.connect('clicked', self.display_uncategorized)
        button.set_visible(False)
        hbox.append(button)

        # Center
        hbox = self.app.add_widget('workspace-toolbar-top-center', self.factory.create_box_horizontal(spacing=0))
        hbox.get_style_context().add_class(class_name='linked')
        hbox.set_valign(Gtk.Align.CENTER)
        toolbar_top.set_center_widget(hbox)

        ## Filters
        self.tgbFilters = self.factory.create_button_toggle('miaz-filters', callback=self._on_filters_toggled)
        self.tgbFilters.set_active(True)
        self.tgbFilters.set_valign(Gtk.Align.CENTER)
        hbox.append(self.tgbFilters)

        ## Searchbox
        self.ent_sb = Gtk.SearchEntry(placeholder_text=_('Type here'))
        self.ent_sb.set_hexpand(True)
        hbox.append(self.ent_sb)

        dropdowns = self.app.get_widget('ws-dropdowns')
        ## Date dropdown
        i_type = Date.__gtype_name__
        dd_date = self.factory.create_dropdown_generic(item_type=Date, ellipsize=False, enable_search=False)
        dropdowns[i_type] = dd_date
        self._update_dropdown_date()
        dd_date.set_selected(2)
        # ~ self.dd_date.connect("notify::selected-item", self._on_filter_selected)
        dd_date.connect("notify::selected-item", self.update)
        hbox.append(dd_date)

        ## Projects dropdown
        i_type = Project.__gtype_name__
        dd_prj = self.factory.create_dropdown_generic(item_type=Project)
        dd_prj.set_size_request(300, -1)
        dropdowns[i_type] = dd_prj
        self.actions.dropdown_populate(self.config[i_type], dd_prj, Project, any_value=True, none_value=True)
        dd_prj.connect("notify::selected-item", self._on_filter_selected)
        self.config[i_type].connect('used-updated', self.update_dropdown_filter, Project)
        hbox.append(dd_prj)

        self.app.set_widget('ws-dropdowns', dropdowns)

        # Right
        hbox = self.app.add_widget('workspace-toolbar-top-right', self.factory.create_box_horizontal(spacing=0))
        hbox.get_style_context().add_class(class_name='linked')
        toolbar_top.set_end_widget(hbox)

        ## Import button
        widgets = []
        btnImportFiles = self.factory.create_button('miaz-import-document', callback=self.actions.import_file)
        rowImportDoc = self.factory.create_actionrow(title=_('Import document'), subtitle=_('Import one or more documents'), suffix=btnImportFiles)
        widgets.append(rowImportDoc)
        btnImportDir = self.factory.create_button('miaz-import-folder', callback=self.actions.import_directory)
        rowImportDir = self.factory.create_actionrow(title=_('Import directory'), subtitle=_('Import all documents from a directory'), suffix=btnImportDir)
        widgets.append(rowImportDir)
        # FIXME: Not implemented yet
        # ~ btnImportConf = self.factory.create_button('miaz-import-config', callback=self.actions.import_config)
        # ~ rowImportConf = self.factory.create_actionrow(title='Import config', subtitle='Import configuration', suffix=btnImportConf)
        # ~ widgets.append(rowImportConf)
        button = self.factory.create_button_popover(icon_name='miaz-list-add', title='', widgets=widgets)
        hbox.append(button)

        # Menu Single and Multiple
        popovermenu = self._setup_menu_selection()
        label = Gtk.Label()
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_child(label)
        self.popDocsSel = Gtk.PopoverMenu()
        self.popDocsSel.set_menu_model(popovermenu)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_sensitive(True)
        hbox.append(self.btnDocsSel)

        # Repo settings button
        menu_repo = self.app.add_widget('workspace-menu-repo', Gio.Menu.new())
        section_common_in = self.app.add_widget('workspace-menu-repo-section-in', Gio.Menu.new())
        section_common_out = self.app.add_widget('workspace-menu-repo-section-out', Gio.Menu.new())
        section_danger = self.app.add_widget('workspace-menu-repo-section-danger', Gio.Menu.new())
        menu_repo.append_section(None, section_common_in)
        menu_repo.append_section(None, section_common_out)
        menu_repo.append_section(None, section_danger)

        # ~ ## Actions in
        # ~ menuitem = self.factory.create_menuitem(name='repo_settings', label='Repository settings', callback=self._on_handle_menu_repo, data=None, shortcuts=[])
        # ~ section_common_in.append_item(menuitem)

        # ~ ## Actions out
        # ~ submenu_backup = Gio.Menu.new()
        # ~ menu_backup = Gio.MenuItem.new_submenu(
            # ~ label = 'Backup...',
            # ~ submenu = submenu_backup,
        # ~ )
        # ~ section_common_out.append_item(menu_backup)
        # ~ menuitem = self.factory.create_menuitem('backup-config', '...only config', self._on_handle_menu_repo, None, [])
        # ~ submenu_backup.append_item(menuitem)
        # ~ menuitem = self.factory.create_menuitem('backup-data', '...only data', self._on_handle_menu_repo, None, [])
        # ~ submenu_backup.append_item(menuitem)
        # ~ menuitem = self.factory.create_menuitem('backup-all', '...config and data', self._on_handle_menu_repo, None, [])
        # ~ submenu_backup.append_item(menuitem)

        btnRepoSettings = self.factory.create_button_menu(icon_name='document-properties', menu=menu_repo)
        hbox.append(btnRepoSettings)

        return hbox_tt

    def _update_dropdown_date(self):
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        dt2str = self.util.datetime_to_string
        now = datetime.now().date()
        model_filter = dd_date.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.remove_all()

        # Since...
        ul = now                                  # upper limit
        ## this month
        ll = self.util.since_date_this_month(now) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('This month')))

        ## Last 3 months
        ll = self.util.since_date_last_n_months(now, 3) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('Last 3 months')))

        ## Last six months
        ll = self.util.since_date_last_n_months(now, 6) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('Last 6 months')))

        ## This year
        ll = self.util.since_date_this_year(now) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('This year')))

        ## Two years ago
        ll = self.util.since_date_past_year(now) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('Since two years ago')))

        ## Three years ago
        ll = self.util.since_date_three_years(now) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('Since three years ago')))

        ## Five years ago
        ll = self.util.since_date_five_years(now) # lower limit
        key = "%s-%s" % (dt2str(ll), dt2str(ul))
        model.append(Date(id=key, title=_('Since five years ago')))

        ## All documents
        key = "All-All"
        model.append(Date(id=key, title=_('All documents')))

        ## No date
        key = "None-None"
        model.append(Date(id=key, title=_('Without date')))

    def _setup_columnview(self):
        self.view = MiAZColumnViewWorkspace(self.app)
        self.app.add_widget('workspace-view', self.view)
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
        child = self.factory.create_button('icon_name')
        button.set_child(child)

    def _setup_workspace(self):
        widget = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        head = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True)
        body = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        # ~ foot = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=False, vexpand=False)
        widget.append(head)
        widget.append(body)
        # ~ widget.append(foot)

        self.toolbar_filters = self._setup_toolbar_filters()
        self.app.add_widget('workspace-toolbar-filters', self.toolbar_filters)
        toolbar_top = self.app.add_widget('workspace-toolbar-top', self._setup_toolbar_top())
        # ~ headerbar = self.app.get_widget('headerbar')
        # ~ headerbar.set_title_widget(toolbar_top)
        frmView = self._setup_columnview()
        # ~ head.append(toolbar_top)
        head.append(toolbar_top)
        head.append(self.toolbar_filters)
        body.append(frmView)

        self.view.column_title.set_visible(False)
        self.view.column_subtitle.set_visible(True)
        self.view.column_subtitle.set_expand(True)
        self.view.column_group.set_visible(True)
        self.view.column_purpose.set_visible(True)
        # ~ self.view.column_flag.set_visible(True)
        self.view.column_sentby.set_visible(True)
        self.view.column_sentto.set_visible(True)
        self.view.column_date.set_visible(True)

        # Connect signals
        selection = self.view.get_selection()

        # Trigger events
        self._do_connect_filter_signals()
        self._on_filters_toggled(self.tgbFilters)

        return widget

        # ~ menuitem = self.factory.create_menuitem('annotate', 'Annotate document', self._on_handle_menu_single, None, [])
        # ~ menuitem = self.factory.create_menuitem('clipboard', 'Copy filename', self._on_handle_menu_single, None, [])
        # ~ menuitem = self.factory.create_menuitem('directory', 'Open file location', self._on_handle_menu_single, None, [])

    def _setup_menu_selection(self):
        menu_selection = self.app.add_widget('workspace-menu-selection', Gio.Menu.new())
        section_common_in = self.app.add_widget('workspace-menu-selection-section-common-in', Gio.Menu.new())
        section_common_out = self.app.add_widget('workspace-menu-selection-section-common-out', Gio.Menu.new())
        section_danger = self.app.add_widget('workspace-menu-selection-section-danger', Gio.Menu.new())
        menu_selection.append_section(None, section_common_in)
        menu_selection.append_section(None, section_common_out)
        menu_selection.append_section(None, section_danger)

        ## Export
        submenu_export = Gio.Menu.new()
        menu_export = Gio.MenuItem.new_submenu(
            label = _('Export...'),
            submenu = submenu_export,
        )
        section_common_out.append_item(menu_export)
        self.app.add_widget('workspace-menu-selection-menu-export', menu_export)
        self.app.add_widget('workspace-menu-selection-submenu-export', submenu_export)

        return menu_selection

    def get_item(self):
        selection = self.view.get_selection()
        selected = selection.get_selection()
        model = self.view.get_model_filter()
        pos = selected.get_nth(0)
        return model.get_item(pos)

    def get_selected_items(self):
        return self.selected_items

    def update(self, *args):
        # FIXME: come up w/ a solution to display only available values
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        dd_prj = dropdowns[Project.__gtype_name__]
        filters = {}
        self.selected_items = []
        docs = self.util.get_files()
        sentby = self.app.get_config('SentBy')
        sentto = self.app.get_config('SentTo')
        countries = self.app.get_config('Country')
        groups = self.app.get_config('Group')
        purposes = self.app.get_config('Purpose')
        warning = False

        try:
            period = dd_date.get_selected_item().title
        except AttributeError:
            return
        project = dd_prj.get_selected_item().id
        # ~ self.log.debug("Period: %s - Project: %s", period, project)
        if project == 'Any' or project == 'None':
            pass

        items = []
        invalid = []
        ds = datetime.now()
        for filename in docs:
            active = True
            doc, ext = self.util.filename_details(filename)
            fields = doc.split('-')
            if self.util.filename_validate(doc):
                # Get field descriptions
                ## Dates
                try:
                    date_dsc = self.cache['date'][fields[0]]
                except:
                    # ~ date_dsc = self.util.filename_date_human(fields[0])
                    date_dsc = self.util.filename_date_human_simple(fields[0])
                    if date_dsc is None:
                        active = False
                        date_dsc = ''
                    else:
                        self.cache['date'][fields[0]] = date_dsc

                ## Countries
                try:
                    country_dsc = self.cache['country'][fields[1]]
                except:
                    country_dsc = countries.get(fields[1])
                    if country_dsc is None:
                        active = False
                        country_dsc = ''
                    else:
                        self.cache['country'][fields[1]] = country_dsc

                ## Purposes
                try:
                    purpose_dsc = self.cache['purpose'][fields[4]]
                except:
                    purpose_dsc = purposes.get(fields[4])
                    if purpose_dsc is None:
                        active = False
                        purpose_dsc = ''
                    else:
                        if len(purpose_dsc) == 0:
                            purpose_dsc = fields[4]
                        self.cache['purpose'][fields[4]] = purpose_dsc

                ## People
                try:
                    sentby_dsc = self.cache['people'][fields[3]]
                except:
                    sentby_dsc = sentby.get(fields[3])
                    if sentby_dsc is None:
                        active = False
                        sentby_dsc = ''
                    else:
                        self.cache['people'][fields[3]] = sentby_dsc

                try:
                    sentto_dsc = self.cache['people'][fields[6]]
                except:
                    sentto_dsc = sentto.get(fields[6])
                    if sentto_dsc is None:
                        active = False
                        sentto_dsc = ''
                    else:
                        self.cache['people'][fields[6]] = sentto_dsc

                if not active:
                    invalid.append(os.path.basename(filename))

                items.append(MiAZItem
                                    (
                                        id=os.path.basename(filename),
                                        date=fields[0],
                                        date_dsc = date_dsc,
                                        country=fields[1],
                                        country_dsc=country_dsc,
                                        group=fields[2],
                                        sentby_id=fields[3],
                                        sentby_dsc=sentby_dsc,
                                        purpose=purpose_dsc,
                                        title=doc,
                                        subtitle=fields[5].replace('_', ' '),
                                        sentto_id=fields[6],
                                        sentto_dsc=sentto_dsc,
                                        active=active
                                    )
                            )
            else:
                invalid.append(filename)
        # ~ de = datetime.now()
        # ~ dt = de - ds
        # ~ self.log.debug("Workspace updated (%s)" % dt)
        self.util.json_save(self.fcache, self.cache)
        # ~ self.log.debug("Saving cache to %s", self.fcache)
        GLib.idle_add(self.view.update, items)
        self._on_filter_selected()
        label = self.btnDocsSel.get_child()
        self.view.select_first_item()
        renamed = 0
        for filename in invalid:
            target = self.util.filename_normalize(filename)
            rename = self.util.filename_rename(filename, target)
            if rename:
                renamed += 1
        self.log.debug("Documents renamed: %d", renamed)

        button = self.app.get_widget('workspace-button-uncategorized')
        if len(invalid) > 0:
            button.set_visible(True)
        else:
            button.set_visible(False)

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
        # Convert timestamp to timedate object and cache it
        try:
            item_dt = self.datetimes[item.date]
        except:
            item_dt = self.util.string_to_datetime(item.date)
            self.datetimes[item.date] = item_dt

        # Check if the date belongs to the lower/upper limit
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        period = dd_date.get_selected_item().id
        ll, ul = period.split('-')

        if ll == 'All' and ul == 'All':
            return True
        elif ll == 'None' and ul == 'None':
            if item_dt is None:
                matches = True
            else:
                matches = False
        elif item_dt is None:
                matches = False
        else:
            start = self.util.string_to_datetime(ll)
            end = self.util.string_to_datetime(ul)
            if item_dt >= start and item_dt <= end:
                matches = True
            else:
                matches = False
        # ~ self.log.debug("%s >= Item[%s] Datetime[%s] <= %s? %s", ll, item.date, item_dt, ul, matches)
        return matches

    def _do_eval_cond_matches_project(self, doc):
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_prj = dropdowns[Project.__gtype_name__]
        matches = False
        try:
            project = dd_prj.get_selected_item().id
        except AttributeError:
            # Raised when managing projects from selector
            # Workaround: do not filter
            return True
        if project == 'Any':
            matches = True
        elif project == 'None':
            projects = self.backend.projects.assigned_to(doc)
            if len(projects) == 0:
                matches = True
        else:
            matches = self.backend.projects.exists(project, doc)
        return matches

    def _do_filter_view(self, item, filter_list_model):
        if self.uncategorized:
            return item.active == False
        else:
            dropdowns = self.app.get_widget('ws-dropdowns')
            c0 = self._do_eval_cond_matches_freetext(item.id)
            cd = self._do_eval_cond_matches_date(item)
            c1 = self._do_eval_cond_matches(dropdowns['Country'], item.country)
            c2 = self._do_eval_cond_matches(dropdowns['Group'], item.group)
            c4 = self._do_eval_cond_matches(dropdowns['SentBy'], item.sentby_id)
            c5 = self._do_eval_cond_matches(dropdowns['Purpose'], item.purpose)
            c6 = self._do_eval_cond_matches(dropdowns['SentTo'], item.sentto_id)
            cp = self._do_eval_cond_matches_project(item.id)
            return c0 and c1 and c2 and c4 and c5 and c6 and cd and cp

    def _do_connect_filter_signals(self):
        self.ent_sb.connect('changed', self._on_filter_selected)
        dropdowns = self.app.get_widget('ws-dropdowns')
        for dropdown in dropdowns:
            dropdowns[dropdown].connect("notify::selected-item", self._on_filter_selected)
        selection = self.view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def display_uncategorized(self, *args):
        self.uncategorized = True
        self._on_filter_selected()
        self.uncategorized = False

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

    def display_dashboard(self, *args):
        self.view.column_subtitle.set_title(_('Concept'))
        self.view.column_subtitle.set_expand(True)
        self.view.refilter()
        self.tgbFilters.set_visible(True)
