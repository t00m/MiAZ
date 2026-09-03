# File: workspace.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The central place to manage the AZ

import os
from collections import namedtuple
from datetime import datetime
from gettext import gettext as _

# Minimal object for removing a store item by id (MiAZColumnView matches on .id).
_ItemRef = namedtuple('_ItemRef', ['id'])

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from MiAZ.env import ENV
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country, Purpose, SentBy, SentTo, Date
from MiAZ.backend.gate import UpdateGate
from MiAZ.backend.query import (
    ANY, DATE_ALL, DATE_NONE, DATE_RANGE, DocumentQuery,
    DATE_PRESET_THIS_MONTH, DATE_PRESET_PAST_MONTH, DATE_PRESET_LAST_3_MONTHS,
    DATE_PRESET_LAST_6_MONTHS, DATE_PRESET_LAST_12_MONTHS, DATE_PRESET_2_YEARS,
    DATE_PRESET_3_YEARS, DATE_PRESET_5_YEARS, DATE_PRESET_10_YEARS,
    DATE_PRESET_FUTURE, DATE_PRESET_ALL, resolve_preset)
from MiAZ.backend.tasks import run_in_background
from MiAZ.frontend.desktop.widgets.browserpage import MiAZBrowserPage
from MiAZ.frontend.desktop.widgets.chip import MiAZChip
from MiAZ.frontend.desktop.widgets.docpreview import MiAZDocPreview
from MiAZ.frontend.desktop.widgets.conversationview import MiAZConversationView
from MiAZ.frontend.desktop.widgets.filenamesview import MiAZFilenamesView
from MiAZ.frontend.desktop.widgets.gridview import MiAZGridView
from MiAZ.frontend.desktop.widgets.pills import FIELD_COLORS
from MiAZ.frontend.desktop.widgets.timelineview import MiAZTimelineView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo
from MiAZ.backend.status import MiAZStatus

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Date'] = Gtk.Calendar


def pick_date_preset(current_index, item_dates, presets):
    """Choose the date preset to select so the workspace is not shown empty.

    `presets` is the dropdown list, in order, of `(kind, start, end)` where kind
    is 'bounded', 'future' or 'all'; `start`/`end` are inclusive `datetime.date`
    bounds for 'bounded' and `None` otherwise. `item_dates` is a list of
    `datetime.date`, one per document. `current_index` is the selected preset.

    If the current preset already contains a document it is kept. Otherwise the
    presets are walked from `current_index` towards wider windows (the bounded
    chain is nested, so the nearest non-empty preset is always wider), skipping
    any 'future' preset, and the first 'bounded' preset that contains a document
    is returned. If none does, the 'all' preset is returned when it has
    documents. When nothing matches (empty repository) `current_index` is
    returned unchanged.
    """
    def contains(preset):
        kind, start, end = preset
        if kind == 'all':
            return bool(item_dates)
        if kind == 'future':
            return start is not None and any(d >= start for d in item_dates)
        return any(start <= d <= end for d in item_dates)

    if not presets or not (0 <= current_index < len(presets)):
        return current_index
    if contains(presets[current_index]):
        return current_index
    all_index = None
    for i in range(current_index, len(presets)):
        kind = presets[i][0]
        if kind == 'future':
            continue
        if kind == 'all':
            all_index = i
            continue
        if contains(presets[i]):
            return i
    if all_index is not None and contains(presets[all_index]):
        return all_index
    return current_index


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
    _filter_tag_css_installed = False
    _drop_target_css_installed = False
    # Tags share the pill palette so a filter tag and a field pill match.
    _FILTER_TAG_COLORS = FIELD_COLORS
    selected_items = []
    dates = {}
    cache = {}
    uncategorized = False
    pending = False

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
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
        # Must exist before _setup_logic(), which builds the date presets and
        # reads these. The presets encode absolute days derived from "now";
        # _date_presets_day tracks the day they were built for (so update() can
        # rebuild them on rollover) and _sid_date_selected lets the rebuild block
        # re-entry via the selection signal.
        self._date_presets_day = None
        self._sid_date_selected = None
        # Armed at load / repo switch / rollover so _apply_parse_results picks the
        # nearest non-empty date preset once (never overriding a manual choice).
        self._auto_date_pending = False
        # What the view is filtered by. Rebuilt from the filter widgets once per
        # pass by _read_query, then read per item by _do_filter_view_main. Set
        # before the setup calls below, which install the filter and can run it.
        self._review = False
        self._query = DocumentQuery()
        self._query_hooks = {}
        # An explicit list of documents to show, put there by something that
        # already worked out which ones matter: a health check, a plugin.
        self._only_ids = None
        self._only_label = ''
        # Holds back refreshes while something does bulk work, and coalesces
        # them into one when the last holder releases. See suspend_updates().
        self._gate = UpdateGate(self.update)
        # True from the moment a scan is handed to a worker until its result
        # comes back. Guards re-entry only; it is not a global app state.
        self._scan_in_flight = False
        self._setup_workspace()
        self._setup_logic()
        self._was_pending = None
        self._update_pending = False
        self._update_timeout_id = None
        # Set by the incremental handler so the trailing full re-scan is skipped
        # when a per-file update already covered the change.
        self._skip_next_full_update = False

        # Allow plug-ins to make their job
        self.connect('workspace-view-updated', self._on_filter_selected)
        self.app.connect('application-started', self._on_finish_configuration)
        self.app.connect('application-finished', self._on_application_finished)
        self.connect('workspace-loaded', self._on_loaded)
        self.connect('workspace-view-filtered', self._update_filter_tags)
        self.connect('workspace-view-updated', self._update_filter_tags)

    def _on_loaded(self, *args):
        pass

    def initialize_caches(self):
        repo = self.app.get_service('repo')

        if repo.conf is None:
            return
        self.fcache = os.path.join(repo.conf, 'cache.json')
        self.app.get_service('index').invalidate_cache()
        self.log.debug("Caches initialized")

    def _on_config_used_updated(self, config, changed):
        """Drop the description cache entries for the keys that changed.

        Renaming one country used to clear the whole cache, so every document
        in the view had its six field descriptions rebuilt. The signal now says
        which keys moved, and only those go.

        'changed' is None when the config could not read its previous contents,
        which is the one case that still has to clear everything.
        """
        index = self.app.get_service('index')
        if changed is None:
            index.invalidate_cache()
            return
        model = getattr(config, 'model', None)
        name = getattr(model, '__gtype_name__', None)
        if name is None:
            index.invalidate_cache()
            return
        for key in changed:
            index.invalidate_cache(name, key)

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
        self._sid_date_selected = dd_date.connect("notify::selected-item", self.update)

        ## Rest of dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = dropdowns[i_type]
            actions.dropdown_populate(  config=self.config,
                                        dropdown=dropdowns[i_type],
                                        item_type=item_type,
                                        any_value=True,
                                        none_value=False)
            dropdown.connect("notify::selected-item", self._on_filter_selected)
            self.used_signals[i_type] = self.config[i_type].connect('used-updated', self.update_dropdown_filter, item_type)

        # Connect Watcher service. 'repository-changed' carries the changed path
        # for a targeted, incremental update; 'repository-updated' is the full
        # re-scan, kept as the safety net and skipped when the incremental path
        # already handled the change.
        watcher = self.app.get_service('watcher')
        watcher.connect('repository-changed', self._on_repository_item_changed)
        watcher.connect('repository-updated', self._on_workspace_update)

        # The index turns a filesystem event into store operations. A full
        # reload emits 'index-loaded' instead, so this never double-applies.
        index = self.app.get_service('index')
        index.connect('index-changed', self._on_index_changed)
        index.connect('duplicates-scanned', self._on_duplicates_scanned)

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
            srvutl = self.app.get_service('util')
            srvutl.connect('filename-renamed', self._schedule_update)
            srvutl.connect('filename-deleted', self._schedule_update)
            srvutl.connect('filename-added', self._schedule_update)
        # Every switch reaches here: switch_start emits 'application-started'
        # once the new repository is loaded and its caches are fresh, which is
        # the only point where reconnecting to the configurations picks up the
        # new objects rather than the ones being replaced. Listening to
        # 'repository-switch-started' instead would run this before the swap.
        self._on_repo_switch()
        self.emit('workspace-loaded')

    def _on_repo_switch(self, *args):
        self.selected_items = []
        # A fresh repository (also the initial load): let the next parse pick the
        # nearest non-empty date preset instead of showing an empty workspace.
        self._auto_date_pending = True
        self.update()
        for node in self.config:
            if node in self._repo_switch_signals:
                prev_obj, sid_used, sid_avail = self._repo_switch_signals[node]
                if prev_obj is self.config[node]:
                    prev_obj.disconnect(sid_used)
                    prev_obj.disconnect(sid_avail)
            sid_used = self.config[node].connect('used-updated', self._schedule_update)
            sid_avail = self.config[node].connect('available-updated', self._schedule_update)
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
                                    none_value=False)

    def _on_workspace_update(self, *args):
        # The watcher emits 'repository-changed' (handled incrementally) right
        # before this full-refresh signal. If the incremental path fully applied
        # the change, skip the O(N) re-scan; otherwise fall back to it.
        if self._skip_next_full_update:
            self._skip_next_full_update = False
            return
        self._schedule_update()

    def _schedule_update(self, *args):
        """Debounce rapid update requests into a single deferred execution."""
        self._update_pending = True
        if self._update_timeout_id is None:
            self._update_timeout_id = GLib.timeout_add(100, self._flush_update)

    def _flush_update(self):
        """Execute pending update if one was scheduled."""
        self._update_timeout_id = None
        if self._update_pending:
            self._update_pending = False
            self.update()
        return False

    def _on_repository_item_changed(self, watcher, path, other, event):
        """Apply a single-file change without re-scanning the whole repository.

        Sets the skip flag only when the change was fully applied, so the
        trailing 'repository-updated' full re-scan (which does a complete
        splice-replace) is skipped. On any doubt it does nothing and lets that
        full re-scan produce the correct view, so an imperfect incremental path
        can never corrupt the list, only cost a redundant re-scan.
        """
        try:
            if self._apply_incremental(path, other, event):
                self._skip_next_full_update = True
        except Exception as error:
            self.log.warning(f"Incremental update failed for '{path}': {error}")

    def _apply_incremental(self, path, other, event):
        """Return True if the single-file change was fully applied to the view.

        The index decides what the change means; this only translates its
        operations into store splices.
        """
        repository = self.app.get_service('repo')
        if repository.conf is None or repository.docs is None:
            return False

        index = self.app.get_service('index')
        return index.apply_change(path, event, other=other)

    def _on_index_changed(self, index, ops):
        """Translate the index operations into store splices."""
        splices = []
        for action, payload in ops:
            if action == 'remove':
                splices.append(('remove', _ItemRef(id=payload)))
                self._num_total_items = max(0, self._num_total_items - 1)
            else:
                splices.append((action, payload))
                if action == 'add':
                    self._num_total_items += 1
        self.view.update_incremental(splices)
        self._publish_concepts(index)
        self.emit('workspace-view-updated')

    def _on_duplicates_scanned(self, index, *args):
        """Show the column when there is something in it, and redraw.

        refilter re-binds every visible row, which is what re-runs the
        duplicate column's bind.
        """
        column = getattr(self.view, 'column_duplicate', None)
        if column is not None:
            column.set_visible(bool(index.duplicates_of_any()))
        self.view.refilter()

    def is_loaded(self):
        return self.workspace_loaded

    def unselect_items(self):
        self.selected_items = []

    def update_dropdown_filter(self, config, changed, item_type):
        # 'changed' is the key set the config signal carries. Repopulating reads
        # the whole file, so it is not needed here.
        actions = self.app.get_service('actions')
        dropdowns = self.app.get_widget('ws-dropdowns')
        i_type = item_type.__gtype_name__
        actions.dropdown_populate(  config=config,
                                    dropdown=dropdowns[i_type],
                                    item_type=item_type,
                                    any_value=True,
                                    none_value=False)

    def show_pending_documents(self, *args):
        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        self._review = togglebutton.get_active()

        # Clear filters
        sidebar = self.app.get_widget('sidebar')
        sidebar.clear_filters()

        # Show all documents in review mode. sidebar.clear_filters() already
        # triggered one full rescan; this only needs to change which date
        # range is visible, so the Date dropdown's rescan-triggering signal
        # is blocked here (its separate refilter-only signal stays connected
        # and applies the new range to the already-loaded items).
        i_type = Date.__gtype_name__
        dropdowns = self.app.get_widget('ws-dropdowns')
        if self._review:
            dd = dropdowns[i_type]
            model = dd.get_model()
            for i in range(model.get_n_items()):
                if model.get_item(i).id == 'All-All':
                    if self._sid_date_selected is not None:
                        dd.handler_block(self._sid_date_selected)
                    dd.set_selected(i)
                    if self._sid_date_selected is not None:
                        dd.handler_unblock(self._sid_date_selected)
                    break
        if self._review:
            self._scan_duplicates()

    def _scan_duplicates(self):
        """Mark documents whose bytes match another one, for review triage.

        Reads files, about 0.9s for 1336 documents, so it runs in a worker and
        only on entering review mode: a user who never opens it pays nothing.
        """
        index = self.app.get_service('index')
        if index is None or not index.duplicates_stale():
            return
        run_in_background(index.scan_duplicates,
                          on_error=lambda error: self.log.error(
                              f"Duplicate scan failed: {error}"),
                          name='workspace-duplicates')

    def _update_dropdown_date(self):
        util = self.app.get_service('util')
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        dt2str = util.datetime_to_string
        now = datetime.now().date()
        model_filter = dd_date.get_model()
        model_sort = model_filter.get_model()
        model = model_sort.get_model()

        # Preserve the selected preset across the rebuild by its title: the key
        # encodes the day and changes when the day rolls over, so it cannot be
        # matched by key. Block update() while the model is torn down and rebuilt
        # so the transient empty selection does not re-enter the filter pass.
        selected = dd_date.get_selected_item()
        selected_title = selected.title if selected is not None else None
        if self._sid_date_selected is not None:
            dd_date.handler_block(self._sid_date_selected)

        model.remove_all()

        # Each entry carries a stable token as well as its resolved range. The
        # id holds today's dates and the title is translated, so the token is
        # the only thing that still identifies an entry tomorrow, or in another
        # language. set_query() writes a query back to this dropdown by token.
        #
        # Only the labels live here. What a token means is query.resolve_preset,
        # so the sidebar and anything else asking the same question (the command
        # line, for one) cannot drift apart.
        titles = [
            (DATE_PRESET_THIS_MONTH, _('This month')),
            (DATE_PRESET_PAST_MONTH, _('Since past month')),
            (DATE_PRESET_LAST_3_MONTHS, _('Since last 3 months')),
            (DATE_PRESET_LAST_6_MONTHS, _('Since last 6 months')),
            # The last twelve months. This used to resolve through
            # since_date_this_year, so the label said "last year" while the
            # range was the calendar year to date: seven months on 7 August,
            # and two days on 2 January.
            (DATE_PRESET_LAST_12_MONTHS, _('Since last year')),
            (DATE_PRESET_2_YEARS, _('Since two years ago')),
            (DATE_PRESET_3_YEARS, _('Since three years ago')),
            (DATE_PRESET_5_YEARS, _('Since five years ago')),
            (DATE_PRESET_10_YEARS, _('Since ten years ago')),
            (DATE_PRESET_FUTURE, _('Future')),
        ]
        for token, title in titles:
            ll, ul = resolve_preset(token, now, util)
            model.append(Date(id=f"{dt2str(ll)}-{dt2str(ul)}", title=title,
                              preset=token))

        ## All documents
        model.append(Date(id="All-All", title=_('All documents'),
                          preset=DATE_PRESET_ALL))

        self._date_presets_day = now

        # Reselect the same preset by title (default to the first one), then
        # unblock update().
        target = 0
        if selected_title is not None:
            for i in range(model.get_n_items()):
                if model.get_item(i).title == selected_title:
                    target = i
                    break
        dd_date.set_selected(target)
        if self._sid_date_selected is not None:
            dd_date.handler_unblock(self._sid_date_selected)

        # The presets were (re)built (initial load or a day/month rollover): let
        # the next parse pick the nearest non-empty preset if the default is now
        # empty.
        self._auto_date_pending = True

    def _setup_columnview(self):
        frame = Gtk.Frame()
        self.view = MiAZColumnViewWorkspace(self.app)
        self.app.add_widget('workspace-view', self.view)
        self.view.add_css_class('monospace')
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
        # ViewStack for workspace-internal pages
        self._stack = Adw.ViewStack()
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        # Size to the page being shown, not to the widest page there is. A
        # homogeneous stack asked every page how wide it wanted to be, so one
        # plugin page wanting 519px set the floor for the whole window and
        # made a narrow window impossible.
        self._stack.set_hhomogeneous(False)
        self._stack.set_vhomogeneous(False)

        # Documents page. Details, Grid and Timeline are three shapes of the
        # same documents under the same filters, so they are buttons on a
        # toolbar inside this one page rather than tabs of their own: a tab
        # says "somewhere else", and none of them is somewhere else.
        frmView = self._setup_columnview()
        self._view_stack = Gtk.Stack()
        self._view_stack.set_hexpand(True)
        self._view_stack.set_vexpand(True)
        self._view_stack.set_hhomogeneous(False)
        self._view_stack.set_vhomogeneous(False)
        self._view_stack.add_named(frmView, 'details')

        grid = MiAZGridView(self.app)
        self._view_stack.add_named(grid, 'grid')
        self.app.add_widget('workspace-grid', grid)

        timeline = MiAZTimelineView(self.app)
        self._view_stack.add_named(timeline, 'timeline')
        self.app.add_widget('workspace-timeline', timeline)

        conversation = MiAZConversationView(self.app)
        self._view_stack.add_named(conversation, 'conversation')
        self.app.add_widget('workspace-conversation', conversation)
        filenames = MiAZFilenamesView(self.app)
        self._view_stack.add_named(filenames, 'filenames')
        self.app.add_widget('workspace-filenames', filenames)

        # What each view name shows. Details is a plain column view with no
        # set_active, so nothing is driven for it.
        self._views = {'details': None, 'grid': grid, 'timeline': timeline,
                       'conversation': conversation, 'filenames': filenames}

        self._view_stack.set_visible_child_name('details')
        self._view_stack.connect('notify::visible-child-name', self._on_view_changed)

        page_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        page_content.append(self._setup_view_toolbar())
        page_content.append(self._view_stack)
        documents_page = self._stack.add_titled(page_content, 'workspace-default', _('Documents'))
        documents_page.set_icon_name('io.github.t00m.MiAZ')
        self._setup_drop_target(page_content)

        # Browser page. Hidden from the view switcher when no plugin registers a
        # page to load, so only the Documents tab shows in that case.
        browser_widget = MiAZBrowserPage(self.app)
        browser_page = self._stack.add_titled(browser_widget, 'workspace-browser', _('Browser'))
        browser_page.set_icon_name('io.github.t00m.MiAZ-webbrowser')
        self.app.add_widget('workspace-browser', browser_widget)
        self._browser_page = browser_page
        browser_page.set_visible(browser_widget.has_pages())
        browser_widget.connect('pages-updated', self._on_browser_pages_updated)

        # InlineViewSwitcher
        self._switcher = self.app.get_widget('workspace-view-switcher')
        if self._switcher is not None:
            self._switcher.set_stack(self._stack)

        # Preview comes up from the bottom, not in from the side: a phone has
        # height to spare and no width, and a document list needs its columns.
        # Not modal, so the list stays usable and the preview follows the row
        # being clicked instead of blocking it.
        preview = MiAZDocPreview(self.app)
        self.app.add_widget('workspace-preview', preview)
        sheet = Adw.BottomSheet()
        sheet.set_hexpand(True)
        sheet.set_vexpand(True)
        sheet.set_modal(False)
        sheet.set_can_close(True)
        sheet.set_show_drag_handle(True)
        sheet.set_open(False)
        sheet.set_content(self._stack)
        sheet.set_sheet(preview)
        self.app.add_widget('workspace-preview-sheet', sheet)
        sheet.connect('notify::open', self._on_preview_open_changed)
        preview.connect('close-requested', lambda *_a: sheet.set_open(False))
        self.connect('workspace-view-selection-changed', self._update_preview)

        self.append(self._setup_filter_tags_bar())
        self.append(sheet)
        self.set_default_columnview_attrs()
        self.add_css_class('toolbar')
        self._stack.connect('notify::visible-child-name', self._on_stack_page_changed)
        self._on_stack_page_changed(self._stack, None)

    # The columns the View menu offers, in the order the table shows them.
    _COLUMNS = (
        ('column_date', _('Date')),
        ('column_country', _('Country')),
        ('column_flag', _('Flag')),
        ('column_icon_type', _('Type')),
        ('column_group', _('Group')),
        ('column_purpose', _('Purpose')),
        ('column_subtitle', _('Concept')),
        ('column_sentby', _('Sent by')),
        ('column_sentto', _('Sent to')),
        ('column_extension', _('Extension')),
    )

    # The shapes the documents can be shown in: stack name, icon, label.
    # Standard view icons, not the application icon and a magnifier: the
    # buttons have to say list, grid and chronology at a glance.
    # The views MiAZ ships. A plugin adds its own through add_view, and the
    # registry below is what every other part of this file walks.
    _BUILTIN_VIEWS = (
        ('details', 'view-list-symbolic', _('Details')),
        ('grid', 'view-grid-symbolic', _('Grid')),
        ('timeline', 'view-continuous-symbolic', _('Timeline')),
        ('conversation', 'mail-send-receive-symbolic', _('Conversations')),
        ('filenames', 'text-x-generic-symbolic', _('Filenames')),
    )

    def _setup_view_toolbar(self):
        """The toolbar above the documents.

        Views on the left, what acts on the documents in the middle, and what
        belongs to the current view on the right. The middle is filled by the
        main window, which owns those actions, and by plugins.
        """
        bar = Gtk.CenterBox()
        bar.set_margin_top(6)
        bar.set_margin_start(6)
        bar.set_margin_end(6)
        # The gap that keeps the toolbar off the documents underneath it.
        bar.set_margin_bottom(6)
        linked = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        linked.add_css_class('linked')
        self._view_buttons = {}
        first = None
        for name, icon_name, label in self._BUILTIN_VIEWS:
            button = Gtk.ToggleButton()
            button.set_icon_name(icon_name)
            button.set_tooltip_text(label)
            if first is None:
                first = button
            else:
                button.set_group(first)
            button.connect('toggled', self._on_view_button_toggled, name)
            self._view_buttons[name] = button
            linked.append(button)
        # Kept so a view added later joins the same radio group and the same box.
        self._view_button_group = first
        self._view_button_box = linked
        self._view_buttons['details'].set_active(True)
        # The Review toggle sits next to the views: it is another way of
        # choosing which documents are on screen. The main window makes it
        # and moves it here, the way it does with the document actions.
        start = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        start.append(linked)
        bar.set_start_widget(start)
        self.app.add_widget('workspace-view-buttons', linked)
        self.app.add_widget('workspace-toolbar-start', start)

        # What acts on the selected documents. The main window packs its
        # buttons here and plugins reach it through 'headerbar-right-box'.
        center = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        center.set_halign(Gtk.Align.CENTER)
        bar.set_center_widget(center)
        self.app.add_widget('workspace-toolbar-center', center)

        # What belongs to the view being shown: columns for Details, page size
        # for Grid. Only one of them is ever visible.
        end = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        end.set_halign(Gtk.Align.END)
        self._button_columns = self._setup_columns_menu()
        end.append(self._button_columns)
        grid = self.app.get_widget('workspace-grid')
        self._grid_controls = grid.get_size_controls()
        end.append(self._grid_controls)
        bar.set_end_widget(end)
        self.app.add_widget('workspace-toolbar-end', end)
        return bar

    def _setup_columns_menu(self):
        """The View menu: which columns the document table shows.

        One check item per column, kept in step with the column itself, so the
        menu always says what the table is actually doing.
        """
        menu = Gio.Menu.new()
        self._column_actions = {}
        for name, title in self._COLUMNS:
            column = getattr(self.view, name, None)
            if column is None:
                continue
            action = Gio.SimpleAction.new_stateful(
                f'column-{name}', None, GLib.Variant.new_boolean(column.get_visible()))
            action.connect('change-state', self._on_column_toggled, column)
            self.app.add_action(action)
            self._column_actions[name] = action
            menu.append(title, f'app.column-{name}')
        button = Gtk.MenuButton()
        button.set_icon_name('view-more-symbolic')
        button.set_tooltip_text(_('Choose the columns to show'))
        button.add_css_class('flat')
        button.set_menu_model(menu)
        self.app.add_widget('workspace-button-columns', button)
        return button

    def _on_column_toggled(self, action, value, column):
        action.set_state(value)
        column.set_visible(value.get_boolean())

    def _on_view_button_toggled(self, button, name):
        if button.get_active():
            self._view_stack.set_visible_child_name(name)

    def get_view_stack(self):
        return self._view_stack

    def get_current_view(self):
        return self._view_stack.get_visible_child_name()

    def show_view(self, name):
        """Show one of details, grid, timeline, conversation or filenames."""
        button = self._view_buttons.get(name)
        if button is not None:
            button.set_active(True)
        self._view_stack.set_visible_child_name(name)

    def get_views(self):
        """The registered view names, in the order their buttons appear."""
        return list(self._views)

    def add_view(self, name, icon_name, label, widget):
        """Register one more view beside the built-in ones.

        The widget joins the view stack and gets a toggle in the same linked
        box, in the same radio group, so it behaves like a view MiAZ ships.
        A widget with set_active is driven like the others: no model unless it
        is the view on screen.
        """
        if name in self._views:
            self.remove_view(name)
        button = Gtk.ToggleButton()
        button.set_icon_name(icon_name)
        button.set_tooltip_text(label)
        button.set_group(self._view_button_group)
        button.connect('toggled', self._on_view_button_toggled, name)
        self._view_buttons[name] = button
        self._view_button_box.append(button)
        self._view_stack.add_named(widget, name)
        self._views[name] = widget
        self.log.debug(f"Workspace view added: {name}")

    def remove_view(self, name):
        """Take a view away, falling back to Details when it was on screen."""
        built_in = {view[0] for view in self._BUILTIN_VIEWS}
        if name not in self._views or name in built_in:
            return
        if self._view_stack.get_visible_child_name() == name:
            self.show_view('details')
        widget = self._views.pop(name)
        if widget is not None and hasattr(widget, 'set_active'):
            widget.set_active(False)
        child = self._view_stack.get_child_by_name(name)
        if child is not None:
            self._view_stack.remove(child)
        button = self._view_buttons.pop(name, None)
        if button is not None:
            self._view_button_box.remove(button)
        self.log.debug(f"Workspace view removed: {name}")

    def _on_view_changed(self, *args):
        """Only the view on screen carries a model, so the others cost nothing."""
        name = self._view_stack.get_visible_child_name()
        button = self._view_buttons.get(name)
        if button is not None and not button.get_active():
            button.set_active(True)
        showing_documents = self._stack.get_visible_child_name() == 'workspace-default'
        for view_name, widget in self._views.items():
            if widget is not None:
                widget.set_active(showing_documents and name == view_name)
        # Columns belong to the table, page size to the grid.
        if getattr(self, '_button_columns', None) is not None:
            self._button_columns.set_visible(name == 'details')
        if getattr(self, '_grid_controls', None) is not None:
            self._grid_controls.set_visible(name == 'grid')

    def _on_preview_open_changed(self, sheet, _pspec):
        # The sheet can be closed by dragging it down, so the headerbar toggle
        # follows the sheet rather than being the only thing that knows.
        button = self.app.get_widget('headerbar-button-preview')
        if button is not None:
            button.set_active(sheet.get_open())
        self._update_preview()

    def _update_preview(self, *args):
        """Feed the preview panel while it is open; do nothing when closed."""
        preview = self.app.get_widget('workspace-preview')
        sheet = self.app.get_widget('workspace-preview-sheet')
        if preview is None or sheet is None or not sheet.get_open():
            return
        repo = self.app.get_service('repo')
        items = self.get_selected_items()
        if items:
            preview.set_document(os.path.join(repo.docs, os.path.basename(items[0].id)))
        else:
            preview.set_document(None)

    def _setup_filter_tags_bar(self):
        """Banner shown above the document list with the currently active
        sidebar filters rendered as removable tags."""
        self._install_filter_tag_css()

        flowbox = Gtk.FlowBox()
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_max_children_per_line(100)
        flowbox.set_column_spacing(6)
        flowbox.set_row_spacing(6)
        flowbox.set_halign(Gtk.Align.START)
        flowbox.set_margin_top(6)
        flowbox.set_margin_bottom(6)
        flowbox.set_margin_start(6)
        flowbox.set_margin_end(6)

        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        revealer.set_reveal_child(False)
        revealer.set_child(flowbox)

        self._filter_tags_flowbox = flowbox
        self._filter_tags_revealer = revealer
        self.app.add_widget('workspace-filter-tags', flowbox)
        self.app.add_widget('workspace-filter-tags-revealer', revealer)
        return revealer

    def _setup_drop_target(self, widget):
        """Accept files dropped on the documents page.

        Only that page: dropping on the Browser tab, or anywhere else in the
        window, does nothing, so the gesture means what it looks like, the
        files join the list you dropped them on.
        """
        self._install_drop_target_css()
        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect('enter', self._on_drop_enter, widget)
        drop.connect('leave', self._on_drop_leave, widget)
        drop.connect('drop', self._on_drop, widget)
        widget.add_controller(drop)
        self._drop_target = drop
        self.app.add_widget('workspace-drop-target', drop)

    def _install_drop_target_css(self):
        if MiAZWorkspace._drop_target_css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        css = (
            ".miaz-drop-active {"
            " background-image: image(alpha(currentColor, 0.08));"
            " outline: 2px dashed alpha(currentColor, 0.45);"
            " outline-offset: -4px; }"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        MiAZWorkspace._drop_target_css_installed = True

    def _on_drop_enter(self, drop, x, y, widget):
        widget.add_css_class('miaz-drop-active')
        return Gdk.DragAction.COPY

    def _on_drop_leave(self, drop, widget):
        widget.remove_css_class('miaz-drop-active')

    def _on_drop(self, drop, value, x, y, widget):
        widget.remove_css_class('miaz-drop-active')
        importdoc = self.app.get_service('importdoc')
        if importdoc is None:
            self.log.error("No import service: the dropped files were ignored")
            return False
        # A file dropped from a remote location has no local path, and Gio
        # gives None for it. The import service reports those as failed.
        paths = [gfile.get_path() for gfile in value.get_files()]
        self.log.debug(f"{len(paths)} paths dropped on the workspace")
        importdoc.import_dropped(paths)
        return True

    def _install_filter_tag_css(self):
        # Colors only; the base pill look comes from MiAZChip.
        if MiAZWorkspace._filter_tag_css_installed:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        parts = []
        for key, color in self._FILTER_TAG_COLORS.items():
            parts.append(f".miaz-chip-{key} {{ background-color: {color}; }}")
        css = "".join(parts)
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        MiAZWorkspace._filter_tag_css_installed = True

    def _create_filter_tag(self, dropdown_key, field_title, value_title):
        field = GLib.markup_escape_text(field_title)
        value = GLib.markup_escape_text(value_title)
        chip = MiAZChip(markup=f"<span alpha='65%'>{field}:</span> {value}",
                        style=dropdown_key)
        chip.set_tooltip_text(_('Remove filter: {field}').format(field=field_title))
        chip.connect('closed', self._on_filter_tag_clicked, dropdown_key)
        return chip

    def _on_filter_tag_clicked(self, button, dropdown_key):
        dropdowns = self.app.get_widget('ws-dropdowns') or {}
        dropdown = dropdowns.get(dropdown_key)
        if dropdown is not None:
            dropdown.set_selected(0)

    def _update_filter_tags(self, *args):
        """Rebuild the active-filter tags banner from the current dropdown state."""
        flowbox = getattr(self, '_filter_tags_flowbox', None)
        if flowbox is None:
            return

        while True:
            child = flowbox.get_first_child()
            if child is None:
                break
            flowbox.remove(child)

        dropdowns = self.app.get_widget('ws-dropdowns') or {}
        count = 0
        # An explicit list of documents is a filter like any other, so it is
        # shown like one and taken off the same way.
        if self._only_ids is not None:
            label = self._only_label or _('{count} documents').format(
                count=len(self._only_ids))
            chip = MiAZChip(
                markup=f"<span alpha='65%'>{GLib.markup_escape_text(_('Showing'))}:</span> "
                       f"{GLib.markup_escape_text(label)}",
                style='Concept')
            chip.set_tooltip_text(_('Show every document again'))
            chip.connect('closed', lambda *_a: self.clear_documents())
            flowbox.append(chip)
            count += 1
        for item_type in [Date, Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            dropdown = dropdowns.get(i_type)
            if dropdown is None:
                continue
            if item_type is not Date and dropdown.get_selected() == 0:
                continue
            item = dropdown.get_selected_item()
            if item is None:
                continue
            field_title = _(item_type.__title__)
            flowbox.append(self._create_filter_tag(i_type, field_title, item.title))
            count += 1
        self._filter_tags_revealer.set_reveal_child(count > 0)

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

    def get_stack(self):
        return self._stack

    def get_view_switcher(self):
        return self._switcher

    def add_stack_page(self, widget, name, title, icon_name=None):
        """Add a page, replacing any child already holding that name.

        Adw.ViewStack keys its children by name and warns on a duplicate, so a
        leftover page from an earlier owner is removed rather than reused. The
        caller passed a widget and expects to see that widget.
        """
        existing = self._stack.get_child_by_name(name)
        if existing is not None:
            if existing is widget:
                page = self._stack.get_page(widget)
                page.set_visible(True)
                return page
            self._stack.remove(existing)
        page = self._stack.add_titled(widget, name, title)
        if icon_name is not None:
            page.set_icon_name(icon_name)
        return page

    def remove_stack_page(self, name):
        """Take a page out of the stack, freeing its name.

        This used to only hide the child, so the name stayed taken for the life
        of the process and a plugin re-adding its page had to find the hidden
        one and adopt it instead.
        """
        child = self._stack.get_child_by_name(name)
        if child is not None:
            self._stack.remove(child)

    def get_stack_page(self, name):
        return self._stack.get_child_by_name(name)

    def show_stack_page(self, name):
        self._stack.set_visible_child_name(name)

    def _on_stack_page_changed(self, stack, _pspec):
        visible = stack.get_visible_child_name()
        # The filter-tags revealer applies only to the Documents view.
        revealer = getattr(self, '_filter_tags_revealer', None)
        if revealer is not None:
            revealer.set_visible(visible == 'workspace-default')
        # Leaving the Documents page puts the grid and the timeline to sleep
        # too, whichever of them was showing.
        self._on_view_changed()

    def _on_browser_pages_updated(self, _browser, count):
        # Show the Browser tab only when at least one page is available. If it
        # gets hidden while selected, fall back to the Documents view.
        page = getattr(self, '_browser_page', None)
        if page is None:
            return
        page.set_visible(count > 0)
        if count == 0 and self._stack.get_visible_child_name() == 'workspace-browser':
            self._stack.set_visible_child_name('workspace-default')

    def update_review_button(self):
        """Label the Review toggle, short enough for the window it is in.

        Gtk.Button.set_label replaces the whole child, so the icon the factory
        put there is long gone by now: the word is all there is to shorten, and
        narrow it goes down to the count. The tooltip always says it in full.
        """
        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        if togglebutton is None:
            return
        review = getattr(self, '_review_count', 0)
        full = _("Review ({review})").format(review=review)
        mainwindow = self.app.get_widget('mainwindow')
        narrow = mainwindow is not None and mainwindow.get_property('narrow')
        togglebutton.set_label(str(review) if narrow else full)
        togglebutton.set_tooltip_text(full)

    def get_workspace_view(self):
        return self.view

    def get_selected_items(self):
        return self.selected_items

    def clear_filters(self):
        """Reset every filter"""
        search_entry = self.app.get_widget('searchentry')
        dropdowns = self.app.get_widget('ws-dropdowns') or {}
        plugin_dropdowns = self.app.get_widget('plugin-dropdowns') or []

        self._clearing_filters = True
        try:
            search_entry.set_text('')
            concept_entry = self.app.get_widget('searchentry-concept')
            if concept_entry is not None:
                concept_entry.set_text('')
            for dd in dropdowns.values():
                dd.set_selected(0)
            for dd in plugin_dropdowns:
                dd.set_selected(0)
        finally:
            self._clearing_filters = False

        # The explicit list (Doctor's Show, the "Showing" tag) is a filter
        # like any other, so clearing filters drops it too.
        self._only_ids = None
        self._only_label = ''

        # The first date preset is usually empty (the last two days), the same
        # as on load: move to the nearest preset that has documents.
        self._auto_select_date_preset(list(self.view.store))

        self._refresh_filter_cache()
        self.view.refilter()
        self.emit('workspace-view-filtered')
        self._update_dropdowns_after_filter()

    def _parse_files_worker(self, repo_docs, result_dict):
        """Run in a background thread: rebuild the index and hand back its items.

        The parse itself lives in MiAZDocumentIndex, so the full scan and the
        single-file update share one implementation. Everything here is the
        thread marshalling the index does not do.
        """
        index = self.app.get_service('index')
        index.reload()
        self._publish_concepts(index)

        result_dict['items'] = index.documents()
        result_dict['invalid'] = index.invalid()
        result_dict['show_pending'] = len(index.pending()) > 0
        result_dict['_repo_docs'] = repo_docs
        return result_dict

    def _publish_concepts(self, index):
        """Expose the concept vocabulary the rename dialog completes against."""
        active, inactive = index.concepts()
        ENV['CACHE']['CONCEPTS']['ACTIVE'] = active
        ENV['CACHE']['CONCEPTS']['INACTIVE'] = inactive

    def _apply_parse_results(self, result_dict):
        """Apply parsed results on the main thread."""
        repository = self.app.get_service('repo')

        # A scan that started before a repository switch comes back after it,
        # holding the documents of the repository that was left. Applying it
        # would show the previous repository's documents in the new one and,
        # worse, spend the armed date-preset selection on them, leaving the new
        # repository filtered by a range that predates it (an empty view). The
        # switch already asked for its own scan, so this one is dropped.
        scanned = result_dict.get('_repo_docs')
        if scanned is not None and scanned != repository.docs:
            self.log.debug(f"Discarding scan of '{scanned}': the repository is now '{repository.docs}'")
            self._scan_in_flight = False
            self._schedule_update()
            return False

        items = result_dict['items']
        invalid = result_dict['invalid']
        show_pending = result_dict['show_pending']

        util = self.app.get_service('util')
        index = self.app.get_service('index')

        # Reuse the index's field index instead of letting util rebuild its own
        # by rescanning the directory.
        util._field_index = index.field_index()
        util._field_index_dir = result_dict['_repo_docs']
        ds = result_dict.get('_ds', datetime.now())

        # Update workspace view. When armed (load / repo switch / rollover),
        # switch an empty default date filter to the nearest non-empty preset
        # before the filter cache is read, so the view is built once against it.
        if self._auto_date_pending:
            self._auto_date_pending = False
            self._auto_select_date_preset(items)
        self._refresh_filter_cache()
        self._num_total_items = len(items)
        GLib.idle_add(self._idle_view_update, items, ds)

        # Rename invalid files (rare, stays on main thread)
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
        self._review_count = review
        self.update_review_button()
        if show_pending:
            togglebutton.add_css_class('destructive-action')
            togglebutton.remove_css_class('flat')
        else:
            togglebutton.remove_css_class('destructive-action')
            togglebutton.add_css_class('flat')
        if show_pending != self._was_pending:
            if show_pending:
                self.log.debug("Pending documents detected: showing Review button")
            else:
                self.log.debug("No pending documents: hiding Review button")
            self._was_pending = show_pending
        togglebutton.set_visible(show_pending)

        if not show_pending:
            togglebutton.set_active(False)
        self._review = togglebutton.get_active()

        self._scan_in_flight = False
        self.selected_items = []
        return False

    def suspend_updates(self):
        """Hold back workspace refreshes until the returned handle is released.

        Nestable and safe to overlap: the view refreshes once, after the last
        holder lets go, and only if something asked for a refresh meanwhile.

            with workspace.suspend_updates():
                for path in files:
                    util.filename_import(path, target)

        Work that finishes on another thread keeps the handle and releases it
        from the main loop instead:

            handle = workspace.suspend_updates()
            GLib.idle_add(handle.release)
        """
        return self._gate.suspend()

    def update(self, *args):
        """Update Workspace columnview"""
        if self._clearing_filters:
            return

        # Something is doing bulk work. The gate remembers that a refresh is due
        # and runs this once when the last holder releases.
        if not self._gate.request():
            return

        if self.app.get_status() == MiAZStatus.BUSY:
            # A repository switch is in progress; it triggers its own update.
            self._schedule_update()
            return

        if self._scan_in_flight:
            # A previous scan has not come back yet. Try again shortly.
            self._schedule_update()
            return

        repository = self.app.get_service('repo')
        if repository.conf is None:
            return

        self._scan_in_flight = True

        # Rebuild the relative date presets if the calendar day rolled over since
        # they were built (the app left running past midnight). Otherwise a
        # document dated today falls outside the today bounded ranges and only
        # appears under "Future". Preserves the selected preset.
        if self._date_presets_day != datetime.now().date():
            self._update_dropdown_date()

        ds = datetime.now()

        # Read and process the files in the background so the window does not
        # freeze. The result comes back on the main loop.
        run_in_background(
            lambda: self._parse_files_worker(repository.docs, {'_ds': ds}),
            on_done=self._apply_parse_results,
            on_error=self._on_scan_failed,
            name='workspace-scan')

    def _on_scan_failed(self, error):
        """Let the next scan through when this one could not finish.

        Only the success path used to clear the flag, so a worker that raised
        blocked every later update for the life of the process.
        """
        self.log.error(f"Workspace scan failed: {error}")
        self._scan_in_flight = False

    def _idle_view_update(self, items, ds):
        """Apply the store splice and emit the updated signal with correct post-filter counts."""
        self.view.update(items)
        model = self.view.cv.get_model()
        self._num_selected_items = len(self.selected_items)
        self._num_displayed_items = len(model)
        dt = datetime.now() - ds
        self.log.debug(f"Workspace updated in {dt}s ({self._num_displayed_items} documents displayed)")
        self.emit('workspace-view-updated')
        return False

    def _auto_select_date_preset(self, items):
        """Switch an empty default date filter to the nearest preset that
        contains documents (see pick_date_preset). Runs only when armed; the
        selection signal is blocked so it does not re-enter the filter pass."""
        dropdowns = self.app.get_widget('ws-dropdowns')
        dd_date = dropdowns[Date.__gtype_name__]
        model = dd_date.get_model()
        if model is None:
            return
        util = self.app.get_service('util')
        today = datetime.now().date()

        presets = []
        for i in range(model.get_n_items()):
            pid = model.get_item(i).id
            if pid == 'All-All':
                presets.append(('all', None, None))
                continue
            parts = pid.split('-')
            start = util.string_to_datetime(parts[0]) if len(parts) == 2 else None
            end = util.string_to_datetime(parts[1]) if len(parts) == 2 else None
            if start is None or end is None:
                # Unparseable id: make it a no-op that the walk skips.
                presets.append(('future', None, None))
                continue
            kind = 'future' if start > today else 'bounded'
            presets.append((kind, start, end))

        item_dates = []
        for item in items:
            adate = util.string_to_datetime(item.date) if item.date else None
            if adate is not None:
                item_dates.append(adate)

        current = dd_date.get_selected()
        target = pick_date_preset(current, item_dates, presets)
        if target != current and 0 <= target < model.get_n_items():
            if self._sid_date_selected is not None:
                dd_date.handler_block(self._sid_date_selected)
            dd_date.set_selected(target)
            if self._sid_date_selected is not None:
                dd_date.handler_unblock(self._sid_date_selected)

    def _refresh_filter_cache(self):
        """Read the filter widgets into a DocumentQuery, once per filter pass.

        The query is what actually filters. Reading the widgets here rather than
        per item is the same optimisation the previous _cached_* attributes
        were, expressed as a value the rest of the app can hold on to.
        """
        self._query = self._read_query()

    def _read_query(self):
        """Build the query the filter widgets currently describe."""
        dropdowns = self.app.get_widget('ws-dropdowns')
        entry = self.app.get_widget('searchentry')
        entry_concept = self.app.get_widget('searchentry-concept')

        query = DocumentQuery(
            search=entry.get_text(),
            concept=entry_concept.get_text() if entry_concept is not None else '',
            country=self._selected_id(dropdowns, Country.__gtype_name__),
            group=self._selected_id(dropdowns, Group.__gtype_name__),
            sentby=self._selected_id(dropdowns, SentBy.__gtype_name__),
            purpose=self._selected_id(dropdowns, Purpose.__gtype_name__),
            sentto=self._selected_id(dropdowns, SentTo.__gtype_name__),
            only_pending=self._review)
        self._read_date_range(dropdowns, query)
        if self._only_ids is not None:
            query.only_ids = self._only_ids
            query.ignore_date = True
            query.ignore_active = True

        # A plugin filtering on something the repository config knows nothing
        # about (project membership, for one) lifts the checks that would hide
        # its documents. The core filter does not know which plugins exist.
        for name, hook in list(self._query_hooks.items()):
            try:
                hook(query)
            except Exception as error:
                self.log.error(f"Query hook '{name}' failed: {error}")
        return query

    @staticmethod
    def _selected_id(dropdowns, gtype_name):
        """The selected item id, or 'Any' when the dropdown has no selection."""
        selected = dropdowns[gtype_name].get_selected_item()
        return ANY if selected is None else selected.id

    def _read_date_range(self, dropdowns, query):
        """Translate the date preset into a mode and, for a range, its bounds."""
        util = self.app.get_service('util')
        selected = dropdowns[Date.__gtype_name__].get_selected_item()
        if selected is None:
            return
        query.date_preset = selected.preset
        ll, ul = selected.id.split('-')
        if ll == 'None' and ul == 'None':
            query.date_mode = DATE_NONE
        elif ll != 'All' and ul != 'All':
            query.date_mode = DATE_RANGE
            query.date_since = util.string_to_datetime(ll)
            query.date_until = util.string_to_datetime(ul)

    def get_query(self):
        """The DocumentQuery the view is currently filtered by."""
        return self._query

    def set_query(self, query):
        """Filter the view by a query built elsewhere (a plugin, a saved search).

        The filter widgets are set to match, then the query is read back from
        them, so the sidebar and the view always agree and the next widget
        change builds on this query instead of discarding it.

        Reading back is also what resolves a date preset: a saved search stores
        'this month' rather than the dates it meant when it was saved, and the
        sidebar entry supplies the range for today.

        Returns the query fields it could not represent in the sidebar, empty
        when everything was applied.
        """
        unrepresented = self._write_widgets(query)
        self._query = self._read_query()
        self.view.refilter()
        self.emit('workspace-view-filtered')
        # Narrow the dropdowns back to the visible values on idle, the way a
        # normal filter change does. Doing it inline runs it against a filter
        # model that has not caught up yet, so the value just selected looks
        # absent and the dropdown resets itself to "Any".
        if not self._dropdown_update_pending:
            self._dropdown_update_pending = True
            GLib.idle_add(self._idle_update_dropdowns)
        if unrepresented:
            self.log.warning(
                f"Query applied without {', '.join(unrepresented)}: "
                f"the sidebar has no control for it")
        return unrepresented

    def _write_widgets(self, query):
        """Set every filter control to what the query says.

        Returns the names of the fields with no control to hold them. Signals
        are muted throughout, so the whole query lands in one refilter instead
        of one per control.
        """
        dropdowns = self.app.get_widget('ws-dropdowns') or {}
        search_entry = self.app.get_widget('searchentry')
        concept_entry = self.app.get_widget('searchentry-concept')
        togglebutton = self.app.get_widget('workspace-togglebutton-pending-docs')
        unrepresented = []

        self._clearing_filters = True
        try:
            if search_entry is not None:
                search_entry.set_text(query.search)
            if concept_entry is not None:
                concept_entry.set_text(query.concept)
            # Refill the field dropdowns from the repository vocabulary first.
            # Between filter passes they hold only the values the visible
            # documents use, so a query naming anything outside the current
            # view had nothing to select. The trailing
            # _update_dropdowns_after_filter narrows them again, keeping the
            # selection made here.
            self._repopulate_field_dropdowns(dropdowns)
            for item_type, value in (
                    (Country, query.country),
                    (Group, query.group),
                    (SentBy, query.sentby),
                    (Purpose, query.purpose),
                    (SentTo, query.sentto)):
                dropdown = dropdowns.get(item_type.__gtype_name__)
                if not self._select_by_id(dropdown, value):
                    unrepresented.append(f'{item_type.__gtype_name__}={value}')
            if not self._select_date_preset(dropdowns.get(Date.__gtype_name__),
                                            query):
                unrepresented.append('date')
            if togglebutton is not None:
                togglebutton.set_active(query.only_pending)
                self._review = query.only_pending
        finally:
            self._clearing_filters = False
        return unrepresented

    def _repopulate_field_dropdowns(self, dropdowns):
        """Put every enabled value back in the five field dropdowns."""
        actions = self.app.get_service('actions')
        for item_type in (Country, Group, SentBy, Purpose, SentTo):
            dropdown = dropdowns.get(item_type.__gtype_name__)
            if dropdown is None:
                continue
            actions.dropdown_populate(
                config=self.app.get_config(item_type.__gtype_name__),
                dropdown=dropdown, item_type=item_type,
                any_value=True, none_value=False)

    @staticmethod
    def _select_by_id(dropdown, value):
        """Select the entry whose id is `value`. False when there is none."""
        if dropdown is None:
            return False
        model = dropdown.get_model()
        for pos in range(model.get_n_items()):
            if model.get_item(pos).id == value:
                dropdown.set_selected(pos)
                return True
        return False

    def _select_date_preset(self, dropdown, query):
        """Select the date entry the query names, by token.

        A query carrying raw bounds and no token came from somewhere other than
        this sidebar, so there may be no entry that means it; the range is left
        as the query gave it and the caller is told.
        """
        if dropdown is None:
            return False
        if not query.date_preset:
            # No preset: representable only if it asks for everything.
            return query.date_mode == DATE_ALL
        model = dropdown.get_model()
        for pos in range(model.get_n_items()):
            if model.get_item(pos).preset == query.date_preset:
                dropdown.set_selected(pos)
                return True
        return False

    def show_documents(self, ids, label=''):
        """Show these documents and nothing else, whatever the filters say.

        The date range and the pending check are lifted: a list worth putting
        in front of somebody usually holds the documents that are wrong, and
        those are exactly the ones the ordinary view hides. The restriction
        appears as a tag in the filter bar, so it is visible and removable
        like any other filter.
        """
        self._only_ids = frozenset(ids)
        self._only_label = label
        self.show_view('details')
        self.update()

    def clear_documents(self):
        """Drop the explicit list and go back to what the filters say."""
        if self._only_ids is None:
            return
        self._only_ids = None
        self._only_label = ''
        self.update()

    def get_shown_documents(self):
        return self._only_ids

    def register_query_hook(self, name: str, callback):
        """Let a component adjust the query after it is read from the widgets.

        The callback takes the DocumentQuery and may set any of its fields; the
        usual use is switching off ignore_date / ignore_active.
        """
        self._query_hooks[name] = callback

    def unregister_query_hook(self, name: str):
        self._query_hooks.pop(name, None)

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
        return self._query.matches(item)

    def _do_connect_filter_signals(self):
        searchentry = self.app.get_widget('searchentry')
        searchentry.connect('changed', self._on_filter_selected)
        concept_entry = self.app.get_widget('searchentry-concept')
        if concept_entry is not None:
            concept_entry.connect('changed', self._on_filter_selected)
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

                model_filter = dropdown.get_model()
                model_sort = model_filter.get_model()
                model = model_sort.get_model()

                new_items = [
                    item_type(id='Any', title=_('Any') + ' ' + i_title.lower()),
                ]
                for key in sorted(values.keys()):
                    title = values[key]
                    new_items.append(item_type(id=key, title=title if title else key))
                model.splice(0, model.get_n_items(), new_items)

                # Selection preservation
                pos_map = {}
                n_dd = model_filter.get_n_items()
                for pos in range(n_dd):
                    dd_item = model_filter.get_item(pos)
                    if dd_item:
                        pos_map[dd_item.id] = pos
                if selected_id in pos_map:
                    dropdown.set_selected(pos_map[selected_id])
                else:
                    dropdown.set_selected(0)
        finally:
            self._updating_dropdowns = False
        self._update_filter_tags()

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

        # Do nothing while the repository is being switched or a scan is out:
        # both replace the store, and this pass would be thrown away.
        if self.app.get_status() == MiAZStatus.BUSY or self._scan_in_flight:
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
        self.selected_items = []
        model = selection.get_model()
        bitset = selection.get_selection()
        for index in range(bitset.get_size()):
            pos = bitset.get_nth(index)
            item = model.get_item(pos)
            self.selected_items.append(item)
        self._num_selected_items = len(self.selected_items)
        self.emit('workspace-view-selection-changed')

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
        index = self.app.get_service('index')
        util.json_save(self.fcache, index.cache)
        self.log.debug(f"Workspace cache saved to {self.fcache}")

    def get_workspace_filters(self):
        return self._workspace_filters
