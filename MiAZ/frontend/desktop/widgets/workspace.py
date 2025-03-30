#!/usr/bin/python3
# File: workspace.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The central place to manage the AZ

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, SentBy, SentTo, Date, Project
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepoSettings
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo, MiAZProjects
from MiAZ.backend.status import MiAZStatus

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
        "workspace-view-updated": (GObject.SignalFlags.RUN_LAST, None, ()),
        "workspace-view-selection-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "workspace-view-filtered": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    _num_selected_items = 0
    _num_displayed_items = 0
    _num_total_items = 0
    workspace_loaded = False
    selected_items = []
    dates = {}
    cache = {}
    used_signals = {} # Signals ids for Dropdowns connected to config
    uncategorized = False
    pending = False

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = MiAZLog('MiAZ.Workspace')
        self.log.debug("Initializing widget Workspace!!")
        self.app = app
        self.config = self.app.get_config_dict()
        self._setup_workspace()
        self._setup_logic()
        self.review = False

        # Allow plug-ins to make their job
        self.connect('workspace-view-updated', self._on_filter_selected)
        self.app.connect('application-started', self._on_finish_configuration)
        self.app.connect('application-finished', self._on_application_finished)

    def initialize_caches(self):
        repo = self.app.get_service('repo')
        util = self.app.get_service('util')

        self.datetimes = {}

        # Load/Initialize rest of caches
        if repo.conf is None:
            return
        self.fcache = os.path.join(repo.conf, 'cache.json')
        try:
            self.cache = util.json_load(self.fcache)
            self.log.debug(f"Loading cache from '{self.fcache}'")
        except Exception:
            util.json_save(self.fcache, {})
            self.log.debug(f"New cache created in '{self.fcache}'")

        self.cache = {}
        for cache in ['Date', 'Country', 'Group', 'SentBy', 'SentTo', 'Purpose']:
            self.cache[cache] = {}
        self.log.debug("Caches initialized")

    def _check_first_time(self):
        """
        Execute Repository Assistant if no countries have been
        defined yet.
        """
        conf = self.config['Country']
        countries = conf.load(conf.used)
        if len(countries) == 0:
            window = self.app.get_widget('window')
            self.log.debug("Executing Assistant")
            assistant = MiAZAssistantRepoSettings(self.app)
            assistant.present(window)

    def _on_config_used_updated(self, *args):
        # FIXME
        # Right now, there is no way to know which config item has been
        # updated, therefore, the whole cache must be invalidated :/
        self.initialize_caches()
        # ~ self.update()


    def _on_filename_renamed(self, util, source, target):
        projects = self.app.get_service('Projects')
        source = os.path.basename(source)
        target = os.path.basename(target)
        lprojects = projects.assigned_to(source)
        self.log.debug(f"{source} found in these projects: {', '.join(lprojects)}")
        for project in lprojects:
            projects.remove(project, source)
            projects.add(project, target)
            self.log.debug(f"P[{project}]: {source} -> {target}")

    def _on_filename_deleted(self, util, target):
        projects = self.app.get_service('Projects')
        projects.remove(project='', doc=os.path.basename(target))

    def _setup_logic(self):
        actions = self.app.get_service('actions')
        util = self.app.get_service('util')
        repository = self.app.get_service('repo')

        # Dropdowns data loading
        dropdowns = self.app.get_widget('ws-dropdowns')

        ## Date dropdown
        i_type = Date.__gtype_name__
        dd_date = dropdowns[i_type]
        self._update_dropdown_date()
        dd_date.set_selected(1)
        dd_date.connect("notify::selected-item", self.update)

        ## Dropdown Projects
        i_type = Project.__gtype_name__
        i_title = _(Project.__title__)
        dd_prj = dropdowns[i_type]
        actions.dropdown_populate(self.config[i_type], dd_prj, Project, any_value=True, none_value=True)
        dd_prj.connect("notify::selected-item", self._on_filter_selected)
        dd_prj.connect("notify::selected-item", self._on_project_selected)
        dd_prj.set_hexpand(True)
        self.config[i_type].connect('used-updated', self.update_dropdown_filter, Project)
        # ~ self.log.debug(f"Dropdown filter for '{i_title}' setup successfully")

        ## Rest of dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = dropdowns[i_type]
            actions.dropdown_populate(self.config[i_type], dropdown, item_type, none_value=True)
            dropdown.connect("notify::selected-item", self._on_filter_selected)
            self.used_signals[i_type] = self.config[i_type].connect('used-updated', self.update_dropdown_filter, item_type)
            # ~ self.log.debug(f"Dropdown filter for '{i_title}' setup successfully")

        # Connect Watcher service
        watcher = self.app.get_service('watcher')
        watcher.connect('repository-updated', self._on_workspace_update)

        # Connect Repository
        repository = self.app.get_service('repo')
        repository.connect('repository-switched', self._update_dropdowns)

        # Observe filename changes
        util.connect('filename-renamed', self._on_filename_renamed)
        util.connect('filename-deleted', self._on_filename_deleted)

        # Observe config changes
        for node in self.config:
            self.config[node].connect('used-updated', self._on_config_used_updated)

        # Trigger events
        self._do_connect_filter_signals()
        # ~ self._on_sidebar_toggled()
        # ~ self._on_filter_selected()
        self.workspace_loaded = True

    def _on_finish_configuration(self, *args):
        self.log.debug("Finish loading workspace")
        window = self.app.get_widget('window')
        window.present()
        workflow = self.app.get_service('workflow')
        srvutl = self.app.get_service('util')
        srvutl.connect('filename-renamed', self.update)
        srvutl.connect('filename-deleted', self.update)
        srvutl.connect('filename-added', self.update)
        workflow.connect('repository-switch-started', self._on_repo_switch)
        self._on_repo_switch()

        self.emit('workspace-loaded')

    def _on_repo_switch(self, *args):
        sidebar = self.app.get_widget('sidebar')
        self.selected_items = []
        sidebar.clear_filters()
        self.view.refilter()
        self.update()
        # ~ self._on_filter_selected()

    def _update_dropdowns(self, *args):
        actions = self.app.get_service('actions')
        dropdowns = self.app.get_widget('ws-dropdowns')
        for item_type in [Country, Group, SentBy, Purpose, SentTo, Project]:
            i_type = item_type.__gtype_name__
            config = self.config[i_type]
            actions.dropdown_populate(config, dropdowns[i_type], item_type, True, True)

        self._update_dropdown_date()
        i_type = Date.__gtype_name__
        dd_date = dropdowns[i_type]
        dd_date.set_selected(1)

    def _on_workspace_update(self, *args):
        GLib.idle_add(self.update)

    def unselect_items(self):
        self.selected_items = []

    def update_dropdown_filter(self, config, item_type):
        actions = self.app.get_service('actions')
        dropdowns = self.app.get_widget('ws-dropdowns')
        i_type = item_type.__gtype_name__
        actions.dropdown_populate(config, dropdowns[i_type], item_type)

    def show_pending_documents(self, *args):
        sidebar = self.app.get_widget('sidebar')
        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        self.review = togglebutton.get_active()
        i_type = Date.__gtype_name__
        dropdowns = self.app.get_widget('ws-dropdowns')
        sidebar.clear_filters()
        dropdowns[i_type].set_selected(9)
        self.view.refilter()

    def _update_dropdown_date(self):
        util = self.app.get_service('util')
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        dt2str = util.datetime_to_string
        now = datetime.now().date()
        model_filter = dd_date.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()
        model.remove_all()

        # Since...
        ul = now                                  # upper limit
        ## this month
        ll = util.since_date_this_month(now) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('This month')))

        ul = now                                  # upper limit
        ## past month
        ll = util.since_date_last_n_months(now, 1) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since past month')))

        ## Last 3 months
        ll = util.since_date_last_n_months(now, 3) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since last 3 months')))

        ## Last six months
        ll = util.since_date_last_n_months(now, 6) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since last 6 months')))

        ## This year
        ll = util.since_date_this_year(now) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since last year')))

        ## Two years ago
        ll = util.since_date_past_n_years_ago(now, 2) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since two years ago')))

        ## Three years ago
        ll = util.since_date_past_n_years_ago(now, 3) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since three years ago')))

        ## Five years ago
        ll = util.since_date_past_n_years_ago(now, 5) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since five years ago')))

        ## Ten years ago
        ll = util.since_date_past_n_years_ago(now, 10) # lower limit
        key = f"{dt2str(ll)}-{dt2str(ul)}"
        model.append(Date(id=key, title=_('Since ten years ago')))

        ## All documents
        key = "All-All"
        model.append(Date(id=key, title=_('All documents')))

    def _setup_columnview(self):
        self.view = MiAZColumnViewWorkspace(self.app)
        self.app.add_widget('workspace-view', self.view)
        self.view.get_style_context().add_class(class_name='monospace')
        self.view.set_filter(self._do_filter_view)
        return self.view

    def _setup_workspace(self):
        factory = self.app.get_service('factory')
        widget = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        head = factory.create_box_vertical(margin=0, spacing=0, hexpand=True)
        body = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        foot = factory.create_box_vertical(margin=0, spacing=0, hexpand=False, vexpand=False)
        widget.append(head)
        widget.append(body)
        widget.append(foot)

        # Documents columnview
        frmView = self._setup_columnview()
        body.append(frmView)

        # Setup columnview
        self.view.column_title.set_visible(False)
        self.view.column_subtitle.set_visible(True)
        self.view.column_subtitle.set_expand(True)
        self.view.column_group.set_visible(True)
        self.view.column_purpose.set_visible(True)
        self.view.column_sentby.set_visible(True)
        self.view.column_sentto.set_visible(True)
        self.view.column_sentto.set_expand(False)
        self.view.column_sentby.set_expand(False)
        self.view.column_date.set_visible(True)

        self.append(widget)

    def get_selected_items(self):
        return self.selected_items

    def update(self, *args):
        """Update Workspace columnview"""

        #Load necessary services
        util = self.app.get_service('util')

        # No update while app is bussy
        if self.app.get_status() == MiAZStatus.BUSY:
            return

        # No update is no repository is loaded
        repository = self.app.get_service('repo')
        if repository.conf is None:
            return

        ds = datetime.now() # Measure performance (start timestamp)

        # Get list of files from current repository
        self.selected_items = []
        try:
            docs = util.get_files(repository.docs)
        except KeyError:
            docs = []

        # Initialize variables
        items = []      # Valid items
        invalid = []    # Invalid items

        keys_used = {}
        key_fields = [('Date', 0), ('Country', 1), ('Group', 2), ('SentBy', 3), ('Purpose', 4), ('Concept', 5), ('SentTo', 6)]
        for skey, nkey in key_fields:
            keys_used[skey] = set() # Avoid duplicates

        desc = {}
        concepts_active = set()
        concepts_inactive = set()
        show_pending = False

        for filename in docs:
            # ~ self.log.debug(f"{filename}")
            doc, ext = util.filename_details(filename)
            fields = doc.split('-')
            if util.filename_validate(doc):
                active = True
                for skey, nkey in key_fields:
                    config = self.app.get_config(skey)
                    key = fields[nkey]
                    if nkey == 0:
                        # Date field cached value differs from other fields
                        key = fields[nkey]
                        try:
                            desc[skey] = self.cache[skey][key]
                        except KeyError:
                            desc[skey] = util.filename_date_human_simple(key)
                            if desc[skey] is None:
                                active &= False
                                desc[skey] = ''
                            else:
                                self.cache[skey][key] = desc[skey]
                    elif nkey != 5:
                        description = config.get(key)
                        if description is None:
                            description = key
                        desc[skey] = description
                        active &= config.exists_used(key=key)
            else:
                invalid.append(filename)
                active &= False

            show_pending |= not active

            try:
                items.append(MiAZItem
                                    (
                                        id=os.path.basename(filename),
                                        date=fields[0],
                                        date_dsc=desc['Date'],
                                        country=fields[1],
                                        country_dsc=desc['Country'],
                                        group=fields[2],
                                        group_dsc=desc['Group'],
                                        sentby_id=fields[3],
                                        sentby_dsc=desc['SentBy'],
                                        purpose=fields[4],
                                        purpose_dsc=desc['Purpose'],
                                        title=doc,
                                        subtitle=fields[5].replace('_', ' '),
                                        sentto_id=fields[6],
                                        sentto_dsc=desc['SentTo'],
                                        active=active
                                    )
                            )
                if active:
                    concepts_active.add(fields[5].replace('_', ' '))
                else:
                    concepts_inactive.add(fields[5].replace('_', ' '))
            except (IndexError, KeyError):
                items.append(MiAZItem
                                    (
                                        id=os.path.basename(filename),
                                        date='',
                                        date_dsc='',
                                        country='',
                                        country_dsc='',
                                        group='',
                                        group_dsc='',
                                        sentby_id='',
                                        sentby_dsc='',
                                        purpose='',
                                        purpose_dsc='',
                                        title=doc,
                                        subtitle='_'.join(fields),
                                        sentto_id='',
                                        sentto_dsc='',
                                        active=False
                                    )
                            )

        ENV['CACHE']['CONCEPTS']['ACTIVE'] = sorted(concepts_active)
        ENV['CACHE']['CONCEPTS']['INACTIVE'] = sorted(concepts_inactive)

        GLib.idle_add(self.view.update, items)
        # ~ self._on_filter_selected()
        # ~ self.view.select_first_item()
        renamed = 0
        for filename in invalid:
            source = os.path.join(repository.docs, filename)
            btarget = util.filename_normalize(filename)
            target = os.path.join(repository.docs, btarget)
            rename = util.filename_rename(source, target)
            if rename:
                renamed += 1
        if renamed > 0:
            self.log.debug(f"Documents renamed: {renamed}")

        # ~ self.selected_items = []

        review = 0
        for item in items:
            if not item.active:
                review += 1
        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        togglebutton.set_label(f"Review ({review})")
        if show_pending:
            self.log.debug("There are pending documents. Displaying warning button")
        togglebutton.set_visible(show_pending)

        if not show_pending:
            togglebutton.set_active(False)
        self.review = togglebutton.get_active()
        self.app.set_status(MiAZStatus.RUNNING)

        # Measure performance (end timestamp and result)
        de = datetime.now()
        dt = de - ds
        self.log.debug(f"Workspace updated in {dt}s")

        self.emit('workspace-view-updated')
        return False

    def _do_eval_cond_matches_freetext(self, item):
        entry = self.app.get_widget('searchentry')
        left = entry.get_text()
        right = item.search_text
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
        util = self.app.get_service('util')
        # Convert timestamp to timedate object and cache it
        try:
            item_dt = self.datetimes[item.date]
        except KeyError:
            item_dt = util.string_to_datetime(item.date)
            self.datetimes[item.date] = item_dt

        # Check if the date belongs to the lower/upper limit
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        selected = dd_date.get_selected_item()
        if selected is None:
            # ~ FIXME: Dropdown {dd_date} with selected item '{selected}' shouldn't be None"
            return False
        period = selected.id
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
            start = util.string_to_datetime(ll)
            end = util.string_to_datetime(ul)
            if item_dt >= start and item_dt <= end:
                matches = True
            else:
                matches = False
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

    def _do_eval_cond_matches_active(self, item):
        return item.active

    def _do_filter_view(self, item, filter_list_model):
        dropdowns = self.app.get_widget('ws-dropdowns')
        if self.review:
            c0 = self._do_eval_cond_matches_freetext(item)
            # ~ cd = self._do_eval_cond_matches_date(item)
            c1 = self._do_eval_cond_matches(dropdowns['Country'], item.country)
            c2 = self._do_eval_cond_matches(dropdowns['Group'], item.group)
            c4 = self._do_eval_cond_matches(dropdowns['SentBy'], item.sentby_id)
            c5 = self._do_eval_cond_matches(dropdowns['Purpose'], item.purpose)
            c6 = self._do_eval_cond_matches(dropdowns['SentTo'], item.sentto_id)
            return not item.active and c0 and c1 and c2 and c4 and c5 and c6
        else:
            projects = self.app.get_service('Projects')
            # ~ dropdowns = self.app.get_widget('ws-dropdowns')
            dd_prj = dropdowns[Project.__gtype_name__]

            try:
                project = dd_prj.get_selected_item().id
            except AttributeError:
                project = 'Any'

            if project != 'None':
                ca = self._do_eval_cond_matches_active(item)
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
                show_item = ca and c0 and c1 and c2 and c4 and c5 and c6 and cd and cp
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
        searchentry = self.app.get_widget('searchentry')
        searchentry.connect('changed', self._on_filter_selected)
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
        workspace_menu = self.app.get_widget('workspace-menu')
        app_status = self.app.get_status()
        util = self.app.get_service('util')
        repository = self.app.get_service('repo')

        if repository.conf is None:
            return

        status = self.app.get_status()
        if status == MiAZStatus.BUSY:
            return

        if self.workspace_loaded:
            self.view.refilter()
            model = self.view.cv.get_model() # nº items in current view
            self._num_selected_items = len(self.selected_items)
            self._num_displayed_items = len(model)
            self._num_total_items = len(util.get_files(repository.docs)) # nº total items
            self.emit('workspace-view-filtered')

    def _on_selection_changed(self, selection, position, n_items):
        repository = self.app.get_service('repo')
        util = self.app.get_service('util')
        self.selected_items = []
        model = selection.get_model()
        bitset = selection.get_selection()
        for index in range(bitset.get_size()):
            pos = bitset.get_nth(index)
            item = model.get_item(pos)
            self.selected_items.append(item)
        self._on_filter_selected()
        # ~ self._num_selected_items = len(self.selected_items)
        # ~ self._num_displayed_items = len(model)
        # ~ self._num_total_items = len(util.get_files(repository.docs)) # nº total items
        # ~ self.emit('workspace-view-selection-changed')

    def get_num_selected_items(self):
        return self._num_selected_items

    def get_num_total_items(self):
        return self._num_total_items

    def get_num_displayed_items(self):
        return self._num_displayed_items

    def _on_select_all(self, *args):
        selection = self.view.get_selection()
        selection.select_all()

    def _on_select_none(self, *args):
        selection = self.view.get_selection()
        selection.unselect_all()

    def _on_application_finished(self, *args):
        util = self.app.get_service('util')
        util.json_save(self.fcache, self.cache)
        self.log.debug(f"Workspace cache saved to {self.fcache}")
