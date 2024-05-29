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
        "workspace-loaded":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    workspace_loaded = False
    selected_items = []
    dates = {}
    cache = {}
    used_signals = {} # Signals ids for Dropdowns connected to config
    uncategorized = False
    pending = False

    def __init__(self, app):
        super(MiAZWorkspace, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = get_logger('MiAZ.Workspace')
        self.app = app
        self.backend = self.app.backend
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.repository = self.app.get_service('repo')
        self.config = self.backend.get_config()
        self.util = self.app.get_service('util')
        self.util.connect('filename-renamed', self._on_filename_renamed)
        self.util.connect('filename-deleted', self._on_filename_deleted)
        for node in self.config:
            self.config[node].connect('used-updated', self._on_config_used_updated)
        self.app.add_widget('ws-dropdowns', {})
        frmView = self._setup_workspace()
        self.append(frmView)

        # Initialize caches
        # Runtime cache for datetime objects to avoid errors such as:
        # 'TypeError: Object of type date is not JSON serializable'
        self.datetimes = {}

        # Load/Initialize rest of caches
        self.fcache = os.path.join(self.repository.conf, 'cache.json')
        try:
            self.cache = self.util.json_load(self.fcache)
            # ~ self.log.debug("Loading cache from %s", self.fcache)
        except:
            self.initialize_caches()

        # Allow plug-ins to make their job
        self.app.connect('start-application-completed', self._finish_configuration)
        self._on_filter_selected()

    def initialize_caches(self):
        self.cache = {}
        for cache in ['Date', 'Country', 'Group', 'SentBy', 'SentTo', 'Purpose']:
            self.cache[cache] = {}

    def _check_first_time(self):
        """
        Execute Repository Assistant if no countries have been
        defined yet.
        """
        conf = self.config['Country']
        countries = conf.load(conf.used)
        if len(countries) == 0:
            self.log.debug("Executing Assistant")
            assistant = MiAZAssistantRepoSettings(self.app)
            assistant.set_transient_for(self.app.win)
            assistant.set_modal(True)
            assistant.present()

    def _on_config_used_updated(self, *args):
        # FIXME
        # Right now, there is no way to know which config item has been
        # updated, therefore, the whole cache must be invalidated :/
        self.initialize_caches()
        self.update()
        # ~ self.log.debug("Config changed")

    def _on_filename_renamed(self, util, source, target):
        projects = self.app.get_service('Projects')
        source = os.path.basename(source)
        target = os.path.basename(target)
        lprojects = projects.assigned_to(source)
        self.log.debug("%s found in these projects: %s", source, ', '.join(lprojects))
        for project in lprojects:
            srvprj.remove(project, source)
            srvprj.add(project, target)
            self.log.debug("P[%s]: %s -> %s", project, source, target)

    def _on_filename_deleted(self, util, target):
        projects = self.app.get_service('Projects')
        projects.remove(project='', doc=os.path.basename(target))

    def _finish_configuration(self, *args):
        # ~ self.log.debug("Finish loading workspace")
        self.workspace_loaded = True
        self.emit('workspace-loaded')

    def _setup_toolbar_filters(self):
        dropdowns = self.app.get_widget('ws-dropdowns')
        widget = self.factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=False)
        body = self.factory.create_box_horizontal(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.set_homogeneous(True)
        body.set_margin_top(margin=6)
        widget.append(body)
        widget.append(Gtk.Separator.new(orientation=Gtk.Orientation.HORIZONTAL))

        ### Projects dropdown
        i_type = Project.__gtype_name__
        i_title = _(Project.__title__)
        dd_prj = self.factory.create_dropdown_generic(item_type=Project)
        boxDropdown = self.factory.create_box_filter(i_title, dd_prj)
        # ~ dd_prj.set_size_request(250, -1)
        dropdowns[i_type] = dd_prj
        self.actions.dropdown_populate(self.config[i_type], dd_prj, Project, any_value=True, none_value=True)
        dd_prj.connect("notify::selected-item", self._on_filter_selected)
        dd_prj.connect("notify::selected-item", self._on_project_selected)
        dd_prj.set_hexpand(True)
        self.config[i_type].connect('used-updated', self.update_dropdown_filter, Project)
        body.append(boxDropdown)

        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = self.factory.create_dropdown_generic(item_type=item_type)
            self.actions.dropdown_populate(self.config[i_type], dropdown, item_type, none_value=True)
            sigid = dropdown.connect("notify::selected-item", self._on_filter_selected)
            boxDropdown = self.factory.create_box_filter(i_title, dropdown)
            body.append(boxDropdown)
            dropdowns[i_type] = dropdown
            self.used_signals[i_type] = self.config[i_type].connect('used-updated', self.update_dropdown_filter, item_type)
            # ~ self.log.debug("Dropdown filter for '%s' setup successfully", i_title)
        self.app.set_widget('ws-dropdowns', dropdowns)
        watcher = self.app.get_service('watcher')
        watcher.connect('repository-updated', self._on_workspace_update)
        repository = self.app.get_service('repo')
        repository.connect('repository-switched', self._update_dropdowns)

        return widget

    def _update_dropdowns(self, *args):
        dropdowns = self.app.get_widget('ws-dropdowns')
        for item_type in [Country, Group, SentBy, Purpose, SentTo, Project]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            config = self.config[i_type]
            self.actions.dropdown_populate(config, dropdowns[i_type], item_type, True, True)
            # ~ self.log.debug("Dropdown filter for '%s' updated", i_title)


    def _on_workspace_update(self, *args):
        GLib.idle_add(self.update)

    def update_dropdown_filter(self, config, item_type):
        dropdowns = self.app.get_widget('ws-dropdowns')
        i_type = item_type.__gtype_name__
        self.actions.dropdown_populate(config, dropdowns[i_type], item_type)
        # ~ self.log.debug("Dropdown %s updated", i_type)

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
        docs = self.util.get_files(self.repository.docs)
        # ~ self.log.debug(', '.join([item.id for item in self.selected_items]))
        label.set_markup("<small>%d</small> / %d / <big>%d</big>" % (len(self.selected_items), len(model), len(docs)))
        # ~ self.app.statusbar_message("Selected %d of %d documents in current view (total documents: %d)" % (len(self.selected_items), len(model), len(docs)))
        # ~ if len(self.selected_items) == 1:
            # ~ menu = self.app.get_widget('workspace-menu-single')
            # ~ self.popDocsSel.set_menu_model(menu)
        # ~ else:
            # ~ menu = self.app.get_widget('workspace-menu-selection')
            # ~ self.popDocsSel.set_menu_model(menu)

    def _setup_toolbar_top(self):
        hdb_left = self.app.get_widget('headerbar-left-box')
        hdb_right = self.app.get_widget('headerbar-right-box')
        hdb_right.get_style_context().add_class(class_name='linked')

        ## Show/Hide Filters
        self.tgbFilters = self.factory.create_button_toggle('miaz-filters2', callback=self._on_filters_toggled)
        self.tgbFilters.set_active(False)
        self.tgbFilters.set_hexpand(False)
        self.tgbFilters.get_style_context().remove_class(class_name='flat')
        self.tgbFilters.set_valign(Gtk.Align.CENTER)
        hdb_left.append(self.tgbFilters)

        ## Searchbox
        self.ent_sb = Gtk.SearchEntry(placeholder_text=_('Type here'))
        self.ent_sb.set_hexpand(False)
        self.ent_sb.get_style_context().add_class(class_name='caption')
        hdb_left.append(self.ent_sb)

        ## Dropdowns
        dropdowns = self.app.get_widget('ws-dropdowns')

        ### Date dropdown
        i_type = Date.__gtype_name__
        dd_date = self.factory.create_dropdown_generic(item_type=Date, ellipsize=False, enable_search=False)
        dd_date.set_hexpand(True)
        dropdowns[i_type] = dd_date
        self._update_dropdown_date()
        dd_date.set_selected(2)
        # ~ self.dd_date.connect("notify::selected-item", self._on_filter_selected)
        dd_date.connect("notify::selected-item", self.update)
        hdb_left.append(dd_date)

        # Workspace Menu
        hbox = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=False)
        popovermenu = self._setup_menu_selection()
        label = Gtk.Label()
        self.btnDocsSel = Gtk.MenuButton()
        self.btnDocsSel.set_always_show_arrow(True)
        self.btnDocsSel.set_child(label)
        self.popDocsSel = Gtk.PopoverMenu()
        self.popDocsSel.set_menu_model(popovermenu)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_sensitive(True)
        hbox.append(self.btnDocsSel)
        headerbar = self.app.get_widget('headerbar')
        headerbar.set_title_widget(hbox)





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
        self.view.get_style_context().add_class(class_name='monospace')
        self.view.set_filter(self._do_filter_view)
        return self.view

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
        # ~ toolbar_top = self.app.add_widget('workspace-toolbar-top', self._setup_toolbar_top())
        self._setup_toolbar_top()
        # ~ headerbar = self.app.get_widget('headerbar')
        # ~ headerbar.set_title_widget(toolbar_top)
        frmView = self._setup_columnview()
        # ~ head.append(toolbar_top)
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
        self.view.column_sentto.set_expand(False)
        self.view.column_sentby.set_expand(False)
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

        ## Add
        submenu_add = Gio.Menu.new()
        menu_add = Gio.MenuItem.new_submenu(
            label = _('Add new...'),
            submenu = submenu_add,
        )
        section_common_in.append_item(menu_add)
        self.app.add_widget('workspace-menu-in-add', submenu_add)

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

    def clean_filters(self, *args):
        dropdowns = self.app.get_widget('ws-dropdowns')
        for ddId in dropdowns:
            dropdowns[ddId].set_selected(0)
        self.log.debug("All filters cleared")

    def update(self, *args):
        # FIXME: come up w/ a solution to display only available values
        # ~ self.log.debug("Update requested")
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        dd_prj = dropdowns[Project.__gtype_name__]
        filters = {}
        self.selected_items = []
        docs = self.util.get_files(self.repository.docs)
        sentby = self.app.get_config('SentBy')
        sentto = self.app.get_config('SentTo')
        countries = self.app.get_config('Country')
        groups = self.app.get_config('Group')
        purposes = self.app.get_config('Purpose')
        warning = False
        items = []
        invalid = []
        ds = datetime.now()

        # Disconnect dropdown signals
        # ~ for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            # ~ i_type = item_type.__gtype_name__
            # ~ i_title = _(item_type.__title__)
            # ~ sigid = self.used_signals[i_type]
            # ~ self.config[i_type].disconnect(sigid)
            # ~ self.log.debug("Signal %d disconnected from Config '%s'", sigid, i_title)

        keys_used = {}
        key_fields = [('Date', 0), ('Country', 1), ('Group', 2), ('SentBy', 3), ('Purpose', 4), ('Concept', 5), ('SentTo', 6)]
        for skey, nkey in key_fields:
            keys_used[skey] = set() # Avoid duplicates

        for filename in docs:
            active = True
            doc, ext = self.util.filename_details(filename)
            fields = doc.split('-')
            if self.util.filename_validate(doc):
                desc = {}
                for skey, nkey in key_fields:
                    key = fields[nkey]
                    # ~ self.log.debug("%s > %s", key, skey)
                    if nkey == 0:
                        # Date field cached value differs from other fields
                        key = fields[nkey]
                        try:
                            desc[skey] = self.cache[skey][key]
                        except:
                            desc[skey] = self.util.filename_date_human_simple(key)
                            if desc[skey] is None:
                                active = False
                                desc[skey] = ''
                            else:
                                self.cache[skey][key] = desc[skey]
                    elif nkey == 5:
                        # Skip concept field
                        pass
                    else:
                        config = self.app.get_config(skey)
                        # Key: autodiscover key fields.
                        # Save key in config if it is used
                        if not config.exists_used(key=key):
                            keys_used[skey].add((key, key))

                        # Description
                        try:
                            desc[skey] = self.cache[skey][key]
                        except:
                            desc[skey] = config.get(key)
                            if desc[skey] is None:
                                active = False
                                desc[skey] = key
                            else:
                                self.cache[skey][key] = desc[skey]

                        # Make sure that sth is displayed if no desc
                        try:
                            if self.cache[skey][key] == '':
                                self.cache[skey][key] = key
                        except KeyError:
                            self.cache[skey][key] = key

                if not active:
                    invalid.append(os.path.basename(filename))
                # ~ self.log.debug("\n%s\n%s\n\n", filename, desc)
                items.append(MiAZItem
                                    (
                                        id=os.path.basename(filename),
                                        date=fields[0],
                                        date_dsc=desc['Date'],
                                        country=fields[1],
                                        country_dsc=desc['Country'],
                                        group=fields[2],
                                        sentby_id=fields[3],
                                        sentby_dsc=desc['SentBy'],
                                        purpose=desc['Purpose'],
                                        title=doc,
                                        subtitle=fields[5].replace('_', ' '),
                                        sentto_id=fields[6],
                                        sentto_dsc=desc['SentTo'],
                                        active=active
                                    )
                            )
            else:
                invalid.append(filename)

        # Save all keys used to conf
        for skey in keys_used:
            config = self.app.get_config(skey)
            if config is not None: # Skip fields without config
                config.add_available_batch(list(keys_used[skey]))
                config.add_used_batch(list(keys_used[skey]))

        de = datetime.now()
        dt = de - ds
        self.log.debug("Workspace updated (%s)" % dt)

        self.util.json_save(self.fcache, self.cache)
        # ~ self.log.debug("Saving cache to %s", self.fcache)
        GLib.idle_add(self.view.update, items)
        self._on_filter_selected()
        label = self.btnDocsSel.get_child()
        self.view.select_first_item()
        renamed = 0
        for filename in invalid:
            source = os.path.join(self.repository.docs, filename)
            btarget = self.util.filename_normalize(filename)
            target = os.path.join(self.repository.docs, btarget)
            rename = self.util.filename_rename(source, target)
            if rename:
                renamed += 1
        if renamed > 0:
            self.log.debug("Documents renamed: %d", renamed)

        self.selected_items = []

    def _do_eval_cond_matches_freetext(self, item):
        left = self.ent_sb.get_text()
        right = item.id
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
            return item.id.upper() == id.upper()

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
        projects = self.app.get_service('Projects')
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
            lprojects = projects.assigned_to(doc)
            if len(lprojects) == 0:
                matches = True
        else:
            matches = projects.exists(project, doc)
        return matches

    def _do_filter_view(self, item, filter_list_model):
        projects = self.app.get_service('Projects')
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_prj = dropdowns[Project.__gtype_name__]

        try:
            project = dd_prj.get_selected_item().id
        except:
            project = 'Any'

        if project != 'None':
            c0 = self._do_eval_cond_matches_freetext(item)
            cd = self._do_eval_cond_matches_date(item)
            c1 = self._do_eval_cond_matches(dropdowns['Country'], item.country)
            c2 = self._do_eval_cond_matches(dropdowns['Group'], item.group)
            c4 = self._do_eval_cond_matches(dropdowns['SentBy'], item.sentby_id)
            c5 = self._do_eval_cond_matches(dropdowns['Purpose'], item.purpose)
            c6 = self._do_eval_cond_matches(dropdowns['SentTo'], item.sentto_id)
            if project == 'Any':
                cp = True
            else:
                cp = projects.exists(project, item.id)
            show_item = c0 and c1 and c2 and c4 and c5 and c6 and cd and cp
        else:
            projects_assigned = projects.assigned_to(item.id)
            if len(projects_assigned) == 0:
                c0 = self._do_eval_cond_matches_freetext(item)
                cd = self._do_eval_cond_matches_date(item)
                c1 = self._do_eval_cond_matches(dropdowns['Country'], item.country)
                c2 = self._do_eval_cond_matches(dropdowns['Group'], item.group)
                c4 = self._do_eval_cond_matches(dropdowns['SentBy'], item.sentby_id)
                c5 = self._do_eval_cond_matches(dropdowns['Purpose'], item.purpose)
                c6 = self._do_eval_cond_matches(dropdowns['SentTo'], item.sentto_id)
                show_item = c0 and c1 and c2 and c4 and c5 and c6 and cd
            else:
                show_item = False
        return show_item

    def _do_connect_filter_signals(self):
        self.ent_sb.connect('changed', self._on_filter_selected)
        dropdowns = self.app.get_widget('ws-dropdowns')
        for dropdown in dropdowns:
            dropdowns[dropdown].connect("notify::selected-item", self._on_filter_selected)
        selection = self.view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def _on_project_selected(self, dropdown, gparam):
        """When a project is chosen, the date change to get show all
        documents"""
        try:
            prjkey = dropdown.get_selected_item().id
            if prjkey != 'Any':
                dropdowns = self.app.get_widget('ws-dropdowns')
                i_type = Date.__gtype_name__
                dropdowns[i_type].set_selected(7)
        except AttributeError:
            # ~ Raised when managing projects from selector. Skip
            pass

    def _on_filter_selected(self, *args):
        if self.workspace_loaded:
            self.view.refilter()
            model = self.view.cv.get_model() # nº items in current view
            label = self.btnDocsSel.get_child()
            docs = self.util.get_files(self.repository.docs) # nº total items
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
        self.column_sentto.set_expand(False)
        self.column_sentby.set_expand(False)
        self.view.refilter()
        self.tgbFilters.set_visible(True)
