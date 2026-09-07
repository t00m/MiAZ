# pylint: disable=E1101

"""
# File: miazhistory.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Undo and redo changes in this repository
"""

import os
import sys
from gettext import gettext as _

from gi.repository import GLib

from MiAZ.backend.tasks import run_in_background
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':        'miazhistory',
    'Name':          'MiAZHistory',
    'Loader':        'Python3',
    'Description':   _('Undo and redo changes in this repository'),
    'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2026 Tomás Vírseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
    'Version':       '0.3.0',
    'Category':      'Repository',
    'Subcategory':   'History',
}

# How long a burst is allowed to settle before it is recorded. Longer than the
# watcher's own 500 ms debounce, so a burst that reaches us in pieces is still
# one step.
SETTLE_MS = 1200

# And how long the settling may be put off. Without a ceiling a long import
# keeps restarting the timer and nothing is ever recorded.
CEILING_MS = 30000


class MiAZHistoryPlugin(MiAZExtension):
    """Two buttons, and whatever it takes to stand behind them.

    Every change to the repository is kept, so any of them can be taken back.
    How that is stored is not the user's problem, and none of it reaches the
    interface.
    """
    __gtype_name__ = 'MiAZHistoryPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.srvdlg = self.app.get_service('dialogs')
        self.repository = self.app.get_service('repo')
        self.store = None
        self._ready = False
        self._counts = {}
        self._settle_id = 0
        self._ceiling_id = 0
        self._recording = False
        self._suppressed = False
        self._handlers = []

        # The history package sits under the plugin directory, which is not on
        # the default path.
        source_dir = self.plugin.get_source_dir()
        if source_dir not in sys.path:
            sys.path.insert(0, source_dir)

        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded',
                                                           self.startup)

    def do_deactivate(self):
        self._stop_recording()
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if self.plugin.started():
            return
        self.plugin.set_started(started=True)
        self.prepare()

    def is_ready(self) -> bool:
        """Whether there is a history to step through."""
        return self._ready

    def prepare(self):
        """Decide what this repository can offer, and set it up if it can."""
        from history.distro import install_command
        from history.gitstore import GitStore, git_available

        if not git_available():
            self._offer_to_install(install_command())
            return

        self.store = GitStore(self.repository.docs)
        if self.store.is_foreign():
            self._refuse_foreign()
            return
        if self.store.is_ours():
            self._start_recording()
            return
        self._offer_first_snapshot()

    def disable_self(self):
        """Switch the plugin off, so nothing half-working is left on screen."""
        config = self.app.get_config('Plugin')
        if config is not None:
            config.remove_used(plugin_info['Name'])

    def _offer_to_install(self, command):
        """Say what is missing, and exactly how to get it."""
        window = self.app.get_widget('window')
        if command:
            body = _('MiAZ needs one more program to keep a history of this '
                     'repository. Install it with:\n\n<tt>%s</tt>') % command
        else:
            body = _('MiAZ needs one more program to keep a history of this '
                     'repository. Install this package with your '
                     'distribution package manager:\n\n<tt>git</tt>')
        dialog = self.srvdlg.show_error(
            title=_('One program is missing'), body=body)
        dialog.present(window)
        self.disable_self()

    def _refuse_foreign(self):
        """Somebody already tracks these documents themselves. Leave them be."""
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_error(
            title=_('This repository is already being tracked'),
            body=_('Something else is already keeping a history of this '
                   'repository, so MiAZ will not keep another one.'))
        dialog.present(window)
        self.disable_self()

    def _offer_first_snapshot(self):
        """Ask before spending the disk, and say how much it is."""
        window = self.app.get_widget('window')
        size = self._repository_size()
        dialog = self.srvdlg.show_question(
            title=_('Keep a history of this repository?'),
            body=_('MiAZ will keep a copy of this repository so your changes '
                   'can be undone. This needs about %s of extra disk space, '
                   'and a few minutes the first time.') % readable(size),
            callback=self._on_first_snapshot_answer)
        dialog.present(window)

    def _on_first_snapshot_answer(self, dialog, response, *args):
        if response != 'apply':
            self.disable_self()
            return
        self.srvdlg.show_toast(_('Preparing the history...'))
        run_in_background(
            lambda: self.store.init(_('Everything as it was')),
            on_done=self._on_first_snapshot_done,
            on_error=self._on_first_snapshot_failed,
            name='miazhistory-first-snapshot')

    def _on_first_snapshot_done(self, _result):
        self._start_recording()
        self.srvdlg.show_toast(_('Your changes can now be undone'))

    def _on_first_snapshot_failed(self, error):
        self.log.error(f"The first snapshot failed: {error}")
        self.srvdlg.show_toast(_('The history could not be prepared'))
        self.disable_self()

    def catch_up(self):
        """Record what changed while the plugin was off, as one step."""
        if not self._ready or not self.store.is_dirty():
            return
        run_in_background(
            lambda: self.store.record(_('Changed outside MiAZ')),
            on_error=lambda error: self.log.error(
                f"Changes made outside MiAZ could not be recorded: {error}"),
            name='miazhistory-catch-up')

    def _start_recording(self):
        """Listen for everything that can change the repository.

        Three sources, one timer. The first two name what the user did, which
        is what a step is called. The third is the file monitor, which sees
        what MiAZ did not do itself: a document dropped into the directory by
        the file manager. It watches the repository root only, so a change
        under .conf reaches us through the configuration signals alone.
        """
        self._ready = True
        util = self.app.get_service('util')
        for signal, key in (('filename-added', 'added'),
                            ('filename-renamed', 'renamed'),
                            ('filename-deleted', 'deleted')):
            handler = util.connect(signal, self._on_documents_changed, key)
            self._handlers.append((util, handler))

        for name in self.app.get_config_dict():
            config = self.app.get_config(name)
            if config is None:
                continue
            for signal in ('available-updated', 'used-updated'):
                handler = config.connect(signal, self._on_config_changed)
                self._handlers.append((config, handler))

        watcher = self.app.get_service('watcher')
        if watcher is not None:
            handler = watcher.connect('repository-updated', self._on_anything_changed)
            self._handlers.append((watcher, handler))

        self.catch_up()

    def _stop_recording(self):
        for source, handler in self._handlers:
            try:
                source.disconnect(handler)
            except TypeError:
                pass
        self._handlers = []
        for source_id in (self._settle_id, self._ceiling_id):
            if source_id:
                GLib.source_remove(source_id)
        self._settle_id = 0
        self._ceiling_id = 0

    def _on_documents_changed(self, _util, *args):
        # filename-deleted carries every path removed in one call, so the
        # count has to come from the collection rather than from the number
        # of signals: one signal, possibly several documents.
        key = args[-1]
        first = args[0]
        amount = len(first) if isinstance(first, (set, list, tuple)) else 1
        self._counts[key] = self._counts.get(key, 0) + amount
        self._restart_settle()

    def _on_config_changed(self, *_args):
        self._counts['config'] = 1
        self._restart_settle()

    def _on_anything_changed(self, *_args):
        self._restart_settle()

    def _restart_settle(self):
        """Wait for the burst to end, but not forever."""
        if self._suppressed or not self._ready:
            return
        if self._settle_id:
            GLib.source_remove(self._settle_id)
        self._settle_id = GLib.timeout_add(SETTLE_MS, self._on_settled)
        if not self._ceiling_id:
            self._ceiling_id = GLib.timeout_add(CEILING_MS, self._on_settled)

    def _on_settled(self):
        self.settle()
        return GLib.SOURCE_REMOVE

    def settle(self):
        """Record what this window collected as one step."""
        if self._settle_id:
            GLib.source_remove(self._settle_id)
            self._settle_id = 0
        if self._ceiling_id:
            GLib.source_remove(self._ceiling_id)
            self._ceiling_id = 0
        if not self._ready or self._recording or self._suppressed:
            return

        from history.summary import subject
        counts = self._counts
        self._counts = {}
        self._recording = True
        run_in_background(
            lambda: self.store.record(subject(counts)),
            on_done=self._on_recorded,
            on_error=self._on_record_failed,
            name='miazhistory-record')

    def _on_recorded(self, _state):
        self._recording = False
        self.refresh_buttons()

    def _on_record_failed(self, error):
        """A change that could not be recorded is not a change that was lost:
        everything is staged again next time, so it lands in a later step."""
        self._recording = False
        self.log.error(f"A change could not be recorded: {error}")
        self.srvdlg.show_toast(_('The change could not be recorded'))

    def refresh_buttons(self):
        """Overridden with real work once the buttons exist."""

    def _repository_size(self) -> int:
        total = 0
        for root, dirs, files in os.walk(self.repository.docs):
            dirs[:] = [name for name in dirs if name != '.git']
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    pass
        return total


def readable(size: int) -> str:
    """A size a person can read, in the units a person uses."""
    units = (('GB', 1000 ** 3), ('MB', 1000 ** 2), ('kB', 1000))
    for unit, step in units:
        if size >= step:
            return f'{size / step:.1f} {unit}'
    return _('%d bytes') % size
