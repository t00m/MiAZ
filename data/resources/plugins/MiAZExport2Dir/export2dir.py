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
        'Version':       '0.6',
        'Category':      'Documents',
        'Subcategory':   'Export'
    }

# What the dialog starts with the first time, before there is anything
# remembered: /{target}/{Country}/{Year}/{month}/{Group}/{Purpose}
DEFAULT_PATTERN = 'CYmGP'

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
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Export to directory'), callback=self.export)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    # Settings: the folder and the pattern survive between exports

    def get_settings(self) -> dict:
        """What the last export used. Defaults when there is nothing yet."""
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
        return {
            'target_dir': settings.get('target_dir', ''),
            'pattern': settings.get('pattern', DEFAULT_PATTERN),
            'use_pattern': settings.get('use_pattern', False),
            'readable': settings.get('readable', False),
        }

    def save_settings(self, settings: dict):
        try:
            self.util.json_save(self.plugin.get_config_file(), settings)
        except Exception as error:
            self.log.warning(f"Could not save the export settings: {error}")

    # The dialog

    def export(self, *args):
        from export.layout import PATTERNS

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

        ## Pattern row
        self.chkPattern = self.factory.create_button_check(title=_('Export with pattern'), callback=None)
        self.chkPattern.set_active(settings['use_pattern'])
        self.chkPattern.set_valign(Gtk.Align.CENTER)
        self.chkPattern.set_tooltip_text(_('Check this box to activate the pattern.\nOtherwise, all documents will be exported in the same folder.'))
        self.app.add_widget('plugin-export2dir-chkpattern', self.chkPattern)
        self.etyPattern = self.app.add_widget('plugin-export2dir-etypattern', Gtk.Entry())
        self.etyPattern.set_valign(Gtk.Align.CENTER)
        self.etyPattern.set_text(settings['pattern'])
        widgets = []
        label = Gtk.Label.new(_('Each letter represent a directory:\n'))
        widgets.append(label)
        for key in PATTERNS:
            label = Gtk.Label()
            label.set_markup(f'<b>{key}</b> = {PATTERNS[key]}')
            label.set_xalign(0.0)
            widgets.append(label)
        btpPattern = self.factory.create_button_popover(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', widgets=widgets)
        btpPattern.set_valign(Gtk.Align.CENTER)
        hbox = self.factory.create_box_horizontal()
        hbox.append(self.chkPattern)
        hbox.append(self.etyPattern)
        hbox.append(btpPattern)
        self.row_pattern = Adw.ActionRow(title=_('Select pattern'))
        self.row_pattern.add_suffix(hbox)
        listbox.append(self.row_pattern)

        ## Readable names row
        self.chkReadable = self.factory.create_button_check(title=_('Readable names'), callback=None)
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
        frame.set_child(listbox)

        # Dialog
        parent = self.app.get_widget('window')
        title = _('Export to directory')
        dialog = self.srvdlg.show_action(title=title, callback=self._on_dialog_response, widget=frame, width=800)
        dialog.present(parent)

    def _on_select_folder(self, *args):
        self.factory.create_filechooser_for_directories(self._on_select_folder_response,
                                                        dirpath=self.target_dir or '')

    def _on_select_folder_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self.target_dir = folder.get_path()
            self.row_target.set_subtitle(self.target_dir)
        except Exception as error:
            self.srvdlg.show_error(title=_('Error selecting files'), body=str(error))
            self.log.error(f"Error selecting files: {error}")

    # The export itself

    def _on_dialog_response(self, dialog, response, data):
        from export.layout import invalid_keys

        if response != 'apply':
            self.srvdlg.show_error(title=_('Action canceled'), body=_('No documents exported'))
            return

        # The folder is checked before it is used: os.path.exists(None) raises
        # and the dialog used to do exactly that when nothing had been picked.
        if self.target_dir is None or not os.path.isdir(self.target_dir):
            self.srvdlg.show_error(title=_('No target folder'),
                                   body=_('Choose an existing folder before exporting'))
            return

        use_pattern = self.chkPattern.get_active()
        pattern = self.etyPattern.get_text().strip()
        readable = self.chkReadable.get_active()

        if use_pattern:
            unknown = invalid_keys(pattern)
            if unknown:
                # An unknown letter used to raise halfway through the copy,
                # leaving a half-written tree behind.
                self.srvdlg.show_error(
                    title=_('Pattern not valid'),
                    body=_('These letters mean nothing here: {keys}').format(
                        keys=' '.join(unknown)))
                return
            if not pattern:
                use_pattern = False

        self.save_settings({'target_dir': self.target_dir,
                            'pattern': pattern or DEFAULT_PATTERN,
                            'use_pattern': use_pattern,
                            'readable': readable})

        documents = self._describe(self.items)
        target_dir = self.target_dir
        self.srvprg.run(
            lambda report: self._copy_all(documents, target_dir, pattern if use_pattern else '',
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
