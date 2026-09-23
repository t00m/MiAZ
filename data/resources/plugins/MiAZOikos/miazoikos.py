# pylint: disable=E1101

"""
# File: miazoikos.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Record documents as income or expense and chart their totals
"""

import os
import sys
from gettext import gettext as _
from gettext import ngettext

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':        'miazoikos',
    'Name':          'MiAZOikos',
    'Loader':        'python',
    'Description':   _('Record documents as income or expense and chart their totals'),
    'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2026 Tomás Vírseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
    'Category':      'Documents',
    'Subcategory':   'Annotation',
    'MenuEntries':   [
        ('set', _('Set income or expense…')),
        ('clear', _('Clear income or expense')),
        ('show', _('Show income and expenses')),
        ('currencies', _('Manage currencies')),
    ]
}

# The view this plugin adds beside Details, Grid and Timeline.
VIEW_NAME = 'oikos'
VIEW_ICON = 'accessories-calculator-symbolic'

# The vocabulary page in Repository Settings > Metadata.
METADATA_VIEW = 'Currency'


class MiAZOikos(MiAZExtension):
    """Each document can be money in or money out.

    The user says which, how much and in what currency, for one document
    (a tab in the rename dialog) or many at once (the Set dialog). A view
    beside Details, Grid and Timeline adds up whatever is selected there,
    per currency, as tiles and a bar chart. Currencies are never converted:
    each has its own totals and its own scale.

    The amounts live in this plugin's data file in the repository, keyed by
    document name, and follow a document when it is renamed or deleted.
    """
    __gtype_name__ = 'MiAZOikosPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.config = None
        self.ledger = None
        self._view = None
        self._handlers = []

        source_dir = os.path.dirname(os.path.abspath(__file__))
        if source_dir not in sys.path:
            sys.path.insert(0, source_dir)

        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded',
                                                           self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        for handler_id in self._handlers:
            try:
                self.util.disconnect(handler_id)
            except (TypeError, ValueError):
                pass
        self._handlers = []
        # The plugin system takes the view off the toolbar; what the view
        # connected to outside itself is let go of here.
        if self._view is not None:
            self._view.dispose_view()
            self._view = None
        self.plugin.unregister_document_tabs()
        self.plugin.set_started(False)

    def startup(self, *args):
        if self.plugin.started():
            return
        from oikos.ledger import Ledger
        from oikos.money import CURRENCIES
        from oikos.vocabulary import MiAZConfigCurrency

        # Factory data first: the config copies it into the available pool.
        self.util.json_save(self.plugin.get_config_file_default_available_data(),
                            CURRENCIES)
        self.config = MiAZConfigCurrency(self.app, self.plugin)
        self.config.ensure_used(self.default_currency())
        self.ledger = Ledger(self.plugin.get_data_file(),
                             load=self.util.json_load, save=self.util.json_save)

        self._handlers = [
            self.util.connect('filename-renamed', self._on_filename_renamed),
            self.util.connect('filename-deleted', self._on_filename_deleted),
        ]

        self.plugin.install_menu_entries({
            'set': self.edit_selection,
            'clear': self.clear_selection,
            'show': self.show_view,
            'currencies': self.show_currencies,
        })
        self.plugin.install_metadata_view(METADATA_VIEW, _('Currencies'),
                                          self.plugin.get_icon_name(),
                                          self._build_metadata_view)
        self.plugin.install_settings_group(self.build_settings)
        self.plugin.register_document_tab(
            name='oikos', title=_('Income or expense'),
            factory=self._build_tab, weight=300)
        self._add_view()
        self.plugin.set_started(started=True)

    # What other parts of the plugin call

    def default_currency(self):
        from oikos.money import DEFAULT_CURRENCY, is_currency_code
        code = self.plugin.get_config_key('default_currency')
        return code if is_currency_code(code) else DEFAULT_CURRENCY

    def set_entries(self, entries):
        """Record {doc: Entry}; returns how many documents changed."""
        changed = self.ledger.set_many(entries)
        if changed:
            self._refresh_view()
        return changed

    def clear_documents(self, docs):
        """Forget what these documents are worth; returns how many had it."""
        removed = self.ledger.clear(docs)
        if removed:
            self._refresh_view()
        return removed

    def edit_selection(self, *args):
        self.edit_documents([item.id for item in self.workspace.get_selected_items()])

    def edit_documents(self, docs):
        """Open the Set dialog for these documents."""
        from oikos.editor import MiAZOikosEditor
        parent = self.workspace.get_root()
        if not docs:
            self.srvdlg.show_error(title=_('Action ignored'),
                                   body=_('You must select at least one document'),
                                   parent=parent)
            return None
        editor = MiAZOikosEditor(self.app, self, docs)
        title = ngettext('Income or expense of {count} document',
                         'Income or expense of {count} documents',
                         len(docs)).format(count=len(docs))
        dialog = self.srvdlg.show_action(title=title, widget=editor, width=520)
        dialog.set_response_enabled('apply', editor.is_valid())
        editor.connect('changed', lambda *args: dialog.set_response_enabled(
            'apply', editor.is_valid()))
        dialog.connect('response', self._on_edit_response, editor)
        dialog.present(parent)
        return dialog

    def _on_edit_response(self, _dialog, response, editor):
        if response != 'apply':
            return
        entries = editor.entries()
        if not entries:
            return
        changed = self.set_entries(entries)
        self.srvdlg.show_toast(ngettext('Income or expense saved for {count} document',
                                        'Income or expense saved for {count} documents',
                                        changed).format(count=changed))

    def clear_selection(self, *args):
        parent = self.workspace.get_root()
        docs = [item.id for item in self.workspace.get_selected_items()
                if item.id in self.ledger]
        if not docs:
            self.srvdlg.show_error(
                title=_('Action ignored'),
                body=_('None of the selected documents has an income or expense'),
                parent=parent)
            return
        body = ngettext('The amount recorded for {count} document will be forgotten.',
                        'The amounts recorded for {count} documents will be forgotten.',
                        len(docs)).format(count=len(docs))
        dialog = self.srvdlg.show_confirmation(
            title=_('Clear income or expense?'), body=body,
            confirm_label=_('Clear'), callback=self._on_clear_response, data=docs)
        dialog.present(parent)

    def _on_clear_response(self, _dialog, response, docs):
        if response != 'apply':
            return
        removed = self.clear_documents(docs)
        self.srvdlg.show_toast(ngettext('Cleared {count} document',
                                        'Cleared {count} documents',
                                        removed).format(count=removed))

    def show_view(self, *args):
        self.workspace.show_stack_page('workspace-default')
        self.workspace.show_view(VIEW_NAME)

    def show_currencies(self, *args):
        """Open Repository Settings on the currencies."""
        self.app.get_service('actions').show_repository_settings()
        page = self.app.get_widget('repository-settings-page-metadata')
        if page is not None:
            page.show_view(METADATA_VIEW)

    # Contributions

    def _add_view(self):
        from oikos.view import MiAZOikosView
        self._view = MiAZOikosView(self.app, self)
        self.plugin.add_workspace_view(self._view, VIEW_NAME, VIEW_ICON,
                                       _('Income and expenses'))

    def get_view(self):
        return self._view

    def _refresh_view(self):
        if self._view is not None and self._view.is_showing():
            self._view.refresh()

    def _build_tab(self, app):
        from oikos.editor import MiAZOikosTab
        return MiAZOikosTab(app, self)

    def _build_metadata_view(self):
        from oikos.vocabulary import MiAZCurrencyView
        view = MiAZCurrencyView(self.app, config=self.config)
        view.update_views()
        return view

    def build_settings(self):
        """The currency new entries start with."""
        from oikos.vocabulary import currency_label
        group = Adw.PreferencesGroup(
            title=_('Income and expenses'),
            description=_('Enable more currencies in Metadata > Currencies'))
        used = self.config.load_used()
        codes = sorted(used)
        row = Adw.ComboRow(title=_('Default currency'),
                           subtitle=_('Chosen for documents that have none yet'))
        row.set_model(Gtk.StringList.new([currency_label(code, used) for code in codes]))
        current = self.default_currency()
        if current in codes:
            row.set_selected(codes.index(current))
        row.connect('notify::selected', self._on_default_currency, codes)
        group.add(row)
        return group

    def _on_default_currency(self, row, _pspec, codes):
        index = row.get_selected()
        if 0 <= index < len(codes):
            self.plugin.set_config_key('default_currency', codes[index])

    # Following the documents

    def _on_filename_renamed(self, _util, source, target):
        if self.ledger.rename(os.path.basename(source), os.path.basename(target)):
            self._refresh_view()

    def _on_filename_deleted(self, _util, targets):
        self.clear_documents([os.path.basename(path) for path in targets])
