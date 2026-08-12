# File: crash.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Desktop crash handler. Shows a HIG dialog on unhandled errors.

import sys
import threading
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog, get_log_file
from MiAZ.backend.crash import (ISSUE_URL, handle_exception, format_summary)


class MiAZCrashHandler(GObject.GObject):
    """
    Capture unhandled exceptions (main thread and worker threads), log them,
    and present a dialog explaining what failed with the Python traceback,
    options to copy/save the report and a link to the issue tracker.
    """

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Crash')
        self._dialog_open = False

    def install(self):
        """Override the interpreter hooks to add the dialog on top of logging."""
        sys.excepthook = self._excepthook

        def _thread_hook(args):
            if issubclass(args.exc_type, SystemExit):
                return
            self._excepthook(args.exc_type, args.exc_value, args.exc_traceback)
        threading.excepthook = _thread_hook
        self.log.debug("Crash handler installed")
        return self

    def _excepthook(self, exc_type, exc_value, exc_tb):
        # Log + console message (shared with the backend handler), then show
        # the dialog on the main thread (excepthook may run on a worker thread).
        env = self.app.get_env()
        report = handle_exception(self.log, env, exc_type, exc_value, exc_tb,
                                  get_log_file())
        if report is None:  # KeyboardInterrupt: already delegated
            return
        summary = format_summary(exc_type, exc_value)
        GLib.idle_add(self._present_dialog, summary, report)

    def _present_dialog(self, summary, report):
        # A single crash dialog at a time avoids stacking on cascading errors.
        if self._dialog_open:
            return GLib.SOURCE_REMOVE
        self._dialog_open = True
        try:
            self._build_and_present(summary, report)
        except Exception as error:
            # Never let the crash handler crash; fall back to the console.
            self._dialog_open = False
            self.log.error(f"Could not display crash dialog: {error}")
        return GLib.SOURCE_REMOVE

    def _present_target(self, fallback):
        """Return the window the user is currently interacting with, so the
        crash dialog appears on top of it. A crash may surface while a separate
        top-level (e.g. the rename window) is above the main window; presenting
        against the main window would leave the dialog hidden behind it."""
        try:
            toplevels = Gtk.Window.get_toplevels()
            for i in range(toplevels.get_n_items()):
                win = toplevels.get_item(i)
                if win is not None and win.get_visible() and win.is_active():
                    return win
        except Exception as error:
            self.log.debug(f"Could not resolve active window: {error}")
        return fallback

    def _build_and_present(self, summary, report):
        window = self.app.get_widget('window')

        dialog = Adw.AlertDialog.new()
        dialog.set_heading_use_markup(True)
        dialog.set_body_use_markup(True)
        dialog.set_heading(_("MiAZ encountered an unexpected error"))
        dialog.set_body(_("The application ran into a problem. You can help "
                          "fix it by reporting the error below."))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_hexpand(True)

        # Short, selectable error summary.
        summary_label = Gtk.Label(label=summary, xalign=0.0, wrap=True,
                                  selectable=True)
        summary_label.add_css_class('error')
        box.append(summary_label)

        # Link to the issue tracker.
        link = Gtk.LinkButton(uri=ISSUE_URL, label=_("Report an issue"))
        link.set_halign(Gtk.Align.START)
        box.append(link)

        # Expandable full traceback in a read-only monospace view.
        expander = Gtk.Expander(label=_("Technical details"))
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(220)
        scrolled.set_min_content_width(480)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_monospace(True)
        textview.get_buffer().set_text(report)
        scrolled.set_child(textview)
        expander.set_child(scrolled)
        box.append(expander)

        # Copy / Save actions (plain buttons so they do not dismiss the dialog).
        btnbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btnbox.set_halign(Gtk.Align.START)
        btn_copy = Gtk.Button(label=_("Copy"))
        btn_copy.connect('clicked', self._on_copy, report)
        btn_save = Gtk.Button(label=_("Save…"))
        btn_save.connect('clicked', self._on_save, report)
        btnbox.append(btn_copy)
        btnbox.append(btn_save)
        box.append(btnbox)

        dialog.set_extra_child(box)

        # When a window exists the crash may be recoverable, so let the user
        # choose. At startup (no window) only closing makes sense.
        if window is not None:
            dialog.add_response('continue', _("Try to Continue"))
            dialog.set_response_appearance('continue',
                                           Adw.ResponseAppearance.SUGGESTED)
        dialog.add_response('quit', _("Close MiAZ"))
        dialog.set_response_appearance('quit',
                                       Adw.ResponseAppearance.DESTRUCTIVE)
        default = 'continue' if window is not None else 'quit'
        dialog.set_default_response(default)
        dialog.set_close_response(default)
        dialog.connect('response', self._on_response)
        dialog.present(self._present_target(window))

    def _on_response(self, dialog, response):
        self._dialog_open = False
        if response == 'quit':
            actions = self.app.get_service('actions')
            if actions is not None:
                actions.exit_app()
            else:
                self.app.quit()

    def _on_copy(self, button, report):
        try:
            display = Gdk.Display.get_default()
            display.get_clipboard().set(report)
            self._toast(_("Error report copied to clipboard"))
        except Exception as error:
            self.log.error(f"Could not copy report: {error}")

    def _on_save(self, button, report):
        window = self.app.get_widget('window')
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Save error report"))
        dialog.set_initial_name("MiAZ-error-report.log")
        dialog.save(window, None, self._on_save_finish, report)

    def _on_save_finish(self, dialog, result, report):
        try:
            gfile = dialog.save_finish(result)
            with open(gfile.get_path(), 'w', encoding='utf-8') as handler:
                handler.write(report)
            self._toast(_("Error report saved"))
        except GLib.Error:
            # User cancelled the file dialog.
            pass
        except Exception as error:
            self.log.error(f"Could not save report: {error}")

    def _toast(self, message):
        dialogs = self.app.get_service('dialogs')
        if dialogs is not None:
            dialogs.show_toast(message)
