# pylint: disable=E1101

"""
# File: ocr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: OCR plugin. Extract text from PDF documents and store it as a
#              note.

Two entry points over one implementation. The menu entry asks for a language
in a dialog and reports with toasts; `miaz ocr` takes the language as a flag
and reports on stdout. Both call MiAZ/backend/ocr.py, which has no frontend
in it.

Nothing GTK is imported at module scope, and MiAZExtension comes from the
backend rather than from the desktop plugin system. That is what lets the
command line import this module on a server with no Gtk typelib: the class
below is never instantiated there, but the module still has to load.
"""

import os
from gettext import gettext as _

from MiAZ.backend import ocr as ocrcore
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.notes import NotesStore, notes_dir
from MiAZ.backend.plugins import MiAZExtension

plugin_info = {
        'Module':        'ocr',
        'Name':          'MiAZOCR',
        'Loader':        'python',
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
        'Operations':    [
            {
                'name': 'ocr',
                'help': _('Extract text from documents with OCR and save it as a note'),
                'run': 'run_ocr',
                'params': [
                    {'name': 'documents', 'positional': True, 'multiple': True,
                     'help': _('Document filenames, as they are in the repository')},
                    {'name': 'language', 'default': 'eng',
                     'help': _('Language the OCR engine should assume')},
                    {'name': 'force', 'flag': True,
                     'help': _('Ignore any existing text layer and OCR every page')},
                ],
            },
        ],
        }

# Written out as a literal on purpose. Packaging reads this list without
# importing the module (tests/test_packaging_tools.py AST-parses it, so that
# adding a tool here without adding it to debian/control and miaz.spec fails
# there rather than on a user's machine), and ast.literal_eval cannot follow
# `ocrcore.REQUIRED_TOOLS`. tests/test_ocr.py checks the two stay in step.
REQUIRED_TOOLS = ('ocrmypdf',)

# The note category OCR files its results under.
NOTE_CATEGORY = 'OCR'


def notes_store(app, log):
    """Where the extracted text goes.

    Notes are core as of 0.3, so this is one import. It used to mean finding
    the MiAZNotes plugin on disk, putting its directory on sys.path and
    importing a top level package called `lib`, and it worked only when that
    plugin happened to be installed.
    """
    repository = app.get_service('repo')
    return NotesStore(notes_dir(repository.docs), log)


def run_ocr(app, args, stdout, stderr):
    """`miaz ocr`. Reads each named document and writes its text as a note.

    Exit codes follow the rest of the command line: 0 when every document
    named produced a note, 1 when any did not, 3 when the environment cannot
    do the work at all. A batch never stops on one bad document, since the
    commonest reason for one to fail is a typo in its name and the rest are
    still worth doing.
    """
    log = MiAZLog('MiAZ.OCR')

    missing = ocrcore.missing_tools()
    if missing:
        stderr.write(_('OCR needs {tools}, which is not installed\n').format(
            tools=', '.join(missing)))
        return 3

    store = notes_store(app, log)
    repository = app.get_service('repo')
    created = 0
    failed = 0
    for document in args.documents:
        source = os.path.join(repository.docs, document)
        if not os.path.isfile(source):
            stderr.write(_('not in this repository: {doc}\n').format(doc=document))
            failed += 1
            continue

        text = ocrcore.extract_text(source, lang=args.language,
                                    force=args.force, logger=log)
        if not text.strip():
            stderr.write(_('no text could be read from {doc}\n').format(doc=document))
            failed += 1
            continue

        note_path = store.create(document, {'Category': NOTE_CATEGORY},
                                 ocrcore.note_body(text, args.language))
        # NotesStore.create logs a write failure and returns the path anyway,
        # so the file is what says whether the note exists.
        if not note_path or not os.path.exists(note_path):
            stderr.write(_('could not write the note for {doc}\n').format(doc=document))
            failed += 1
            continue

        stdout.write(f'{document}: {os.path.basename(note_path)}\n')
        created += 1

    if failed:
        stderr.write(_('{created} note(s) created, {failed} failed\n').format(
            created=created, failed=failed))
        return 1
    return 0


class MiAZOCRPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZOCRPlugin'
    plugin = None

    # Activation lifecycle
    def do_activate(self):
        """Plugin activation. Vetoes activation if the OCR tooling is missing."""
        from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin
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
        missing = ocrcore.missing_tools()
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
        from gi.repository import GLib
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
        return ocrcore.available_languages()

    def _default_language(self, langs):
        return ocrcore.default_language(langs, self.plugin.get_config_key('lang'))

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
        from gi.repository import Adw, Gtk
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
        from MiAZ.backend.tasks import run_in_background
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
            name='ocr-process',
            label=_('Reading text from documents'),
            queued=True)

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
        """OCR every document. Returns (created, failed, skipped) for _finish.

        No toast per document: a selection of forty produced forty of them,
        each one covering the last. _finish shows the counts once, and the log
        keeps the per-document detail, which is where anyone chasing one bad
        document is looking anyway.
        """
        created = 0
        failed = 0
        for item in items:
            try:
                text = self._extract_text(item, lang, force)
                if text and text.strip() and self._create_note(item.id, text, lang):
                    created += 1
                    self.log.info(f"OCR wrote a note for '{item.id}'")
                else:
                    failed += 1
                    self.log.warning(f"No text stored for '{item.id}'")
            except Exception as error:
                failed += 1
                self.log.error(f"OCR failed for '{item.id}': {error}")
        return created, failed, skipped

    def _extract_text(self, item, lang, force):
        """The same extraction `miaz ocr` runs."""
        source = os.path.join(self.repository.docs, item.id)
        return ocrcore.extract_text(source, lang=lang, force=force,
                                    logger=self.log)

    def _create_note(self, doc_id, text, lang):
        """File the text through the core notes service.

        The service exists whenever there is a window, so there is no longer a
        plugin to be missing. It also refreshes the notes views, which writing
        straight to the store would not.
        """
        notes = self.app.get_service('notes')
        if notes is None:
            self.log.error('No notes service; cannot create note')
            return False
        try:
            return notes.add_note(doc_id, ocrcore.note_body(text, lang),
                                  category=NOTE_CATEGORY) is not None
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
        from gi.repository import Adw, Gtk
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
