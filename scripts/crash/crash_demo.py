#!/usr/bin/python3
"""Manual visual test for the crash dialog fix.

Stacks a second top-level (simulating the rename window) over a main window,
then drives the real MiAZCrashHandler so the crash dialog should appear on top
of the active window, not behind it.
"""

import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, GLib

from MiAZ.frontend.desktop.services.crash import MiAZCrashHandler


class StubApp:
    """Minimal app surface the crash handler needs."""

    def __init__(self, env, window, gtk_app):
        self._env = env
        self._window = window
        self._gtk_app = gtk_app

    def get_env(self):
        return self._env

    def get_widget(self, name):
        return self._window if name == 'window' else None

    def get_service(self, name):
        return None

    def quit(self):
        self._gtk_app.quit()


ENV = {
    'APP': {'shortname': 'MiAZ', 'VERSION': 'crash-demo'},
    'DESKTOP': {'GTK_VERSION': (4, 22, 4), 'ADW_VERSION': (1, 9, 1)},
}


def on_activate(gtk_app):
    main = Adw.ApplicationWindow(application=gtk_app)
    main.set_title('MiAZ (main window)')
    main.set_default_size(900, 640)
    tv = Adw.ToolbarView()
    tv.add_top_bar(Adw.HeaderBar())
    tv.set_content(Gtk.Label(label='Main window. A crash will be forced in ~1s.'))
    main.set_content(tv)
    main.present()

    # Simulated rename window: a separate top-level placed on top of main.
    second = Adw.Window()
    second.set_title('Rename document (simulated top window)')
    second.set_default_size(640, 420)
    second.set_transient_for(main)
    stv = Adw.ToolbarView()
    stv.add_top_bar(Adw.HeaderBar())
    stv.set_content(Gtk.Label(
        label='This window sits ON TOP of the main window.\n'
              'The crash dialog must appear over THIS window.'))
    second.set_content(stv)
    second.present()

    handler = MiAZCrashHandler(StubApp(ENV, main, gtk_app)).install()

    def boom():
        try:
            raise RuntimeError('Forced crash for testing the crash dialog')
        except Exception:
            handler._excepthook(*sys.exc_info())
        return GLib.SOURCE_REMOVE

    GLib.timeout_add(1000, boom)


def main():
    app = Adw.Application(application_id='io.github.t00m.MiAZ.CrashDemo')
    app.connect('activate', on_activate)
    return app.run(None)


if __name__ == '__main__':
    raise SystemExit(main())
