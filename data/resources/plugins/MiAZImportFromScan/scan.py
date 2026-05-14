#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: scan.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Scan plugin
"""

import os
import re
import glob
import subprocess
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

_DESKTOP_SEARCH_PATTERNS = [
    '~/.local/share/applications/*.desktop',
    '~/.applications/*.desktop',
    '~/.local/share/flatpak/exports/share/applications/*.desktop',
    '~/.gnome/apps/*.desktop',
    '~/.kde/share/applications/*.desktop',
    '/usr/share/applications/*.desktop',
    '/usr/local/share/applications/*.desktop',
    '/var/lib/flatpak/exports/share/applications/*.desktop',
    '/var/lib/snapd/desktop/applications/*.desktop',
    '/etc/xdg/autostart/*.desktop',
    '/opt/*/share/applications/*.desktop',
]

plugin_info = {
        'Module':        'scan',
        'Name':          'MiAZImportFromScan',
        'Loader':        'Python3',
        'Description':   _('Import document from scanner'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Data Management',
        'Subcategory':   'Import'
    }


class MiAZImportFromScanPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZImportFromScanPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.factory = self.app.get_service('factory')

        # Connect signals to startup
        self.workspace = self.app.get_widget('workspace')

        # Activate if any scan app is available or a custom command is saved
        scanapp = self._search_scan_app()
        saved_app = self.plugin.get_config_key('scanner_app')
        if scanapp is not None or saved_app:
            if self.workspace.is_loaded():
                self.startup()
            else:
                self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Scan a document'), callback=self.exec_scanner)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def _get_origin(self, desktop_path):
        """Return a human-readable origin label for a .desktop file path."""
        home = os.path.expanduser('~')
        checks = [
            (os.path.join(home, '.local', 'share', 'flatpak'), _('Flatpak')),
            ('/var/lib/flatpak',                                _('Flatpak')),
            ('/var/lib/snapd',                                  _('Snap')),
            (os.path.join(home, '.kde'),                        _('KDE')),
            (os.path.join(home, '.gnome'),                      _('GNOME')),
            ('/opt' + os.sep,                                   _('Third-party')),
            ('/etc/xdg',                                        _('Autostart')),
            (os.path.join(home, '.local', 'share', 'applications'), _('User')),
            (os.path.join(home, '.applications'),               _('User')),
            ('/usr/local/share',                                _('System')),
            ('/usr/share',                                      _('System')),
        ]
        for prefix, label in checks:
            if desktop_path.startswith(prefix):
                return label
        return _('Unknown')

    def _iter_desktop_files(self):
        """Yield (path, origin) tuples for unique .desktop files across all search locations."""
        seen = set()
        for pattern in _DESKTOP_SEARCH_PATTERNS:
            for desktop_path in glob.glob(os.path.expanduser(pattern)):
                name = os.path.basename(desktop_path)
                if name not in seen:
                    seen.add(name)
                    yield desktop_path, self._get_origin(desktop_path)

    def _search_scan_app(self):
        """Return the first scanner application found, or None."""
        try:
            for desktop_path, _origin in self._iter_desktop_files():
                desktop_name = os.path.basename(desktop_path)
                try:
                    appinfo = Gio.DesktopAppInfo.new_from_filename(desktop_path)
                    if appinfo is None:
                        continue
                    categories = appinfo.get_categories()
                    if categories is not None:
                        if re.search('scan', categories, re.IGNORECASE):
                            return appinfo
                except TypeError as error:
                    self.log.debug(f"Skipping desktop entry '{desktop_name}': {error}")
        except AttributeError as error:
            # Not available in Windows/MSYS2
            self.log.error(f"Plugin 'scan' couldn't be activated: {error}")
        return None

    def _search_scan_apps(self):
        """Return (appinfo, origin) pairs for all scanner applications found on the system."""
        scanapps = []
        try:
            for desktop_path, origin in self._iter_desktop_files():
                desktop_name = os.path.basename(desktop_path)
                try:
                    appinfo = Gio.DesktopAppInfo.new_from_filename(desktop_path)
                    if appinfo is None:
                        continue
                    categories = appinfo.get_categories()
                    if categories is not None:
                        if re.search('scan', categories, re.IGNORECASE):
                            scanapps.append((appinfo, origin))
                except TypeError as error:
                    self.log.debug(f"Skipping desktop entry '{desktop_name}': {error}")
        except AttributeError as error:
            self.log.error(f"Could not search scanner apps: {error}")
        return scanapps

    def exec_scanner(self, *args):
        """Launch the configured scanner app, or fall back to auto-detection."""
        saved_app = self.plugin.get_config_key('scanner_app')
        if saved_app:
            # Try to launch as a desktop app ID first
            try:
                appinfo = Gio.DesktopAppInfo.new(saved_app)
                if appinfo is not None:
                    appinfo.launch([], None)
                    return
            except Exception:
                pass
            # Fall back to treating it as a shell command
            try:
                subprocess.Popen(saved_app.split())
            except Exception as error:
                self.log.error(f"Failed to launch scanner '{saved_app}': {error}")
        else:
            scanapp = self._search_scan_app()
            if scanapp is not None:
                scanapp.launch([], None)

    def show_settings(self, widget):
        """Display a preferences dialog for choosing the scanner application."""
        dialog = Adw.PreferencesDialog()
        desc = self.plugin.get_plugin_info_key('Description')
        page = Adw.PreferencesPage(
            title=_(desc),
            icon_name='io.github.t00m.MiAZ-config-symbolic'
        )
        dialog.add(page)

        group = Adw.PreferencesGroup(title=_('Scanner application'))
        page.add(group)

        scan_apps = self._search_scan_apps()
        saved_app = self.plugin.get_config_key('scanner_app')

        if scan_apps:
            app_ids = [app.get_id() for app, _origin in scan_apps]
            app_names = [
                f"{app.get_display_name()} ({origin})"
                for app, origin in scan_apps
            ]

            string_list = Gtk.StringList()
            for name in app_names:
                string_list.append(name)

            combo = Adw.ComboRow(title=_('Application'))
            combo.set_subtitle(_('Scanner application to launch'))
            combo.set_model(string_list)

            if saved_app and saved_app in app_ids:
                combo.set_selected(app_ids.index(saved_app))
            else:
                combo.set_selected(0)
                self.plugin.set_config_key('scanner_app', app_ids[0])

            def _on_combo_changed(row, gparam):
                pos = row.get_selected()
                if 0 <= pos < len(app_ids):
                    self.plugin.set_config_key('scanner_app', app_ids[pos])
                    self.log.debug(f"Scanner app set to: {app_ids[pos]}")

            combo.connect('notify::selected', _on_combo_changed)
            group.add(combo)
        else:
            # No scanner app detected. Let the user type a command
            entry_row = Adw.EntryRow(title=_('Scanner command'))
            entry_row.set_text(saved_app or '')
            entry_row.set_show_apply_button(True)

            def _on_entry_apply(row):
                cmd = row.get_text().strip()
                if cmd:
                    self.plugin.set_config_key('scanner_app', cmd)
                    self.log.debug(f"Scanner command set to: {cmd}")

            entry_row.connect('apply', _on_entry_apply)
            group.add(entry_row)

            hint = Adw.ActionRow(
                title=_('No scanner application detected'),
                subtitle=_('Enter the command used to launch your scanner software')
            )
            hint.set_sensitive(False)
            group.add(hint)

        dialog.present(widget.get_root())
