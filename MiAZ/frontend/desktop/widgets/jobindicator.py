# File: jobindicator.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: What is running in the background, in the header bar

from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog

# How long work has to run before it is worth showing. Most background jobs in
# MiAZ are housekeeping that finishes in well under this: a workspace scan, an
# index reload, a history settle. They are recorded and counted, and a spinner
# that appeared for each of them would flicker through ordinary browsing.
SHOW_AFTER_MS = 500


class MiAZJobIndicator(Gtk.MenuButton):
    """A spinner, a count, and a list of what is running and what is waiting."""
    __gtype_name__ = 'MiAZJobIndicator'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.JobIndicator')
        self._show_id = 0

        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.count_label = Gtk.Label()
        self.count_label.add_css_class('caption')
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.append(self.spinner)
        box.append(self.count_label)
        self.set_child(box)
        self.set_tooltip_text(_('Work running in the background'))
        self.set_visible(False)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.list_box.set_margin_top(12)
        self.list_box.set_margin_bottom(12)
        self.list_box.set_margin_start(12)
        self.list_box.set_margin_end(12)
        popover = Gtk.Popover()
        popover.set_child(self.list_box)
        self.set_popover(popover)

        queue = self.app.get_service('jobs')
        if queue is not None:
            queue.connect('job-added', self._on_changed)
            queue.connect('job-changed', self._on_changed)
            queue.connect('job-removed', self._on_changed)

    def _on_changed(self, _queue, _job):
        self._refresh()

    def _refresh(self):
        queue = self.app.get_service('jobs')
        if queue is None:
            return
        running = queue.running()
        pending = queue.pending()
        busy = bool(running or pending)

        if not busy:
            self._cancel_timer()
            self.set_visible(False)
            return

        self.count_label.set_text(str(len(running) + len(pending))
                                  if len(running) + len(pending) > 1 else '')
        self._rebuild(running, pending)
        if not self.get_visible() and self._show_id == 0:
            self._show_id = GLib.timeout_add(SHOW_AFTER_MS, self._show_if_busy)

    def _show_if_busy(self):
        """Show only if the work is still going. Anything that finished inside
        the window was never worth a spinner."""
        self._show_id = 0
        queue = self.app.get_service('jobs')
        if queue is not None and (queue.running() or queue.pending()):
            self.set_visible(True)
        return GLib.SOURCE_REMOVE

    def _cancel_timer(self):
        if self._show_id != 0:
            GLib.source_remove(self._show_id)
            self._show_id = 0

    def _rebuild(self, running, pending):
        child = self.list_box.get_first_child()
        while child is not None:
            self.list_box.remove(child)
            child = self.list_box.get_first_child()

        self._add_heading(_('Background work'))
        for job in running:
            self._add_running(job)
        if pending:
            self._add_heading(_('Pending'))
            for job in pending:
                self._add_line(job.label)

    def _add_heading(self, text):
        label = Gtk.Label(xalign=0)
        label.set_markup(f'<b>{GLib.markup_escape_text(text)}</b>')
        self.list_box.append(label)

    def _add_line(self, text):
        label = Gtk.Label(xalign=0, label=text)
        label.set_ellipsize(3)  # Pango.EllipsizeMode.END, without the import
        self.list_box.append(label)

    def _add_running(self, job):
        self._add_line(job.label)
        if job.message:
            self._add_line(f'   {job.message}')
        if job.fraction is not None:
            bar = Gtk.ProgressBar()
            bar.set_fraction(job.fraction)
            self.list_box.append(bar)

    def describe(self) -> str:
        """Everything the popover is showing, as one string. For tests."""
        parts = []
        child = self.list_box.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Label):
                parts.append(child.get_text())
            child = child.get_next_sibling()
        return '\n'.join(parts)
