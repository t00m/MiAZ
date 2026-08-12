# pylint: disable=E1101

"""
# File: allview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Workspace-level "All notes" page for MiAZNotes
"""

from gettext import gettext as _
from typing import Callable, List, Optional

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from lib.model import Note, PRIORITIES, STATUSES


ALL_STATUSES = _('All statuses')
ALL_PRIORITIES = _('All priorities')
ALL_CATEGORIES = _('All categories')


class NotesAllView(Gtk.Box):
    """Workspace page showing every note in the repository.

    Activating a row calls back into the plugin so it can open the
    per-document NotesListView with that note preselected.
    """

    def __init__(self, app, store, backup, log,
                 on_open_document: Callable[[str, Optional[str]], None],
                 existing_document_ids: Optional[set] = None,
                 compute_existing_document_ids: Optional[Callable[[], set]] = None,
                 compute_visible_document_ids: Optional[Callable[[], set]] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                         hexpand=True, vexpand=True, spacing=0)
        self.app = app
        self.store = store
        self.backup = backup
        self.log = log
        self._on_open_document = on_open_document
        self._existing_doc_ids = existing_document_ids or set()
        self._compute_existing_doc_ids = compute_existing_document_ids
        # Documents currently shown in the workspace view. None means "no
        # restriction" (show every note); a set restricts notes to those docs.
        self._compute_visible_doc_ids = compute_visible_document_ids
        self._visible_doc_ids: Optional[set] = None
        self._search_text = ''

        self._build_ui()
        self.refresh()

    # UI
    def _build_ui(self):
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(0)

        self.btn_refresh = Gtk.Button(icon_name='view-refresh-symbolic',
                                      tooltip_text=_('Refresh'))
        self.btn_refresh.connect('clicked', lambda _b: self.refresh())
        self.btn_refresh.set_valign(Gtk.Align.CENTER)
        toolbar.append(self.btn_refresh)

        # Backup / Restore behind an overflow menu instead of text buttons.
        actions = Gio.SimpleActionGroup()
        act_backup = Gio.SimpleAction.new('backup', None)
        act_backup.connect('activate', self._on_backup_clicked)
        actions.add_action(act_backup)
        act_restore = Gio.SimpleAction.new('restore', None)
        act_restore.connect('activate', self._on_restore_clicked)
        actions.add_action(act_restore)
        self.insert_action_group('allnotes', actions)

        menu = Gio.Menu()
        menu.append(_('Backup notes…'), 'allnotes.backup')
        menu.append(_('Restore notes…'), 'allnotes.restore')
        self.btn_menu = Gtk.MenuButton(icon_name='open-menu-symbolic',
                                       tooltip_text=_('Notes menu'))
        self.btn_menu.set_valign(Gtk.Align.CENTER)
        self.btn_menu.set_menu_model(menu)
        toolbar.append(self.btn_menu)

        self.lbl_orphans = Gtk.Label()
        self.lbl_orphans.set_margin_start(6)
        self.lbl_orphans.set_margin_end(6)
        self.lbl_orphans.set_hexpand(True)
        self.lbl_orphans.set_xalign(0.0)
        toolbar.append(self.lbl_orphans)

        self.append(toolbar)

        # Search entry + faceted filter dropdowns
        filter_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_row.set_margin_start(6)
        filter_row.set_margin_end(6)
        filter_row.set_margin_top(6)
        filter_row.set_margin_bottom(6)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_('Filter notes'))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect('search-changed', self._on_search_changed)
        filter_row.append(self.search_entry)

        self._category_values: List[str] = []
        self.dd_status = Gtk.DropDown.new_from_strings(
            [ALL_STATUSES, *STATUSES])
        self.dd_status.set_tooltip_text(_('Filter by status'))
        self.dd_status.set_selected(0)
        self.dd_status.connect('notify::selected', self._on_facet_changed)
        filter_row.append(self.dd_status)

        self.dd_priority = Gtk.DropDown.new_from_strings(
            [ALL_PRIORITIES, *PRIORITIES])
        self.dd_priority.set_tooltip_text(_('Filter by priority'))
        self.dd_priority.connect('notify::selected', self._on_facet_changed)
        filter_row.append(self.dd_priority)

        self.dd_category = Gtk.DropDown.new_from_strings([ALL_CATEGORIES])
        self.dd_category.set_tooltip_text(_('Filter by category'))
        self.dd_category.connect('notify::selected', self._on_facet_changed)
        filter_row.append(self.dd_category)

        self.append(filter_row)

        self.list_store = Gio.ListStore(item_type=Note)
        self.filter_model = Gtk.FilterListModel(model=self.list_store)
        self.item_filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model.set_filter(self.item_filter)
        self.selection = Gtk.SingleSelection.new(self.filter_model)

        self.column_view = Gtk.ColumnView(model=self.selection)
        self.column_view.set_show_row_separators(True)
        self.column_view.set_hexpand(True)
        self.column_view.set_vexpand(True)
        self.column_view.connect('activate', self._on_row_activated)

        self._add_column(_('Document'), 'document_id', expand=True)
        self._add_column(_('Date'), 'date', expand=False)
        self._add_column(_('Status'), 'status', expand=False)
        self._add_column(_('Priority'), 'priority', expand=False)
        self._add_column(_('Category'), 'category', expand=False)
        self._add_column(_('Summary'), 'summary', expand=True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_child(self.column_view)

        self.status_empty = Adw.StatusPage(
            icon_name='io.github.t00m.MiAZ-view-pin-symbolic',
            title=_('No notes'),
            description=_('Notes you attach to documents will appear here.'))

        self.list_stack = Gtk.Stack()
        self.list_stack.set_hexpand(True)
        self.list_stack.set_vexpand(True)
        self.list_stack.add_named(scroll, 'list')
        self.list_stack.add_named(self.status_empty, 'empty')
        self.append(self.list_stack)

    def _add_column(self, title: str, prop: str, expand: bool = False):
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind, prop)
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        column.set_resizable(True)
        column.set_expand(expand)
        self.column_view.append_column(column)

    @staticmethod
    def _on_factory_setup(_factory, list_item):
        label = Gtk.Label(xalign=0.0)
        label.set_margin_start(6)
        label.set_margin_end(6)
        list_item.set_child(label)

    def _on_factory_bind(self, _factory, list_item, prop: str):
        note = list_item.get_item()
        label = list_item.get_child()
        if note is None:
            label.set_label('')
            return
        value = note.get_property(prop) or ''
        if prop == 'document_id':
            doc_id = note.get_property('document_id')
            if doc_id and doc_id not in self._existing_doc_ids:
                value = f"{value}  ⚠"
                label.set_tooltip_text(_('Document is missing in the repository'))
            else:
                label.set_tooltip_text(None)
        label.set_label(value)

    # Data
    def _recompute_visible(self):
        if self._compute_visible_doc_ids is None:
            self._visible_doc_ids = None
            return
        try:
            self._visible_doc_ids = self._compute_visible_doc_ids()
        except Exception as error:
            self.log.warning(f"Could not compute visible document ids: {error}")
            self._visible_doc_ids = None

    def update_visible_documents(self):
        """Re-run the filter against the documents currently shown in the
        workspace, without reloading notes from disk."""
        self._recompute_visible()
        self.item_filter.changed(Gtk.FilterChange.DIFFERENT)

    def set_compute_visible_document_ids(self, fn: Optional[Callable[[], set]]):
        self._compute_visible_doc_ids = fn

    def refresh(self):
        self._recompute_visible()
        if self._compute_existing_doc_ids is not None:
            try:
                self._existing_doc_ids = self._compute_existing_doc_ids() or set()
            except Exception as error:
                self.log.warning(f"Could not recompute existing document ids: {error}")
        if self.store is None:
            self.list_store.remove_all()
            self.lbl_orphans.set_text(_('All Notes'))
            self.lbl_orphans.set_visible(False)
            self._rebuild_category_dropdown(set())
            self.list_stack.set_visible_child_name('empty')
            self.item_filter.changed(Gtk.FilterChange.DIFFERENT)
            return
        self.list_store.remove_all()
        orphan_count = 0
        seen_categories = set()
        for note_path in self.store.list_all():
            note = self._note_from_path(note_path)
            if note is None:
                continue
            self.list_store.append(note)
            if note.get_property('document_id') not in self._existing_doc_ids:
                orphan_count += 1
            cat = (note.get_property('category') or '').strip()
            if cat:
                seen_categories.add(cat)
        if orphan_count > 0:
            self.lbl_orphans.set_markup(
                _('<b>{n}</b> orphan note(s)').format(n=orphan_count))
            self.lbl_orphans.set_visible(True)
        else:
            self.lbl_orphans.set_text(_('All Notes'))
            self.lbl_orphans.set_visible(False)
        self._rebuild_category_dropdown(seen_categories)
        self.list_stack.set_visible_child_name(
            'list' if self.list_store.get_n_items() > 0 else 'empty')
        self.item_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _rebuild_category_dropdown(self, categories: set):
        previous = ''
        idx = self.dd_category.get_selected()
        if 0 < idx < len(self._category_values) + 1:
            previous = self._category_values[idx - 1]
        self._category_values = sorted(categories)
        model = Gtk.StringList.new([ALL_CATEGORIES, *self._category_values])
        self.dd_category.set_model(model)
        if previous and previous in self._category_values:
            self.dd_category.set_selected(
                self._category_values.index(previous) + 1)
        else:
            self.dd_category.set_selected(0)

    def set_existing_document_ids(self, doc_ids: set):
        self._existing_doc_ids = doc_ids or set()

    def set_compute_existing_document_ids(self, fn: Optional[Callable[[], set]]):
        self._compute_existing_doc_ids = fn

    def _note_from_path(self, note_path: str) -> Optional[Note]:
        try:
            header, body = self.store.read(note_path)
        except Exception as error:
            self.log.warning(f"Failed to load '{note_path}': {error}")
            return None
        return Note(
            path=note_path,
            document_id=self.store.document_id_of(note_path),
            author=header.get('Author', ''),
            category=header.get('Category', ''),
            date=header.get('Date', ''),
            priority=header.get('Priority', ''),
            status=header.get('Status', ''),
            summary=self.store.summary_of(body),
        )

    # Filtering / actions
    def _filter_func(self, item) -> bool:
        if not isinstance(item, Note):
            return True
        if self._visible_doc_ids is not None:
            if (item.get_property('document_id') or '') not in self._visible_doc_ids:
                return False
        if not self._match_facet(self.dd_status, list(STATUSES),
                                 item.get_property('status') or ''):
            return False
        if not self._match_facet(self.dd_priority, list(PRIORITIES),
                                 item.get_property('priority') or ''):
            return False
        if not self._match_facet(self.dd_category, self._category_values,
                                 item.get_property('category') or ''):
            return False
        if not self._search_text:
            return True
        text = self._search_text.lower()
        for prop in ('document_id', 'date', 'status', 'priority',
                     'category', 'summary', 'author'):
            value = item.get_property(prop) or ''
            if text in value.lower():
                return True
        return False

    @staticmethod
    def _match_facet(dropdown: Gtk.DropDown, values: List[str],
                     item_value: str) -> bool:
        idx = dropdown.get_selected()
        if idx <= 0:
            return True
        if idx - 1 >= len(values):
            return True
        return values[idx - 1] == item_value

    def _on_facet_changed(self, *_args):
        self.item_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _on_search_changed(self, entry):
        self._search_text = entry.get_text().strip()
        self.item_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _on_row_activated(self, _view, position: int):
        note = self.selection.get_selected_item()
        if note is None:
            return
        doc_id = note.get_property('document_id')
        note_path = note.get_property('path')
        if self._on_open_document is None:
            return
        GLib.idle_add(self._on_open_document, doc_id, note_path)

    # Backup / Restore
    def _on_backup_clicked(self, *_args):
        if self.backup is None:
            return
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Backup notes'))
        dialog.set_initial_name(self.backup.default_backup_name())
        dialog.save(self.app.get_widget('window'), None,
                    self._on_backup_chosen)

    def _on_backup_chosen(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except Exception as error:
            self.log.debug(f"Backup cancelled: {error}")
            return
        if gfile is None:
            return
        path = gfile.get_path()
        count = self.backup.backup(path)
        self._show_toast(_('Backed up {count} notes').format(count=count))

    def _on_restore_clicked(self, *_args):
        if self.backup is None:
            return
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Restore notes from backup'))
        zip_filter = Gtk.FileFilter()
        zip_filter.set_name(_('Zip archives'))
        zip_filter.add_pattern('*.zip')
        dialog.set_default_filter(zip_filter)
        dialog.open(self.app.get_widget('window'), None,
                    self._on_restore_chosen)

    def _on_restore_chosen(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except Exception as error:
            self.log.debug(f"Restore cancelled: {error}")
            return
        if gfile is None:
            return
        self._ask_restore_mode(gfile.get_path())

    def _ask_restore_mode(self, zip_path: str):
        dialog = Adw.AlertDialog.new(
            _('Restore mode'),
            _('Merge keeps existing notes and overwrites collisions.\n'
              'Replace moves existing notes aside before extracting.'),
        )
        dialog.add_response('cancel', _('Cancel'))
        dialog.add_response('replace', _('Replace'))
        dialog.add_response('merge', _('Merge'))
        dialog.set_response_appearance('merge', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_response_appearance('replace', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response('merge')
        dialog.set_close_response('cancel')

        def _on_response(_dialog, response):
            if response == 'cancel':
                return
            merge = response == 'merge'
            count = self.backup.restore(zip_path, merge=merge)
            self._show_toast(_('Restored {count} notes').format(count=count))
            self.refresh()

        dialog.connect('response', _on_response)
        dialog.present(self.app.get_widget('window'))

    def _show_toast(self, message: str):
        try:
            self.app.get_service('dialogs').show_toast(message)
        except Exception as error:
            self.log.debug(f"Toast unavailable: {error}")
