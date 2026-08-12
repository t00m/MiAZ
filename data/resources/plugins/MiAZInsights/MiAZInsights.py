# pylint: disable=E1101

"""
# File: MiAZInsights.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Insights into the active repository, published to the WWW
#              root as one self-contained page so it shows up in the integrated
#              MiAZ Browser dropdown.
#
# The page carries every aggregated number as an embedded JSON payload and
# renders views from it in the browser: an "All years" overview (lifetime
# totals, per-year trend, month-by-year activity heatmap, rank movers, firsts
# and lasts) and one view per year (rhythm of the year, senders, concepts,
# purposes, what is new). Switching years is a client-side swap, so there is a
# single output file.
#
# Output:
#   $HOME/.MiAZ/var/www/html/MiAZInsights/index.html
#
# Triggers (debounced rebuild):
#   workspace-loaded             initial build + menu install
#   util.filename-added          rebuild
#   util.filename-deleted        rebuild
#   util.filename-renamed        rebuild
"""

import os
import sys
import shutil
from datetime import datetime
from gettext import gettext as _

from gi.repository import GLib

from MiAZ.backend.tasks import run_in_background
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

# The support package sits next to this file, which is not on the default path.
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

from insights import render  # noqa: E402


plugin_info = {
    'Module':       'MiAZInsights',
    'Name':         'MiAZInsights',
    'Loader':       'Python3',
    'Description':  _('Insights into your documents'),
    'Authors':      'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':    'Copyright © 2026 Tomás Vírseda',
    'Website':      'https://github.com/t00m/MiAZ',
    'Help':         'https://github.com/t00m/MiAZ/README.adoc',
    'Version':      '0.2.0',
    'Category':     'Analytics and Reporting',
    'Subcategory':  'Custom Reports',
}

PLUGIN_DIR_NAME = 'MiAZInsights'
REBUILD_DEBOUNCE_MS = 1500

# Repository configuration holding the display name of each field value.
NAME_CONFIGS = (
    ('sender', 'SentBy'),
    ('purpose', 'Purpose'),
    ('group', 'Group'),
    ('country', 'Country'),
    ('sentto', 'SentTo'),
)


class MiAZInsightsPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZInsightsPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()

        self.util = self.app.get_service('util')
        self.repo = self.app.get_service('repo')
        self.factory = self.app.get_service('factory')

        self._rebuild_timeout_id = 0
        self._signal_handlers = []
        self.workspace = self.app.get_widget('workspace')

        self._connect_signals()

        if self.workspace is not None and self.workspace.is_loaded():
            self._on_workspace_loaded()
        elif self.workspace is not None:
            handler = self.workspace.connect('workspace-loaded', lambda *_a: self._on_workspace_loaded())
            self._signal_handlers.append((self.workspace, handler))

    def do_deactivate(self):
        if self._rebuild_timeout_id:
            GLib.source_remove(self._rebuild_timeout_id)
            self._rebuild_timeout_id = 0
        for obj, handler in self._signal_handlers:
            try:
                obj.disconnect(handler)
            except Exception:
                pass
        self._signal_handlers = []
        # The published site under LPATH/WWW is removed centrally by the plugin
        # manager (unload_plugin -> _remove_plugin_www) when the plugin is
        # disabled or uninstalled, so no per-plugin cleanup is needed here.
        self.plugin.set_started(False)

    # Setup

    def _connect_signals(self):
        for sig in ('filename-added', 'filename-deleted', 'filename-renamed'):
            handler = self.util.connect(sig, self._on_repo_changed)
            self._signal_handlers.append((self.util, handler))

    def _on_workspace_loaded(self):
        if not self.plugin.started():
            menuitem = self.factory.create_menuitem(
                name=self.plugin.get_menu_item_name(),
                label=_('Open insights'),
                callback=self._on_menu_clicked,
            )
            self.plugin.install_menu_entry(menuitem)
            self.plugin.set_started(True)
        self._schedule_rebuild()

    def _on_menu_clicked(self, *_args):
        # The page lives in the Browser tab; bring that tab forward.
        if self.workspace is not None:
            try:
                self.workspace.show_stack_page('workspace-browser')
            except Exception as error:
                self.log.debug(f"MiAZInsights: could not show Browser page: {error}")

    def _on_repo_changed(self, *_args):
        self._schedule_rebuild()

    # Paths

    def _plugin_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    def _target_dir(self):
        env = self.app.get_env()
        if env is None:
            return None
        return os.path.join(env['LPATH']['WWW'], PLUGIN_DIR_NAME)

    def _asset(self, name):
        path = os.path.join(self._plugin_dir(), 'static', name)
        with open(path, 'r', encoding='utf-8') as fh:
            return fh.read()

    # Build (debounced, off the GTK main loop)

    def _schedule_rebuild(self):
        if self._rebuild_timeout_id:
            GLib.source_remove(self._rebuild_timeout_id)
        self._rebuild_timeout_id = GLib.timeout_add(REBUILD_DEBOUNCE_MS, self._kick_rebuild)

    def _kick_rebuild(self):
        self._rebuild_timeout_id = 0
        run_in_background(self._rebuild_worker, name='MiAZInsights-build')
        return False

    def _rebuild_worker(self):
        """Runs off the main loop. run_in_background logs a failure with its
        traceback, which the local try/except here used to swallow."""
        payload = render.build_payload(self._records(), self._names(), self._meta(),
                                       self._periods())
        page = render.render_page(payload, self._asset('report.css'),
                                  self._asset('report.js'), self._asset('worldmap.svg'))
        self._write_page(page)

    def _write_page(self, page):
        target = self._target_dir()
        if not target:
            return
        # Wiping the directory also clears the per-year files earlier versions
        # of this plugin published.
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, 'index.html'), 'w', encoding='utf-8') as fh:
            fh.write(page)
        self.log.debug(f"MiAZInsights: wrote the page to {target}")

    # Data

    def _records(self):
        """Seven-field tuples for every normalized document in the repository."""
        docs_dir = self.repo.docs
        if not docs_dir or not os.path.isdir(docs_dir):
            return []
        records = []
        for filepath in self.util.get_files(docs_dir):
            filename = os.path.basename(filepath)
            if filename.startswith('.'):
                continue
            stem = filename.rsplit('.', 1)[0]
            if not self.util.filename_is_normalized(stem):
                continue
            records.append(self.util.get_fields(filename))
        return records

    def _periods(self):
        """The workspace date-filter windows, as (key, label, start, end).

        Same titles and same lower limits as the workspace dropdown, so a period
        here means what it means there. "Future" and "All documents" are left
        out: the report has no future documents to show and "All years" already
        covers the whole repository.
        """
        util = self.util
        now = datetime.now()
        end = util.datetime_to_string(now)
        windows = (
            ('this-month', _('This month'), util.since_date_this_month(now)),
            ('past-month', _('Since past month'), util.since_date_last_n_months(now, 1)),
            ('last-3-months', _('Since last 3 months'), util.since_date_last_n_months(now, 3)),
            ('last-6-months', _('Since last 6 months'), util.since_date_last_n_months(now, 6)),
            # The last twelve months, matching the workspace date filter. Both
            # used since_date_this_year, so the label said "last year" while the
            # window was the calendar year to date.
            ('last-12-months', _('Since last year'), util.since_date_last_n_months(now, 12)),
            ('two-years', _('Since two years ago'), util.since_date_past_n_years_ago(now, 2)),
            ('three-years', _('Since three years ago'), util.since_date_past_n_years_ago(now, 3)),
            ('five-years', _('Since five years ago'), util.since_date_past_n_years_ago(now, 5)),
            ('ten-years', _('Since ten years ago'), util.since_date_past_n_years_ago(now, 10)),
        )
        return [{'key': key, 'label': label, 'start': util.datetime_to_string(start), 'end': end}
                for key, label, start in windows]

    def _names(self):
        """Display names per field, so the report shows people, not keys."""
        names = {}
        for field, config_name in NAME_CONFIGS:
            config = self.app.get_config(config_name)
            if config is None:
                names[field] = {}
                continue
            try:
                names[field] = config.load_used()
            except Exception:
                names[field] = {}
        return names

    def _meta(self):
        env = self.app.get_env()
        app_info = env['APP'] if env else {}
        appconf = self.app.get_config('App')
        repo_id = appconf.get('current') if appconf is not None else None
        language = os.environ.get('LANG', '') or os.environ.get('LANGUAGE', '')
        locale_name = language.split('.')[0] if language else ''
        return {
            'app': app_info.get('name', 'MiAZ'),
            'version': app_info.get('VERSION', ''),
            'repo': repo_id.replace('_', ' ') if repo_id else app_info.get('name', 'MiAZ'),
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'locale': locale_name,
            'lang': locale_name.split('_')[0] or 'en',
        }
