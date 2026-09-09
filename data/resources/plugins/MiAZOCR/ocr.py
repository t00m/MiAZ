# pylint: disable=E1101

"""
# File: ocr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: OCR plugin. Extract text from PDF documents and store it as a
#              note via the MiAZNotes plugin.
"""

import os
import shutil
import tempfile
import subprocess
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import GObject  # noqa: F401
from gi.repository import Gtk

from MiAZ.backend.tasks import run_in_background
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'ocr',
        'Name':          'MiAZOCR',
        'Loader':        'Python3',
        'Description':   _('Extract text from PDF documents with OCR and save it as a note'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2026 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Category':      'Documents',
        'Subcategory':   'Annotation',
        'MenuEntries':   [
            ('extract', _('Extract text (OCR)…')),
        ],
        'Dependencies':  'MiAZNotes',
    }

# Command line tools the plugin needs. ocrmypdf is mandatory (it wraps
# tesseract + ghostscript); without it the plugin refuses to activate.
REQUIRED_TOOLS = ('ocrmypdf',)


class MiAZOCRPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZOCRPlugin'
    plugin = None

    # Activation lifecycle
    def do_activate(self):
        """Plugin activation. Vetoes activation if the OCR tooling is missing."""
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.workspace = self.app.get_widget('workspace')

        # Refuse to activate when the required tools are not installed. The
        # loader catches this exception, cleans up and leaves the plugin
        # disabled (not written to plugins-used.json).
        missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
        if missing:
            self._notify_missing_tools(missing)
            raise RuntimeError(f"Required OCR tools not found: {', '.join(missing)}")

        if self.workspace is not None and self.workspace.is_loaded():
            self.startup()
        elif self.workspace is not None:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            self.plugin.install_menu_entries({'extract': self._on_ocr})
            self.plugin.install_settings_group(self.build_settings)
            self.plugin.set_started(started=True)

    # Helpers
    def _active_parent(self):
        """Window to anchor dialogs on.

        Plugins are enabled from the Repository Settings window, a separate
        modal window stacked on top of the main one. Anchoring on the main
        window would hide the dialog behind it, so prefer the settings window
        when it is visible and fall back to the main window otherwise.
        """
        try:
            repo_settings = self.app.get_widget('window-repo-settings')
            if repo_settings is not None and repo_settings.get_visible():
                return repo_settings
        except Exception:
            pass
        return self.app.get_widget('window')

    def _notify_missing_tools(self, missing):
        title = _('OCR tools not installed')
        body = _(
            'MiAZOCR needs the following command line tool(s) which are not '
            'installed:\n\n<b>{tools}</b>\n\nInstall them and enable the plugin '
            'again:\n\n'
            '• Fedora: <tt>sudo dnf install ocrmypdf poppler-utils</tt>\n'
            '• Debian/Ubuntu: <tt>sudo apt install ocrmypdf poppler-utils</tt>\n'
            '• Arch: <tt>sudo pacman -S ocrmypdf poppler</tt>'
        ).format(tools=', '.join(missing))
        # do_activate() raises right after this call, so the loader unloads this
        # plugin within the same synchronous stack. Present the dialog on the
        # next main-loop iteration through the persistent dialogs service, with
        # a closure that does not reference this (soon torn-down) instance.
        srvdlg = self.srvdlg
        log = self.log
        window = self._active_parent()

        def _present():
            try:
                srvdlg.show_error(title=title, body=body, parent=window)
            except Exception as error:
                log.error(f"{title}: {missing} ({error})")
            return False

        GLib.idle_add(_present)

    def _is_eligible(self, item):
        """Eligible = a reviewed (not pending) PDF document."""
        extension = (getattr(item, 'extension', '') or '').lower()
        is_pdf = extension == 'pdf' or item.id.lower().endswith('.pdf')
        return bool(item.active) and is_pdf

    def _available_languages(self):
        """List installed tesseract languages, falling back to English."""
        try:
            out = subprocess.run(['tesseract', '--list-langs'],
                                 capture_output=True, text=True, timeout=10)
            langs = []
            for line in out.stdout.splitlines()[1:]:
                line = line.strip()
                if line and line != 'osd':
                    langs.append(line)
            if langs:
                return sorted(langs)
        except Exception as error:
            self.log.debug(f"Could not list tesseract languages: {error}")
        return ['eng']

    def _default_language(self, langs):
        last = self.plugin.get_config_key('lang')
        if last and last in langs:
            return last
        if 'eng' in langs:
            return 'eng'
        return langs[0] if langs else 'eng'

    # Menu callback
    def _on_ocr(self, *args):
        items = self.workspace.get_selected_items()
        if not items:
            self.srvdlg.show_error(
                title=_('OCR'),
                body=_('Select at least one document'),
                parent=self._active_parent())
            return

        eligible = [item for item in items if self._is_eligible(item)]
        skipped = len(items) - len(eligible)
        if not eligible:
            self.srvdlg.show_error(
                title=_('No documents to process'),
                body=_('OCR runs only on reviewed PDF documents. Documents still '
                       'pending review and non-PDF files are skipped.'),
                parent=self._active_parent())
            return

        self._show_options_dialog(eligible, skipped)

    def _show_options_dialog(self, eligible, skipped):
        langs = self._available_languages()
        default = self._default_language(langs)

        box = self.factory.create_box_vertical(margin=12, spacing=12,
                                               hexpand=True, vexpand=True)
        group = Adw.PreferencesGroup()

        string_list = Gtk.StringList()
        for lang in langs:
            string_list.append(lang)
        combo = Adw.ComboRow(title=_('Document language'))
        combo.set_subtitle(_('Language used by the OCR engine'))
        combo.set_model(string_list)
        combo.set_selected(langs.index(default))
        group.add(combo)

        force_row = Adw.SwitchRow(
            title=_('Force OCR'),
            subtitle=_('Ignore any existing text layer and OCR every page'))
        group.add(force_row)
        box.append(group)

        dialog = self.srvdlg.show_action(title=_('OCR options'), widget=box)
        data = (eligible, skipped, combo, langs, force_row)
        dialog.connect('response', self._on_options_response, data)
        dialog.present(self.workspace.get_root())

    def _on_options_response(self, dialog, response, data):
        if response != 'apply':
            return
        eligible, skipped, combo, langs, force_row = data
        idx = combo.get_selected()
        lang = langs[idx] if 0 <= idx < len(langs) else 'eng'
        self.plugin.set_config_key('lang', lang)
        force = force_row.get_active()
        self._suspend = self.app.get_widget('workspace').suspend_updates()
        run_in_background(
            lambda: self._process(eligible, lang, force, skipped),
            on_done=self._finish,
            on_error=self._on_process_crashed,
            name='ocr-process')

    def _on_process_crashed(self, error):
        """The OCR run died outside the per-document try block.

        _finish is what releases the update gate, so without this the workspace
        would stop refreshing for the rest of the session. It reports an error
        rather than a summary: no counts survived the failure.
        """
        self.log.error(f"OCR run failed: {error}")
        self._release_suspend()
        self.srvdlg.show_error(title=_('OCR failed'), body=str(error))

    # Background processing
    def _process(self, items, lang, force, skipped):
        """OCR every document. Returns (created, failed, skipped) for _finish."""
        created = 0
        failed = 0
        for item in items:
            try:
                text = self._extract_text(item, lang, force)
                if text and text.strip() and self._create_note(item.id, text, lang):
                    created += 1
                    GLib.idle_add(self.srvdlg.show_toast,
                                  _('OCR finished: {doc}').format(doc=item.id))
                else:
                    failed += 1
                    self.log.warning(f"No text stored for '{item.id}'")
                    GLib.idle_add(self.srvdlg.show_toast,
                                  _('OCR found no text: {doc}').format(doc=item.id))
            except Exception as error:
                failed += 1
                self.log.error(f"OCR failed for '{item.id}': {error}")
                GLib.idle_add(self.srvdlg.show_toast,
                              _('OCR failed: {doc}').format(doc=item.id))
        return created, failed, skipped

    def _extract_text(self, item, lang, force):
        source = os.path.join(self.repository.docs, item.id)

        # Fast path: reuse an existing text layer with pdftotext (no OCR).
        if not force and shutil.which('pdftotext') is not None:
            try:
                out = subprocess.run(['pdftotext', source, '-'],
                                     capture_output=True, text=True, timeout=120)
                if out.returncode == 0 and out.stdout.strip():
                    self.log.debug(f"Text layer extracted from '{item.id}' (no OCR needed)")
                    return out.stdout
            except Exception as error:
                self.log.debug(f"pdftotext failed for '{item.id}': {error}")

        # OCR path: ocrmypdf writes the text to a sidecar; the output PDF goes
        # to a temp file and is discarded (the original file is never modified).
        with tempfile.TemporaryDirectory() as tmpdir:
            sidecar = os.path.join(tmpdir, 'out.txt')
            tmp_pdf = os.path.join(tmpdir, 'out.pdf')
            cmd = ['ocrmypdf', '-l', lang, '--sidecar', sidecar]
            cmd.append('--force-ocr' if force else '--skip-text')
            cmd += [source, tmp_pdf]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            if result.returncode != 0:
                self.log.error(f"ocrmypdf error for '{item.id}': {result.stderr.strip()}")
            if os.path.exists(sidecar):
                with open(sidecar, 'r', encoding='utf-8') as fin:
                    return fin.read()
        return ''

    def _create_note(self, doc_id, text, lang):
        plugin_system = self.app.get_service('plugin-system')
        notes_ext = plugin_system.get_extension('notes')
        if notes_ext is None:
            self.log.error("MiAZNotes is not enabled; cannot create note")
            return False
        body = _('# OCR extraction\n\nLanguage: {lang}\n\n{text}').format(
            lang=lang, text=text.strip())
        try:
            if hasattr(notes_ext, 'add_note'):
                notes_ext.add_note(doc_id, body, category='OCR')
            else:
                # Fallback for an older MiAZNotes without the public API: write
                # the note and marshal the UI refresh to the main loop.
                notes_ext.store.create(doc_id, {'Category': 'Documents'}, body)
                if hasattr(notes_ext, '_notes_changed'):
                    GLib.idle_add(notes_ext._notes_changed)
            return True
        except Exception as error:
            self.log.error(f"Could not create note for '{doc_id}': {error}")
            return False

    def _release_suspend(self):
        """Let the workspace refresh again. Safe to reach twice."""
        if getattr(self, '_suspend', None) is not None:
            self._suspend.release()
            self._suspend = None

    def _finish(self, counts):
        created, failed, skipped = counts
        self._release_suspend()
        parts = [_('{n} note(s) created').format(n=created)]
        if failed:
            parts.append(_('{n} failed').format(n=failed))
        if skipped:
            parts.append(_('{n} skipped').format(n=skipped))
        self.srvdlg.show_toast(_('OCR finished: {summary}').format(summary=', '.join(parts)))

    # Settings
    def build_settings(self):
        """Return the OCR settings as a group, for the Repository Settings tab."""
        langs = self._available_languages()
        default = self._default_language(langs)

        group = Adw.PreferencesGroup(title=_('OCR'))
        string_list = Gtk.StringList()
        for lang in langs:
            string_list.append(lang)
        combo = Adw.ComboRow(title=_('Document language'))
        combo.set_subtitle(_('Default language used by the OCR engine'))
        combo.set_model(string_list)
        combo.set_selected(langs.index(default))

        def _on_changed(row, gparam):
            idx = row.get_selected()
            if 0 <= idx < len(langs):
                self.plugin.set_config_key('lang', langs[idx])
                self.log.debug(f"OCR default language set to: {langs[idx]}")

        combo.connect('notify::selected', _on_changed)
        group.add(combo)
        return group
