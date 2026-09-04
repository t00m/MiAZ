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
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.6',
        'Category':      'Documents',
        'Subcategory':   'Import',
        'MenuEntries':   [
            ('scan', _('Scan a document')),
        ]
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
            self.plugin.install_menu_entries({'scan': self.exec_scanner})
            self.plugin.install_settings_group(self.build_settings)
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

    def build_settings(self):
        """Return the scanner settings as a group, for the Repository Settings tab."""
        group = Adw.PreferencesGroup(title=_('Scanner application'))
        scan_apps = self._search_scan_apps()
        saved_app = self.plugin.get_config_key('scanner_app')

        if not scan_apps:
            # A row saying why, rather than no group at all: an empty space
            # does not tell anyone that no scanner application was found.
            row = Adw.ActionRow(title=_('No scanner application found'))
            row.set_subtitle(_('Install one, for example Simple Scan'))
            group.add(row)
            return group

        app_ids = [app.get_id() for app, _origin in scan_apps]
        app_names = [f"{app.get_display_name()} ({origin})"
                     for app, origin in scan_apps]

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

        combo.connect('notify::selected',
                      lambda row, _gparam, ids=app_ids:
                          self.plugin.set_config_key(
                              'scanner_app', ids[row.get_selected()]))
        group.add(combo)
        return group

    def show_settings(self, widget):
        # Kept for the Plugins tab button until Task 7 removes it; wraps the
        # same group build_settings() contributes to the Settings tab.
        dialog = Adw.PreferencesDialog()
        desc = self.plugin.get_plugin_info_key('Description')
        page = Adw.PreferencesPage(
            title=_(desc),
            icon_name='io.github.t00m.MiAZ-config-symbolic'
        )
        dialog.add(page)
        page.add(self.build_settings())
        dialog.present(widget.get_root())
