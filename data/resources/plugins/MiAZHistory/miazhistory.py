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

from gi.repository import Adw, GLib, Gtk

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

BOX_WIDGET_ID = 'headerbar-box-history'
UNDO_WIDGET_ID = 'headerbar-button-history-undo'
REDO_WIDGET_ID = 'headerbar-button-history-redo'


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

        self.plugin.install_settings_group(self.build_settings)

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
        self._install_buttons()
        self.prepare()

    def _install_buttons(self):
        """One pair of buttons, in the header bar, for the whole window.

        They are built insensitive: until prepare() has found or made a
        history, there is nothing to step through.
        """
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.add_css_class('linked')
        self.button_undo = Gtk.Button()
        self.button_undo.set_icon_name('edit-undo-symbolic')
        self.button_undo.set_has_frame(False)
        self.button_undo.set_valign(Gtk.Align.CENTER)
        self.button_undo.set_sensitive(False)
        self.button_undo.connect('clicked', lambda button: self.ask_undo())
        self.button_redo = Gtk.Button()
        self.button_redo.set_icon_name('edit-redo-symbolic')
        self.button_redo.set_has_frame(False)
        self.button_redo.set_valign(Gtk.Align.CENTER)
        self.button_redo.set_sensitive(False)
        self.button_redo.connect('clicked', lambda button: self.ask_redo())
        box.append(self.button_undo)
        box.append(self.button_redo)
        self.app.add_widget(UNDO_WIDGET_ID, self.button_undo)
        self.app.add_widget(REDO_WIDGET_ID, self.button_redo)
        self.plugin.add_headerbar_widget(box, position='left',
                                         widget_key=BOX_WIDGET_ID)

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
        self.refresh_buttons()
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
        self.refresh_buttons()

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
        if not self._ready or self._suppressed:
            return
        if self._recording:
            # A recording from an earlier window is still in flight. What was
            # collected since has to wait its turn rather than sit unarmed, so
            # this window settles again as soon as that recording finishes.
            self._restart_settle()
            return

        from history.summary import subject
        counts = self._counts
        self._counts = {}
        self._recording = True
        run_in_background(
            lambda: self.store.record(subject(counts)),
            on_done=self._on_recorded,
            on_error=lambda error: self._on_record_failed(error, counts),
            name='miazhistory-record')

    def _on_recorded(self, _state):
        self._recording = False
        self.refresh_buttons()

    def _on_record_failed(self, error, counts):
        """The file content is never lost: record() stages everything again
        on the next attempt. What settle() already cleared is the count of
        what this window was, so it is merged back into whatever has piled up
        since, and the next successful step is named after all of it rather
        than only the part that came after the failure. Nothing is re-armed
        here: a failure that keeps failing must not spin a timer forever, and
        the next real signal starts a window the usual way.
        """
        self._recording = False
        for key, amount in counts.items():
            self._counts[key] = self._counts.get(key, 0) + amount
        self.log.error(f"A change could not be recorded: {error}")
        self.srvdlg.show_toast(_('The change could not be recorded'))

    def refresh_buttons(self):
        """Say what each button would do, or grey it out when it would do
        nothing."""
        from history.summary import headline, when
        if not self._ready:
            return
        for button, pending, wording in (
                (self.button_undo, self.store.pending_undo(),
                 _('Undo: %(what)s (%(when)s)')),
                (self.button_redo, self.store.pending_redo(),
                 _('Redo: %(what)s (%(when)s)'))):
            button.set_sensitive(pending is not None)
            if pending is None:
                button.set_tooltip_text('')
                continue
            older, newer = pending
            changes = self.store.changes(older, newer)
            button.set_tooltip_text(wording % {
                'what': headline(changes),
                'when': when(self.store.timestamp(newer))})

    def ask_undo(self):
        return self._ask('back')

    def ask_redo(self):
        return self._ask('forward')

    def _ask(self, direction: str):
        """Show what the step would change, and let the user decide.

        Returns the dialog, so a test can read what the user would read.
        """
        from history.summary import body
        pending = (self.store.pending_undo() if direction == 'back'
                   else self.store.pending_redo())
        if pending is None:
            return None
        older, newer = pending
        changes = self.store.changes(older, newer)
        back = direction == 'back'
        # show_confirmation rather than show_question: it puts the action on
        # the button ("Undo") instead of answering "Yes", and it makes Cancel
        # the default, which is right for something that rewrites files.
        dialog = self.srvdlg.show_confirmation(
            title=_('Undo this change?') if back else _('Redo this change?'),
            body=body(changes, self.store.timestamp(newer)),
            confirm_label=_('Undo') if back else _('Redo'),
            callback=self._on_answer, data=direction,
            width=520, height=420)
        dialog.present(self.app.get_widget('window'))
        return dialog

    def _on_answer(self, dialog, response, direction):
        if response == 'apply':
            self.apply_step(direction)

    def apply_step(self, direction: str):
        """Put an earlier or later state of the repository back on disk.

        Recording is suppressed while this runs: the files change, and the
        file monitor would otherwise report the step as a change the user
        made. The same flag also guards against a second step starting
        before this one finishes: two of them against the same working tree
        at once would race.
        """
        if not self._ready or self._suppressed:
            return
        pending = (self.store.pending_undo() if direction == 'back'
                   else self.store.pending_redo())
        if pending is None:
            return
        # Asked before the step, because afterwards the two states it compares
        # are no longer the ones either side of where we are.
        touched_config = any(path.startswith('.conf/') or other.startswith('.conf/')
                             for _status, path, other
                             in self.store.changes(pending[0], pending[1]))
        self._suppressed = True
        self.button_undo.set_sensitive(False)
        self.button_redo.set_sensitive(False)
        subject = (_('Stepped back') if direction == 'back'
                   else _('Stepped forward'))
        step = (self.store.step_back if direction == 'back'
                else self.store.step_forward)
        run_in_background(lambda: step(subject),
                          on_done=lambda state: self._on_step_done(state, touched_config),
                          on_error=self._on_step_failed,
                          name=f'miazhistory-step-{direction}')

    def _on_step_done(self, _state, touched_config: bool):
        self._suppressed = False
        self._counts = {}
        self.refresh_buttons()
        if touched_config:
            self.reload()

    def _on_step_failed(self, error):
        self._suppressed = False
        self.log.error(f"The step could not be applied: {error}")
        self.srvdlg.show_toast(_('The change could not be undone'))
        self.refresh_buttons()

    def reload(self):
        """Tell MiAZ to read the configuration that is now on disk.

        Documents alone need nothing: the file monitor repaints the workspace
        by itself. Configuration does, because every config object holds its
        file in memory, so the repository is opened again, the same way a
        repository switch does it. That is the expensive path, which is why it
        runs only when a step touched .conf.
        """
        workflow = self.app.get_service('workflow')
        if workflow is None:
            return
        workflow.switch_start(repo_id=self.repository.get_active_id())

    def build_settings(self):
        """What the history holds, and what it costs. Nothing to change here:
        nothing is pruned, so the size is the one thing worth saying."""
        from gettext import ngettext
        group = Adw.PreferencesGroup(
            title=_('History'),
            description=_('What can be undone in this repository'))
        if not self._ready:
            group.add(Adw.ActionRow(
                title=_('No history yet'),
                subtitle=_('Nothing has been recorded for this repository.')))
            return group
        count = self.store.count()
        group.add(Adw.ActionRow(
            title=_('Changes kept'),
            subtitle=ngettext('%d change can be undone',
                              '%d changes can be undone', count) % count))
        group.add(Adw.ActionRow(
            title=_('Disk used'),
            subtitle=readable(self.store.size())))
        return group

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
