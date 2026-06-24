#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: autoscan.py
# Author: Tomas Virseda
# License: GPL v3
# Description: Auto scan plugin
"""

import os
import re
import glob
import subprocess
import threading
import shutil
from datetime import datetime
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.status import MiAZStatus

plugin_info = {
    'Module':      'autoscan',
    'Name':        'MiAZAutoScan',
    'Loader':      'Python3',
    'Description': _('Scan documents in background and import them directly into the repository'),
    'Authors':     'Tomas Virseda <tomasvirseda@gmail.com>',
    'Copyright':   'Copyright \u00a9 2026 Tomas Virseda',
    'Website':     'http://github.com/t00m/MiAZ',
    'Help':        'http://github.com/t00m/MiAZ/README.adoc',
    'Version':     '0.1',
    'Category':    'Data Management',
    'Subcategory': 'Import',
}

_RESOLUTIONS = ['100', '200', '300', '600']
_MODES = ['Color', 'Gray']
_SOURCES = ['Flatbed', 'ADF', 'ADF Duplex']
_FORMATS = ['pdf', 'tiff', 'png', 'jpeg']

# Programs needed to detect the scanner and its sources. They are shipped by
# the SANE project (package sane-utils or sane-backends, depending on distro).
_REQUIRED_TOOLS = ['scanimage']


class MiAZAutoScanPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZAutoScanPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.workspace = self.app.get_widget('workspace')

        # The plugin always installs its Add menu entry, even when the scanner
        # tools are missing. In that case the entry reports the missing
        # programs when used, instead of silently disappearing.
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect(
                'workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def _missing_tools(self):
        """Return the list of required programs not found on PATH."""
        return [tool for tool in _REQUIRED_TOOLS if shutil.which(tool) is None]

    def startup(self, *args):
        if self.plugin.started():
            return
        self.plugin.set_started(True)

        missing = self._missing_tools()
        if missing:
            self.log.warning(
                f"Scanner tools not found on PATH: {', '.join(missing)}")
            menuitem = self.factory.create_menuitem(
                name=self.plugin.get_menu_item_name(),
                label=_('Scan and import (auto)'),
                callback=self._on_missing_tools,
            )
            self.plugin.install_menu_entry(menuitem)
            self._refresh_add_menu()
            return

        # Detect the scanner sources in a background thread: querying the
        # device wakes it up and can take several seconds. The menu is built
        # back on the main thread once detection finishes.
        threading.Thread(target=self._detect_sources, daemon=True).start()

    def _detect_sources(self):
        devices = self._list_devices()
        sources = []
        if devices:
            device = self.plugin.get_config_key('device')
            if not device or device not in devices:
                device = devices[0]
                self.plugin.set_config_key('device', device)
            sources = self._list_sources(device)
            if not sources:
                sources = list(_SOURCES)
        GLib.idle_add(self._build_source_menu, sources)

    def _build_source_menu(self, sources):
        base = self.plugin.get_menu_item_name()

        if not sources:
            # Tools are present but no scanner was detected. Install a single
            # entry that triggers the normal scan flow, which then reports the
            # missing scanner.
            menuitem = self.factory.create_menuitem(
                name=base,
                label=_('Scan and import (auto)'),
                callback=self._on_scan,
            )
            self.plugin.install_menu_entry(menuitem)
            self._refresh_add_menu()
            return False

        sources_menu = Gio.Menu()
        for source in sources:
            slug = source.lower().replace(' ', '-')
            menuitem = self.factory.create_menuitem(
                name=f"{base}-{slug}",
                label=source,
                callback=self._on_scan_source,
                data=source,
            )
            sources_menu.append_item(menuitem)

        # A submenu menu item carries the per-source items into both the
        # workspace selection menu and the headerbar Add menu. install_menu_entry
        # registers it under the canonical 'plugin-menuitem-<name>' key, which is
        # the key the Add menu mirrors.
        submenu_item = Gio.MenuItem.new_submenu(
            _('Scan and import (auto)'), sources_menu)
        self.plugin.install_menu_entry(submenu_item)
        self._refresh_add_menu()
        return False

    def _refresh_add_menu(self):
        """Rebuild the headerbar Add menu so it picks up our entry.

        Detection runs asynchronously, so our menu item may be registered after
        the Add menu was first built at application startup.
        """
        mainwindow = self.app.get_widget('mainwindow')
        if mainwindow is not None and hasattr(mainwindow, '_populate_add_menu'):
            mainwindow._populate_add_menu()

    def _on_missing_tools(self, *args):
        missing = self._missing_tools()
        tools = ', '.join(missing) if missing else ', '.join(_REQUIRED_TOOLS)
        self.srvdlg.show_error(
            _('Scanner tools not installed'),
            _('These programs are needed to detect the scanner but were not '
              'found: {tools}. Install the SANE package that provides them '
              '(for example sane-utils or sane-backends) and restart MiAZ.'
              ).format(tools=tools),
        )

    def _list_sources(self, device):
        """Return the source types reported by the scanner (Flatbed, ADF...)."""
        try:
            result = subprocess.run(
                ['scanimage', '--help', '--device-name', device],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if not stripped.startswith('--source'):
                    continue
                # Format: --source Flatbed|ADF|ADF Duplex [Flatbed]
                rest = stripped[len('--source'):].strip()
                rest = re.sub(r'\[.*?\]', '', rest).strip()
                if rest:
                    return [s.strip() for s in rest.split('|') if s.strip()]
        except Exception as error:
            self.log.error(f"Failed to list scanner sources: {error}")
        return []

    def _list_devices(self):
        try:
            result = subprocess.run(
                ['scanimage', '-L'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            devices = []
            for line in result.stdout.splitlines():
                match = re.search(r"device\s+`([^']+)'", line)
                if match:
                    devices.append(match.group(1))
            return devices
        except Exception as error:
            self.log.error(f"Failed to list scanner devices: {error}")
            return []

    def _on_scan(self, *args):
        """Scan using the source saved in the plugin settings."""
        self._start_scan(None)

    def _on_scan_source(self, action, param, source):
        """Scan using the source picked from the Add submenu."""
        self._start_scan(source)

    def _start_scan(self, source_override):
        self.app.set_status(MiAZStatus.BUSY)
        threading.Thread(
            target=self._do_scan,
            kwargs={'source_override': source_override},
            daemon=True,
        ).start()

    def _do_scan(self, source_override=None):
        env = self.app.get_env()
        tmp_dir = env['LPATH']['TMP']
        os.makedirs(tmp_dir, exist_ok=True)

        device = self.plugin.get_config_key('device')
        if not device:
            devices = self._list_devices()
            if not devices:
                GLib.idle_add(
                    self._on_scan_error,
                    _('No scanner device detected. Check your scanner '
                      'connection and SANE configuration.'),
                )
                return
            device = devices[0]
            self.plugin.set_config_key('device', device)

        resolution = self.plugin.get_config_key('resolution') or '300'
        mode = self.plugin.get_config_key('mode') or 'Color'
        source = source_override or self.plugin.get_config_key('source') or 'Flatbed'
        fmt = self.plugin.get_config_key('format') or 'pdf'

        now = datetime.now()
        date_part = now.strftime('%Y%m%d')
        time_part = now.strftime('%H%M%S')
        country = self.plugin.get_config_key('default_country') or ''
        group = self.plugin.get_config_key('default_group') or ''
        sentby = self.plugin.get_config_key('default_sentby') or 'SCAN'
        purpose = self.plugin.get_config_key('default_purpose') or ''
        concept = self.plugin.get_config_key('default_concept') or 'Autoscan'
        # Build the concept in MiAZ's canonical form (a valid uppercase key) so
        # the scanned document is born normalised and does not show up as a
        # pending rename.
        concept = self.util.valid_key(f"{concept}_{time_part}".upper())
        sentto = self.plugin.get_config_key('default_sentto') or ''
        basename = f"{date_part}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}"

        if source == 'Flatbed':
            self._scan_single(tmp_dir, basename, device, resolution,
                              mode, source, fmt)
        else:
            self._scan_batch(tmp_dir, basename, device, resolution,
                             mode, source, fmt)

    def _scan_single(self, tmp_dir, basename, device,
                     resolution, mode, source, fmt):
        fmt = self._sane_format(fmt)
        output_file = os.path.join(tmp_dir, f"{basename}.{fmt}")
        cmd = [
            'scanimage',
            f'--device={device}',
            f'--resolution={resolution}',
            f'--mode={mode}',
            f'--source={source}',
            f'--format={fmt}',
            f'--output-file={output_file}',
        ]
        self.log.debug(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120)
            self._log_result('single', cmd, result)
            if result.returncode != 0:
                msg = result.stderr.strip() or result.stdout.strip()
                GLib.idle_add(self._on_scan_error, msg)
                return
            if not os.path.exists(output_file):
                GLib.idle_add(self._on_scan_error,
                              _('Scan completed but no output file was created'))
                return
            self._import_and_finish([output_file])
        except subprocess.TimeoutExpired:
            GLib.idle_add(self._on_scan_error,
                          _('Scan timed out after 120 seconds'))
        except Exception as error:
            GLib.idle_add(self._on_scan_error, str(error))

    def _scan_batch(self, tmp_dir, basename, device,
                    resolution, mode, source, fmt):
        fmt = self._sane_format(fmt)
        pattern = os.path.join(tmp_dir, f"{basename}_%d.{fmt}")
        glob_pattern = os.path.join(tmp_dir, f"{basename}_*.{fmt}")

        # Drop any stale pages left from a previous run with the same basename
        # so the post-scan glob only picks up what this run produced.
        for stale in glob.glob(glob_pattern):
            try:
                os.unlink(stale)
            except OSError:
                pass

        cmd = [
            'scanimage',
            f'--device={device}',
            f'--resolution={resolution}',
            f'--mode={mode}',
            f'--source={source}',
            f'--format={fmt}',
            f'--batch={pattern}',
            '--batch-print',
        ]
        self.log.debug(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300)
            self._log_result('batch', cmd, result)
            # Two ADF realities make stdout and the exit code unreliable:
            #  - --batch-print emits nothing on some backends (eSCL/airscan),
            #    so result.stdout is empty even though pages were written.
            #  - the end-of-feeder ("Document feeder out of documents") makes
            #    scanimage exit non-zero on some versions.
            # So discover the produced pages straight from disk by globbing the
            # batch pattern, ordered by page number.
            created = sorted(
                glob.glob(glob_pattern), key=self._batch_page_index)
            self.log.debug(f"[batch] pages found on disk: {created}")
            if not created:
                msg = result.stderr.strip() or result.stdout.strip() or _(
                    'Scan completed but no output files were created')
                GLib.idle_add(self._on_scan_error, msg)
                return
            self._import_and_finish(created)
        except subprocess.TimeoutExpired:
            GLib.idle_add(self._on_scan_error,
                          _('Scan timed out after 300 seconds'))
        except Exception as error:
            GLib.idle_add(self._on_scan_error, str(error))

    def _log_result(self, mode, cmd, result):
        """Dump the full scanimage invocation and its output to the console."""
        self.log.debug(f"[{mode}] command: {' '.join(cmd)}")
        self.log.debug(f"[{mode}] return code: {result.returncode}")
        stdout = (result.stdout or '').strip()
        stderr = (result.stderr or '').strip()
        self.log.debug(f"[{mode}] stdout:\n{stdout if stdout else '(empty)'}")
        if result.returncode != 0 or stderr:
            self.log.error(f"[{mode}] stderr:\n{stderr if stderr else '(empty)'}")
        else:
            self.log.debug(f"[{mode}] stderr:\n{stderr if stderr else '(empty)'}")

    def _batch_page_index(self, path):
        """Sort key: the trailing _<n> page number scanimage appends in batch."""
        match = re.search(r'_(\d+)\.[^.]+$', os.path.basename(path))
        return int(match.group(1)) if match else 0

    def _sane_format(self, fmt):
        lookup = {
            'pdf': 'pdf',
            'tiff': 'tiff',
            'png': 'png',
            'jpeg': 'jpeg',
        }
        return lookup.get(fmt, 'pdf')

    def _import_and_finish(self, filepaths):
        watcher = self.app.get_service('watcher')
        watcher.set_active(False)
        imported = []
        failed = []
        try:
            for filepath in filepaths:
                try:
                    btarget = self.util.filename_normalize(filepath)
                    target = os.path.join(self.repository.docs, btarget)
                    # The source is a temporary scan file, so record the
                    # scanner as the provenance instead of that temp path.
                    self.util.filename_import(filepath, target,
                                              origin={'type': 'scan'})
                    imported.append(btarget)
                except Exception as error:
                    failed.append(os.path.basename(filepath))
                    self.log.error(
                        f"Could not import '{filepath}': {error}")
        finally:
            GLib.idle_add(watcher.set_active, True)
            GLib.idle_add(self.app.set_status, MiAZStatus.RUNNING)
            GLib.idle_add(self.workspace.update)

        if imported:
            if len(imported) == 1:
                msg = _('1 document scanned and imported')
            else:
                msg = _('{count} documents scanned and imported').format(
                    count=len(imported))
            GLib.idle_add(self.srvdlg.show_toast, msg)
            # Open the rename dialog so the user can review and accept each
            # imported document, whether it is already valid or pending review.
            GLib.idle_add(self._open_rename_dialogs, imported)
        if failed:
            GLib.idle_add(self.srvdlg.show_error,
                          _('Some documents could not be imported'),
                          '\n'.join(failed))

    def _open_rename_dialogs(self, basenames):
        """Open the rename dialog for each imported document, one after another.

        The dialogs are chained: the next one opens only after the current is
        closed, so multi-page (ADF) scans do not stack a pile of dialogs.
        """
        actions = self.app.get_service('actions')
        pending = list(basenames)
        if not pending:
            return False
        self._open_next_rename_dialog(actions, pending)
        return False

    def _open_next_rename_dialog(self, actions, pending):
        if not pending:
            return
        basename = pending.pop(0)
        actions._document_rename_single(basename)
        dialog = self.app.get_widget('dialog-rename')
        if dialog is not None and pending:
            dialog.connect(
                'closed',
                lambda *_a: self._open_next_rename_dialog(actions, pending))

    def _on_scan_error(self, error_msg):
        self.log.error(f"Scan failed: {error_msg}")
        self.app.set_status(MiAZStatus.RUNNING)
        self.srvdlg.show_error(_('Scan failed'), error_msg)

    def show_settings(self, widget):
        dialog = Adw.PreferencesDialog()
        desc = self.plugin.get_plugin_info_key('Description')
        page = Adw.PreferencesPage(
            title=_(desc),
            icon_name='io.github.t00m.MiAZ-config-symbolic',
        )
        dialog.add(page)

        group_scan = Adw.PreferencesGroup(
            title=_('Scanner settings'),
            description=_('Configure the scanner device and scan parameters'),
        )
        page.add(group_scan)

        devices = self._list_devices()
        saved_device = self.plugin.get_config_key('device')

        if devices:
            string_list = Gtk.StringList()
            for dev in devices:
                string_list.append(dev)
            combo_device = Adw.ComboRow(
                title=_('Scanner device'),
                subtitle=_('SANE device to use for scanning'),
                model=string_list,
            )
            if saved_device and saved_device in devices:
                combo_device.set_selected(devices.index(saved_device))
            elif devices:
                combo_device.set_selected(0)
                self.plugin.set_config_key('device', devices[0])

            combo_device.connect(
                'notify::selected',
                lambda row, _gparam, devs=devices:
                    self.plugin.set_config_key(
                        'device', devs[row.get_selected()]),
            )
            group_scan.add(combo_device)
        else:
            entry_device = Adw.EntryRow(
                title=_('Scanner device'),
            )
            entry_device.set_text(saved_device or '')
            entry_device.set_show_apply_button(True)
            entry_device.connect(
                'apply',
                lambda row: self.plugin.set_config_key(
                    'device', row.get_text().strip()),
            )
            group_scan.add(entry_device)

        combo_res = self._make_combo_row(
            title=_('Resolution'),
            subtitle=_('Scan resolution in DPI'),
            options=_RESOLUTIONS,
            saved_key='resolution',
            default='300',
        )
        group_scan.add(combo_res)

        combo_mode = self._make_combo_row(
            title=_('Color mode'),
            subtitle=_('Color or grayscale scan'),
            options=_MODES,
            saved_key='mode',
            default='Color',
        )
        group_scan.add(combo_mode)

        combo_source = self._make_combo_row(
            title=_('Source'),
            subtitle=_('Flatbed or Automatic Document Feeder'),
            options=_SOURCES,
            saved_key='source',
            default='Flatbed',
        )
        group_scan.add(combo_source)

        combo_format = self._make_combo_row(
            title=_('Format'),
            subtitle=_('Output file format'),
            options=_FORMATS,
            saved_key='format',
            default='pdf',
        )
        group_scan.add(combo_format)

        group_fields = Adw.PreferencesGroup(
            title=_('Default filename fields'),
            description=_('Default values for the 7-field document name. '
                          'Leave empty to omit a field.'),
        )
        page.add(group_fields)

        field_configs = [
            ('default_country', _('Country'), 'Country'),
            ('default_group', _('Group'), 'Group'),
            ('default_sentby', _('Sent by'), 'SentBy'),
            ('default_purpose', _('Purpose'), 'Purpose'),
            ('default_sentto', _('Sent to'), 'SentTo'),
        ]
        for key, title, config_name in field_configs:
            items = [('', '')]  # (code, display)  empty = no default
            config = self.app.get_config(config_name)
            if config is not None:
                used = config.load_used()
                for code in sorted(used.keys()):
                    desc = used[code] or code
                    items.append((code, desc))
            string_list = Gtk.StringList()
            for _code, desc in items:
                string_list.append(desc)
            combo = Adw.ComboRow(
                title=title,
                subtitle=_('Select a default value or leave empty'),
                model=string_list,
            )
            saved = self.plugin.get_config_key(key) or ''
            codes = [c for c, _d in items]
            if saved in codes:
                combo.set_selected(codes.index(saved))
            else:
                combo.set_selected(0)
            combo.connect(
                'notify::selected',
                lambda row, _gparam, itms=items, k=key:
                    self.plugin.set_config_key(k, itms[row.get_selected()][0]),
            )
            group_fields.add(combo)

        entry_concept = Adw.EntryRow(title=_('Concept'))
        saved_concept = self.plugin.get_config_key('default_concept') or 'Autoscan'
        entry_concept.set_text(saved_concept)
        entry_concept.set_show_apply_button(True)
        entry_concept.connect(
            'apply',
            lambda row: self.plugin.set_config_key(
                'default_concept', row.get_text().strip()),
        )
        group_fields.add(entry_concept)

        dialog.present(widget.get_root())

    def _make_combo_row(self, title, subtitle, options, saved_key, default):
        string_list = Gtk.StringList()
        for opt in options:
            string_list.append(opt)
        combo = Adw.ComboRow(
            title=title,
            subtitle=subtitle,
            model=string_list,
        )
        saved = self.plugin.get_config_key(saved_key) or default
        if saved in options:
            combo.set_selected(options.index(saved))
        else:
            combo.set_selected(options.index(default))
            self.plugin.set_config_key(saved_key, default)
        combo.connect(
            'notify::selected',
            lambda row, _gparam, opts=options, key=saved_key:
                self.plugin.set_config_key(key, opts[row.get_selected()]),
        )
        return combo
