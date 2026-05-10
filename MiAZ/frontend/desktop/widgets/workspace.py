#!/usr/bin/python3
# File: workspace.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The central place to manage the AZ

import os
from datetime import datetime, timedelta
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, SentBy, SentTo, Date
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepoSettings
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo
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
Configview['Date'] = Gtk.Calendar


class MiAZWorkspace(Gtk.Box):
    """Workspace"""
    __gtype_name__ = 'MiAZWorkspace'
    __gsignals__ = {
        "workspace-loaded":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "workspace-view-updated": (GObject.SignalFlags.RUN_LAST, None, ()),
        "workspace-view-selection-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "workspace-view-filtered": (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    _workspace_filters = {}
    _num_selected_items = 0
    _num_displayed_items = 0
    _num_total_items = 0
    workspace_loaded = False
    selected_items = []
    dates = {}
    cache = {}
    uncategorized = False
    pending = False

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.log = MiAZLog('MiAZ.Workspace')
        self.log.debug("Initializing widget Workspace!!")
        self.app = app
        self.config = self.app.get_config_dict()
        self.used_signals = {}
        self._repo_switch_signals = {}
        self._finish_config_done = False
        self._clearing_filters = False
        self._updating_dropdowns = False
        self._filter_in_progress = False
        self._dropdown_update_pending = False
        self._setup_workspace()
        self._setup_logic()
        self._review = False
        self._was_pending = None
        self._cached_dropdowns = None
        self._cached_search_text = ''
        self._cached_date_ll = 'All'
        self._cached_date_ul = 'All'
        self._cached_date_start = None
        self._cached_date_end = None

        # Allow plug-ins to make their job
        self.connect('workspace-view-updated', self._on_filter_selected)
        self.app.connect('application-started', self._on_finish_configuration)
        self.app.connect('application-finished', self._on_application_finished)

        self.connect('workspace-loaded', self._on_loaded)

    def _on_loaded(self, *args):
        pass

    def initialize_caches(self):
        repo = self.app.get_service('repo')

        self.datetimes = {}

        if repo.conf is None:
            return
        self.fcache = os.path.join(repo.conf, 'cache.json')
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
        dd_date.set_selected(0)
        dd_date.connect("notify::selected-item", self.update)

        ## Rest of dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = dropdowns[i_type]
            actions.dropdown_populate(  config=self.config,
                                        dropdown=dropdowns[i_type],
                                        item_type=item_type,
                                        any_value=True,
                                        none_value=True)
            dropdown.connect("notify::selected-item", self._on_filter_selected)
            self.used_signals[i_type] = self.config[i_type].connect('used-updated', self.update_dropdown_filter, item_type)

        # Connect Watcher service
        watcher = self.app.get_service('watcher')
        watcher.connect('repository-updated', self._on_workspace_update)

        # Connect Repository
        repository = self.app.get_service('repo')
        repository.connect('repository-switched', self._update_dropdowns)

        # Observe config changes
        for node in self.config:
            self.config[node].connect('used-updated', self._on_config_used_updated)

        # Trigger events
        self._do_connect_filter_signals()
        self.workspace_loaded = True

    def _on_finish_configuration(self, *args):
        self.log.debug("Finishing loading workspace")
        window = self.app.get_widget('window')
        window.present()
        if not self._finish_config_done:
            self._finish_config_done = True
            workflow = self.app.get_service('workflow')
            srvutl = self.app.get_service('util')
            srvutl.connect('filename-renamed', self.update)
            srvutl.connect('filename-deleted', self.update)
            srvutl.connect('filename-added', self.update)
            workflow.connect('repository-switch-started', self._on_repo_switch)
        self._on_repo_switch()
        self.emit('workspace-loaded')

    def _on_repo_switch(self, *args):
        self.selected_items = []
        self.update()
        for node in self.config:
            if node in self._repo_switch_signals:
                prev_obj, sid_used, sid_avail = self._repo_switch_signals[node]
                if prev_obj is self.config[node]:
                    prev_obj.disconnect(sid_used)
                    prev_obj.disconnect(sid_avail)
            sid_used = self.config[node].connect('used-updated', self.update)
            sid_avail = self.config[node].connect('available-updated', self.update)
            self._repo_switch_signals[node] = (self.config[node], sid_used, sid_avail)

    def _update_dropdowns(self, *args):
        actions = self.app.get_service('actions')
        dropdowns = self.app.get_widget('ws-dropdowns')
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            config = self.config[i_type]
            actions.dropdown_populate(  config=config,
                                    dropdown=dropdowns[i_type],
                                    item_type=item_type,
                                    any_value=True,
                                    none_value=True)

    def _on_workspace_update(self, *args):
        GLib.idle_add(self.update)

    def is_loaded(self):
        return self.workspace_loaded

    def unselect_items(self):
        self.selected_items = []

    def update_dropdown_filter(self, config, item_type):
        actions = self.app.get_service('actions')
        dropdowns = self.app.get_widget('ws-dropdowns')
        i_type = item_type.__gtype_name__
        actions.dropdown_populate(  config=config,
                                    dropdown=dropdowns[i_type],
                                    item_type=item_type,
                                    any_value=True,
                                    none_value=True)

    def show_pending_documents(self, *args):
        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        self._review = togglebutton.get_active()

        # Clear filters
        sidebar = self.app.get_widget('sidebar')
        sidebar.clear_filters()

        # Show all documents in review mode
        i_type = Date.__gtype_name__
        dropdowns = self.app.get_widget('ws-dropdowns')
        if self._review:
            dd = dropdowns[i_type]
            model = dd.get_model()
            for i in range(model.get_n_items()):
                if model.get_item(i).id == 'All-All':
                    dd.set_selected(i)
                    break

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

        ## Future (tomorrow onwards)
        ll = now + timedelta(days=1)
        key = f"{dt2str(ll)}-99991231"
        model.append(Date(id=key, title=_('Future')))

        ## All documents
        key = "All-All"
        model.append(Date(id=key, title=_('All documents')))

    def _setup_columnview(self):
        frame = Gtk.Frame()
        self.view = MiAZColumnViewWorkspace(self.app)
        self.app.add_widget('workspace-view', self.view)
        self.view.get_style_context().add_class(class_name='monospace')
        self._workspace_filters['main'] = self._do_filter_view_main
        self.view.set_filter(self._do_filter_view)
        frame.set_child(self.view)

        return frame

    def register_filter_view(self, name: str, callback):
        registered = False
        if name not in self._workspace_filters:
            self._workspace_filters[name] = callback
            self.log.debug(f"Added new workspace filter: {name}")
            registered = True
        else:
            self.log.error(f"Workspace filter {name} already registered. Skip.")
        return registered

    def unregister_filter_view(self, name):
        unregistered = False
        if name in self._workspace_filters:
            del(self._workspace_filters[name])
            unregistered = True
        else:
            self.log.error(f"Workspace filter {name} was not registered. Skip.")
        return unregistered

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
        self.append(widget)
        self.set_default_columnview_attrs()
        self.get_style_context().add_class(class_name='toolbar')

    def set_default_columnview_attrs(self):
        # Setup columnview
        self.view.column_country.set_visible(False)
        self.view.column_flag.set_visible(True)
        self.view.column_icon_type.set_visible(True)
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
        self.view.column_extension.set_visible(False)

    def get_workspace_view(self):
        return self.view

    def get_selected_items(self):
        return self.selected_items

    def clear_filters(self):
        """Reset every filter control atomically, then refilter once."""
        search_entry = self.app.get_widget('searchentry')
        dropdowns = self.app.get_widget('ws-dropdowns') or {}
        plugin_dropdowns = self.app.get_widget('plugin-dropdowns') or []

        self._clearing_filters = True
        try:
            search_entry.set_text('')
            for dd in dropdowns.values():
                dd.set_selected(0)
            for dd in plugin_dropdowns:
                dd.set_selected(0)
        finally:
            self._clearing_filters = False

        self._refresh_filter_cache()
        self.view.refilter()
        self.emit('workspace-view-filtered')
        self._update_dropdowns_after_filter()

    def update(self, *args):
        """Update Workspace columnview"""
        if self._clearing_filters:
            return

        #Load necessary services
        util = self.app.get_service('util')

        # No update while app is busy (expected during startup/plugin loading)
        if self.app.get_status() == MiAZStatus.BUSY:
            if self.app.get_plugins_loaded():
                self.log.warning("App is busy. Workspace not updated")
            return

        self.app.set_status(MiAZStatus.BUSY)

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
                active = False

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
                                        title=doc, #f'{doc}.{ext}',
                                        subtitle=fields[5].replace('_', ' '),
                                        sentto_id=fields[6],
                                        sentto_dsc=desc['SentTo'],
                                        extension = filename[filename.rfind('.')+1:],
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
                                        title=doc, #f'{doc}.{ext}',
                                        subtitle='_'.join(fields),
                                        sentto_id='',
                                        sentto_dsc='',
                                        extension = filename[filename.rfind('.')+1:],
                                        active=active
                                    )
                            )

        ENV['CACHE']['CONCEPTS']['ACTIVE'] = sorted(concepts_active)
        ENV['CACHE']['CONCEPTS']['INACTIVE'] = sorted(concepts_inactive)

        # Update workspace view — refresh filter cache before handing off to the view
        self._refresh_filter_cache()
        self._num_total_items = len(docs)
        GLib.idle_add(self._idle_view_update, items)

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

        review = 0
        for item in items:
            if not item.active:
                review += 1

        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        togglebutton.set_label(_("Review ({review})").format(review=review))
        style_ctx = togglebutton.get_style_context()
        if show_pending:
            style_ctx.add_class('destructive-action')
            style_ctx.remove_class('flat')
        else:
            style_ctx.remove_class('destructive-action')
            style_ctx.add_class('flat')
        if show_pending != self._was_pending:
            if show_pending:
                self.log.debug("Pending documents detected — showing Review button")
            else:
                self.log.debug("No pending documents — hiding Review button")
            self._was_pending = show_pending
        togglebutton.set_visible(show_pending)

        if not show_pending:
            togglebutton.set_active(False)
        self._review = togglebutton.get_active()

        # Measure performance (end timestamp and result)
        de = datetime.now()
        dt = de - ds
        self.log.debug(f"Workspace updated in {dt}s")

        self.app.set_status(MiAZStatus.RUNNING)
        return False

    def _idle_view_update(self, items):
        """Apply the store splice and emit the updated signal with correct post-filter counts."""
        self.view.update(items)
        model = self.view.cv.get_model()
        self._num_selected_items = len(self.selected_items)
        self._num_displayed_items = len(model)
        self.emit('workspace-view-updated')
        return False

    def _refresh_filter_cache(self):
        """Pre-compute per-filter-pass constants so per-item callbacks are cheap."""
        util = self.app.get_service('util')
        self._cached_dropdowns = self.app.get_widget('ws-dropdowns')
        entry = self.app.get_widget('searchentry')
        self._cached_search_text = entry.get_text()

        dd_date = self._cached_dropdowns[Date.__gtype_name__]
        selected = dd_date.get_selected_item()
        if selected is None:
            self._cached_date_ll = 'All'
            self._cached_date_ul = 'All'
            self._cached_date_start = None
            self._cached_date_end = None
        else:
            ll, ul = selected.id.split('-')
            self._cached_date_ll = ll
            self._cached_date_ul = ul
            if ll not in ('All', 'None') and ul not in ('All', 'None'):
                self._cached_date_start = util.string_to_datetime(ll)
                self._cached_date_end = util.string_to_datetime(ul)
            else:
                self._cached_date_start = None
                self._cached_date_end = None

    def _do_eval_cond_matches_freetext(self, item):
        return self._cached_search_text.upper() in item.search_text.upper()

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
        try:
            item_dt = self.datetimes[item.date]
        except KeyError:
            util = self.app.get_service('util')
            item_dt = util.string_to_datetime(item.date)
            self.datetimes[item.date] = item_dt

        ll, ul = self._cached_date_ll, self._cached_date_ul
        if ll == 'All' and ul == 'All':
            return True
        elif ll == 'None' and ul == 'None':
            return item_dt is None
        elif item_dt is None:
            return False
        return self._cached_date_start <= item_dt <= self._cached_date_end

    def _do_eval_cond_matches_active(self, item):
        # ~ self.log.warning(f"\t\t{item.id} active? {item.active}") # DEBUG FILTERS
        return item.active

    def _do_filter_view(self, item, filter_list_model):
        show_item = True
        lresults = []
        for name in self._workspace_filters:
            filter_func = self._workspace_filters[name]
            result = filter_func(item, filter_list_model)
            lresults.append(f"{name}[{result}]")
            show_item = show_item and result
        # DEBUG FILTERS
        # ~ msg = '\t\t' + ' and '.join(lresults) # DEBUG FILTERS
        # ~ msg += f" = {show_item}" # DEBUG FILTERS
        # ~ self.log.error(msg)
        return show_item

    def _do_filter_view_main(self, item, filter_list_model):
        show_item = False
        dropdowns = self._cached_dropdowns
        c0 = self._do_eval_cond_matches_freetext(item)
        ca = self._do_eval_cond_matches_active(item)
        cd = self._do_eval_cond_matches_date(item)
        c1 = self._do_eval_cond_matches(dropdowns['Country'], item.country)
        c2 = self._do_eval_cond_matches(dropdowns['Group'], item.group)
        c4 = self._do_eval_cond_matches(dropdowns['SentBy'], item.sentby_id)
        c5 = self._do_eval_cond_matches(dropdowns['Purpose'], item.purpose)
        c6 = self._do_eval_cond_matches(dropdowns['SentTo'], item.sentto_id)

        # When a specific project is selected, bypass the date and active checks:
        # project members may have unrecognised field values (ca=False) or any date.
        project_dd = self.app.get_widget('plugin-MiAZProjectMgt-dropdown')
        if project_dd is not None:
            sel = project_dd.get_selected_item()
            if sel is not None and sel.id not in ('Any', 'None'):
                cd = True
                ca = True

        if self._review:
            show_item = not ca and c0 and c1 and c2 and c4 and c5 and c6
        else:
            show_item = ca and c0 and c1 and c2 and c4 and c5 and c6 and cd

        # DEBUG FILTERS
        # ~ self.log.warning(f"{item.id}: prj[{sel.id}]\tc0[{c0}] ca[{ca}] cd[{cd}] c1[{c1}] c2[{c2}] c4[{c4}] c5[{c5}] c6[{c6}] = {show_item}") # DEBUG FILTERS
        return show_item

    def _do_connect_filter_signals(self):
        searchentry = self.app.get_widget('searchentry')
        searchentry.connect('changed', self._on_filter_selected)
        dropdowns = self.app.get_widget('ws-dropdowns')
        for dropdown in dropdowns:
            dropdowns[dropdown].connect("notify::selected-item", self._on_filter_selected)
        selection = self.view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def _update_dropdowns_after_filter(self):
        """Rebuild the five field dropdowns to contain only values
        present in the current workspace view"""
        if self._clearing_filters or self._updating_dropdowns:
            return

        self._updating_dropdowns = True
        try:
            filter_model = self.view.filter_model
            n = filter_model.get_n_items()

            field_values = {
                Country: {},
                Group: {},
                SentBy: {},
                Purpose: {},
                SentTo: {},
            }

            for i in range(n):
                item = filter_model.get_item(i)
                if item.country:
                    field_values[Country][item.country] = item.country_dsc or item.country
                if item.group:
                    field_values[Group][item.group] = item.group_dsc or item.group
                if item.sentby_id:
                    field_values[SentBy][item.sentby_id] = item.sentby_dsc or item.sentby_id
                if item.purpose:
                    field_values[Purpose][item.purpose] = item.purpose_dsc or item.purpose
                if item.sentto_id:
                    field_values[SentTo][item.sentto_id] = item.sentto_dsc or item.sentto_id

            dropdowns = self.app.get_widget('ws-dropdowns')
            for item_type, values in field_values.items():
                i_type = item_type.__gtype_name__
                dropdown = dropdowns[i_type]
                i_title = _(item_type.__title__)

                selected_item = dropdown.get_selected_item()
                selected_id = selected_item.id if selected_item else 'Any'

                # Model chain: FilterListModel → SortListModel → ListStore
                model_filter = dropdown.get_model()
                model_sort = model_filter.get_model()
                model = model_sort.get_model()

                new_items = [
                    item_type(id='Any', title=_('Any') + ' ' + i_title.lower()),
                    item_type(id='None', title=_('None') + ' ' + i_title.lower()),
                ]
                for key in sorted(values.keys()):
                    title = values[key]
                    new_items.append(item_type(id=key, title=title if title else key))
                model.splice(0, model.get_n_items(), new_items)

                n_dd = model_filter.get_n_items()
                reselected = False
                for pos in range(n_dd):
                    dd_item = model_filter.get_item(pos)
                    if dd_item and dd_item.id == selected_id:
                        dropdown.set_selected(pos)
                        reselected = True
                        break
                if not reselected:
                    dropdown.set_selected(0)
        finally:
            self._updating_dropdowns = False

    def _idle_update_dropdowns(self):
        self._dropdown_update_pending = False
        # When a filter changes, update values of the others
        self._update_dropdowns_after_filter()
        return False

    def _on_filter_selected(self, *args):
        # Do nothing if filters are being updated
        if self._clearing_filters or self._updating_dropdowns or self._filter_in_progress:
            return

        repository = self.app.get_service('repo')

        # Do nothing if no repository is loaded
        if repository.conf is None:
            return

        # Do nothing if MiAZ is busy updating workspace
        if self.app.get_status() == MiAZStatus.BUSY:
            return

        self._filter_in_progress = True
        try:
            if self.workspace_loaded:
                self._refresh_filter_cache()
                self.view.refilter()
                model = self.view.cv.get_model()
                self._num_selected_items = len(self.selected_items)
                self._num_displayed_items = len(model)
                if not self._dropdown_update_pending:
                    self._dropdown_update_pending = True
                    GLib.idle_add(self._idle_update_dropdowns)
                self.emit('workspace-view-filtered')
        finally:
            self._filter_in_progress = False

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

    def get_workspace_filters(self):
        return self._workspace_filters
