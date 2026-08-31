"""
# File: progress.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Modal progress dialog for long operations (backup and restore)

Backup and restore move files around underneath the running application. They
used to run on the main loop and report with a toast: the window froze for as
long as the copy took, with nothing on screen to say why, and a second click
started a second copy of the same operation over the first.

This service is the one place that fixes both. The work goes to a worker
thread, the application UI is made insensitive, and a modal dialog reports what
is happening. The dialog cannot be dismissed until the work is over, and when
it is, it says what happened and waits: the UI comes back when the user closes
it, not the moment the last file is written.

Only the window content is made insensitive, never the window itself. Dialogs
live in libadwaita's dialog host, beside that content rather than inside it, so
disabling the window would disable this dialog too, Close button included.
"""

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.tasks import run_in_background


class MiAZProgress:
    """Run one long operation at a time behind a modal progress dialog."""

    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZ.Progress')
        self._busy = False

    def is_busy(self) -> bool:
        """True while an operation is running or its result is still on screen."""
        return self._busy

    def run(self, work, title: str, message: str = '', parent=None, on_close=None):
        """Run work(report) in a worker thread behind a modal progress dialog.

        work is called with a report(text, fraction=None) callback it may call
        from the worker thread; a fraction of None pulses the bar instead of
        filling it. Whatever work returns is shown to the user as the outcome:
        a string is shown as it is, None falls back to a plain "Done".

        on_close(ok, result) runs after the user dismisses the dialog, with the
        UI already usable again. On failure, result is the exception.

        Returns the dialog it presented, or None when another operation is
        already running, so a second click cannot start a second copy of the
        same work.
        """
        if self._busy:
            self.log.warning(f"'{title}' not started: another operation is running")
            return None
        self._busy = True

        window = self.app.get_widget('window')
        content = self.app.get_widget('window-mainbox')
        if content is not None:
            content.set_sensitive(False)

        dialog = Adw.AlertDialog(heading=title,
                                 body=message or _('Working…'))
        # Fixed geometry: the detail line changes on every update, and letting
        # it size the dialog makes the window jump around while it works.
        dialog.set_content_width(460)
        dialog.set_content_height(180)
        dialog.set_can_close(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        progress = Gtk.ProgressBar()
        progress.set_hexpand(True)
        progress.set_show_text(True)
        progress.set_text(_('Working…'))
        box.append(progress)

        detail = Gtk.Label()
        detail.add_css_class('caption')
        detail.add_css_class('dim-label')
        # One ellipsized line, never wrapped, so a long filename cannot resize
        # the dialog mid-operation.
        detail.set_wrap(False)
        detail.set_single_line_mode(True)
        detail.set_ellipsize(Pango.EllipsizeMode.END)
        detail.set_xalign(0.0)
        box.append(detail)
        dialog.set_extra_child(box)

        dialog.add_response('close', _('Close'))
        dialog.set_close_response('close')
        dialog.set_response_enabled('close', False)

        state = {'ok': False, 'result': None}

        def _update(text, fraction):
            detail.set_text(text)
            if fraction is None:
                progress.pulse()
            else:
                progress.set_fraction(fraction)
                progress.set_text(f'{int(fraction * 100)}%')
            return GLib.SOURCE_REMOVE

        def report(text, fraction=None):
            # Called from the worker thread: GTK is touched on the main loop.
            GLib.idle_add(_update, text, fraction)

        def _finish(ok, result):
            # Close is enabled first, before anything that could raise. The
            # dialog is what holds the UI back, so it must never be the thing
            # that traps it: work returning something that is not text is a
            # mistake in the caller, not a reason to lock the application.
            state['ok'] = ok
            state['result'] = result
            dialog.set_can_close(True)
            dialog.set_response_enabled('close', True)
            progress.set_fraction(1.0 if ok else progress.get_fraction())
            progress.set_text(_('Done') if ok else _('Failed'))
            detail.set_text('')
            if ok:
                message = result if isinstance(result, str) else ''
                dialog.set_body(message or _('Done.'))
            else:
                dialog.set_body(_('It failed: {error}').format(error=result))

        def _on_done(result):
            _finish(True, result)

        def _on_error(error):
            self.log.error(f"'{title}' failed: {error}")
            _finish(False, error)

        def _on_response(_dialog, _response):
            if content is not None:
                content.set_sensitive(True)
            self._busy = False
            if on_close is not None:
                on_close(state['ok'], state['result'])

        dialog.connect('response', _on_response)
        dialog.present(parent if parent is not None else window)
        run_in_background(lambda: work(report),
                          on_done=_on_done,
                          on_error=_on_error,
                          name='progress-dialog')
        return dialog
