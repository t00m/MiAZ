# pylint: disable=E1101

"""
# File: export2dir.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to a given directory
"""

import os
import sys
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.frontend.desktop.widgets.pills import item_fields

plugin_info = {
        'Module':        'export2dir',
        'Name':          'MiAZExport2Dir',
        'Loader':        'Python3',
        'Description':   _('Export to directory'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.3.0',
        'Category':      'Documents',
        'Subcategory':   'Export',
        'MenuEntries':   [
            ('export', _('Export to directory')),
        ]
    }

# The checkboxes, in two rows. The letters are the pattern the export speaks;
# the order the folders nest in is layout.ORDER, not the order they are ticked.
DATE_KEYS = 'Ymd'
FIELD_KEYS = 'CGBPT'

# How many failed documents the closing dialog names before it stops. The rest
# are in the log; a dialog listing three hundred filenames is not read.
FAILURES_SHOWN = 5


class Export2Dir(MiAZExtension):
    """Export selected documents to a directory"""

    __gtype_name__ = 'MiAZExport2DirPlugin'
    plugin = None
    _copied = 0

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

        # Get services
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.srvprg = self.app.get_service('progress')

        # The export package sits beside this file, which is not on the path
        source_dir = os.path.dirname(os.path.abspath(__file__))
        if source_dir not in sys.path:
            sys.path.insert(0, source_dir)

        # Connect startup signals
        self.workspace = self.app.get_widget('workspace')
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
            self.plugin.install_menu_entries({'export': self.export})
            self.plugin.set_started(started=True)

    # Settings: the folder and the pattern survive between exports

    def get_settings(self) -> dict:
        """What the last export used. Defaults when there is nothing yet."""
        from export.layout import canonical

        settings = {}
        configfile = self.plugin.get_config_file()
        if os.path.exists(configfile):
            try:
                settings = self.util.json_load(configfile)
            except Exception as error:
                # A settings file that cannot be read is not a reason to
                # refuse the export: start from the defaults instead.
                self.log.warning(f"Could not read {configfile}: {error}")
                settings = {}
        # A file written before the checkboxes carries the pattern and a
        # separate switch saying whether it was in use. The switch wins, so an
        # export that was flat comes back flat, and canonical() throws away
        # whatever a hand-edited file put in the string.
        pattern = settings.get('pattern', '')
        if not settings.get('use_pattern', bool(pattern)):
            pattern = ''
        return {
            'target_dir': settings.get('target_dir', ''),
            'pattern': canonical(pattern),
            'readable': settings.get('readable', False),
        }

    def save_settings(self, settings: dict):
        try:
            self.util.json_save(self.plugin.get_config_file(), settings)
        except Exception as error:
            self.log.warning(f"Could not save the export settings: {error}")

    # The dialog

    def export(self, *args):
        self.items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return

        settings = self.get_settings()
        remembered = settings['target_dir']
        self.target_dir = remembered if os.path.isdir(remembered) else None

        # Options for the dialog
        frame = Gtk.Frame()
        listbox = Gtk.ListBox.new()

        ## Folder rows: one checkbox per field, nesting in a fixed order
        self.checks = {}
        ticked = settings['pattern']
        self.row_date = self._add_check_row(listbox, _('Folders by date'), DATE_KEYS, ticked)
        self.row_field = self._add_check_row(listbox, _('Folders by field'), FIELD_KEYS, ticked)

        ## Readable names row
        self.chkReadable = self.factory.create_button_check(title=_('Readable names'),
                                                            callback=self._on_layout_changed)
        self.chkReadable.set_active(settings['readable'])
        self.chkReadable.set_valign(Gtk.Align.CENTER)
        self.chkReadable.set_tooltip_text(_('Rename the exported copies using the descriptions,\nfor someone who does not know MiAZ filenames.'))
        self.app.add_widget('plugin-export2dir-chkreadable', self.chkReadable)
        self.row_readable = Adw.ActionRow(title=_('Use readable names'))
        self.row_readable.set_subtitle(_('The documents in the repository are not renamed'))
        self.row_readable.add_suffix(self.chkReadable)
        listbox.append(self.row_readable)

        ## Target directory
        button = Gtk.Button()
        button.set_valign(Gtk.Align.CENTER)
        button.set_label(_('Select folder'))
        button.connect('clicked', self._on_select_folder)
        self.row_target = Adw.ActionRow(title=_('Select target folder'))
        self.row_target.set_subtitle(self.target_dir or _('No target folder set yet'))
        self.row_target.add_suffix(button)
        listbox.append(self.row_target)

        ## Example row, last: every row above it feeds the path it shows
        self.row_example = Adw.ActionRow(title=_('Example'))
        self.row_example.set_subtitle_lines(2)
        # A subtitle is Pango markup by default, and a path is not: a concept
        # holding an ampersand would be dropped, or worse, break the label.
        self.row_example.set_use_markup(False)
        listbox.append(self.row_example)

        frame.set_child(listbox)
        self._on_layout_changed()

        # Dialog
        parent = self.app.get_widget('window')
        title = _('Export to directory')
        dialog = self.srvdlg.show_action(title=title, callback=self._on_dialog_response, widget=frame, width=800)
        dialog.present(parent)

    def _add_check_row(self, listbox, title, keys, ticked):
        """One row of checkboxes, one per pattern letter in keys."""
        from export.layout import PATTERNS

        box = self.factory.create_box_horizontal(spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        for key in keys:
            check = Gtk.CheckButton(label=PATTERNS[key])
            check.set_active(key in ticked)
            check.connect('toggled', self._on_layout_changed)
            self.app.add_widget(f'plugin-export2dir-check-{key}', check)
            self.checks[key] = check
            box.append(check)
        row = Adw.ActionRow(title=title)
        row.add_suffix(box)
        listbox.append(row)
        return row

    def get_pattern(self) -> str:
        """The ticked letters, in the order the folders nest."""
        from export.layout import canonical

        return canonical(key for key, check in self.checks.items() if check.get_active())

    def _on_layout_changed(self, *args):
        """Redraw the example line. Every widget in the dialog feeds it."""
        from export.runner import relative_target

        pattern = self.get_pattern()
        folder = self.target_dir or _('the target folder')
        document = self._describe(self.items[:1])
        if not document:
            self.row_example.set_subtitle('')
            return
        doc_id, fields, labels, extension = document[0]
        try:
            relative = relative_target(fields, labels, extension, doc_id,
                                       pattern=pattern,
                                       readable=self.chkReadable.get_active())
        except (ValueError, IndexError):
            # The first selected document is not in MiAZ format. The export
            # will say so; the example has nothing to show.
            self.row_example.set_subtitle(_('This document cannot be exported with folders'))
            return
        self.row_example.set_subtitle(os.path.join(folder, relative))

    def _on_select_folder(self, *args):
        self.factory.create_filechooser_for_directories(self._on_select_folder_response,
                                                        dirpath=self.target_dir or '')

    def _on_select_folder_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self.target_dir = folder.get_path()
            self.row_target.set_subtitle(self.target_dir)
            self._on_layout_changed()
        except Exception as error:
            self.srvdlg.show_error(title=_('Error selecting files'), body=str(error))
            self.log.error(f"Error selecting files: {error}")

    # The export itself

    def _on_dialog_response(self, dialog, response, data):
        if response != 'apply':
            self.srvdlg.show_error(title=_('Action canceled'), body=_('No documents exported'))
            return

        # The folder is checked before it is used: os.path.exists(None) raises
        # and the dialog used to do exactly that when nothing had been picked.
        if self.target_dir is None or not os.path.isdir(self.target_dir):
            self.srvdlg.show_error(title=_('No target folder'),
                                   body=_('Choose an existing folder before exporting'))
            return

        pattern = self.get_pattern()
        readable = self.chkReadable.get_active()

        # use_pattern is written for a settings file an older build might read.
        # Here the ticked boxes are the whole answer: none of them means one
        # flat folder, so there is nothing left to validate.
        self.save_settings({'target_dir': self.target_dir,
                            'pattern': pattern,
                            'use_pattern': bool(pattern),
                            'readable': readable})

        documents = self._describe(self.items)
        target_dir = self.target_dir
        self.srvprg.run(
            lambda report: self._copy_all(documents, target_dir, pattern,
                                          readable, report),
            title=_('Export to directory'),
            message=_('Exporting {total} documents…').format(total=len(documents)),
            parent=self.app.get_widget('window'),
            on_close=lambda ok, result: self._on_export_closed(ok, target_dir))

    def _describe(self, items) -> list:
        """The plain data of each document, read while still on the main loop.

        The worker thread gets tuples, never the workspace items: a model row
        belongs to the widget that owns it.
        """
        documents = []
        for item in items:
            fields = self.util.get_fields(item.id)
            _name, extension = self.util.filename_details(item.id)
            try:
                labels = item_fields(item)[1]
            except AttributeError:
                # A view that does not carry the descriptions: the keys do.
                labels = None
            documents.append((item.id, fields, labels, extension))
        return documents

    def _copy_all(self, documents, target_dir, pattern, readable, report) -> str:
        """Copy every document. Runs in a worker thread: no GTK in here."""
        from export.runner import export_documents

        copied, failures = export_documents(documents, target_dir,
                                            self.repository.docs,
                                            self.util.filename_export,
                                            pattern=pattern,
                                            readable=readable,
                                            report=report)
        for doc_id, reason in failures:
            self.log.error(f"{doc_id} was not exported: {reason}")
        self._copied = copied
        return self._summary(copied, failures)

    def _summary(self, copied: int, failures: list) -> str:
        """What the progress dialog says when the copy is over."""
        lines = [_('{copied} of {total} documents exported').format(
            copied=copied, total=copied + len(failures))]
        if failures:
            for doc_id, reason in failures[:FAILURES_SHOWN]:
                lines.append(f'{doc_id}: {reason}')
            rest = len(failures) - FAILURES_SHOWN
            if rest > 0:
                lines.append(_('and {rest} more, in the log').format(rest=rest))
        return '\n'.join(lines)

    def _on_export_closed(self, ok: bool, target_dir: str):
        # Nothing copied, nothing to look at: opening the file browser on an
        # empty folder reads as success when it was not.
        if ok and self._copied > 0:
            self.util.directory_open(target_dir)
