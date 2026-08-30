# pylint: disable=E1101

"""
# File: listview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Per-document notes window for MiAZNotes
"""

import os
from gettext import gettext as _
from typing import Callable, List, Optional

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk

from lib.editor import NoteEditor
from lib.model import Note


class NotesListView(Adw.Window):
    """Window showing all notes for a single document."""

    def __init__(self, app, store, backup, document_id: str, log,
                 select_note: Optional[str] = None,
                 category_store=None,
                 on_changed: Optional[Callable[[], None]] = None,
                 start_new: bool = False,
                 document_ids: Optional[List[str]] = None):
        super().__init__()
        self.app = app
        self.store = store
        self.backup = backup
        self.category_store = category_store
        self.document_id = document_id
        # Every document a new note is filed against. It is the one document
        # for the usual case; the workspace passes the whole selection when
        # the user asks for a note on several documents at once. The list
        # below still shows the notes of document_id: a note belongs to one
        # document, and the same text saved for five of them is five notes.
        self.document_ids = list(document_ids) if document_ids else [document_id]
        self.log = log
        self._on_changed = on_changed
        self._draft_path = None
        self._original_header = None
        self._original_body = None

        if len(self.document_ids) > 1:
            self.set_title(_('Notes - {n} documents').format(
                n=len(self.document_ids)))
        else:
            self.set_title(_('Notes - {document}').format(document=document_id))
        self.set_default_size(1000, 640)
        parent = self.app.get_widget('window')
        if parent is not None:
            self.set_transient_for(parent)
            self.set_modal(False)

        self._build_ui()
        self.refresh()

        if select_note:
            self._select_note_by_path(select_note)

        if start_new:
            self._on_new_clicked(None)

    # UI construction
    def _build_ui(self):
        root = Adw.ToolbarView()
        self.set_content(root)

        header = Adw.HeaderBar()
        root.add_top_bar(header)

        # Primary action: a single icon button with the accent colour (HIG).
        self.btn_new = Gtk.Button(icon_name='list-add-symbolic',
                                  tooltip_text=_('Add note'))
        self.btn_new.add_css_class('suggested-action')
        self.btn_new.connect('clicked', self._on_new_clicked)
        header.pack_start(self.btn_new)

        # Secondary actions live behind a primary menu instead of crowding
        # the header bar with text buttons.
        actions = Gio.SimpleActionGroup()
        for name, handler in (('refresh', lambda *_a: self.refresh()),
                              ('backup', self._on_backup_clicked),
                              ('restore', self._on_restore_clicked)):
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', handler)
            actions.add_action(action)
        self.insert_action_group('notes', actions)

        menu = Gio.Menu()
        menu.append(_('Refresh'), 'notes.refresh')
        section = Gio.Menu()
        section.append(_('Backup notes…'), 'notes.backup')
        section.append(_('Restore notes…'), 'notes.restore')
        menu.append_section(None, section)

        self.btn_menu = Gtk.MenuButton(icon_name='open-menu-symbolic',
                                       tooltip_text=_('Main menu'))
        self.btn_menu.set_menu_model(menu)
        header.pack_end(self.btn_menu)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_hexpand(True)
        paned.set_vexpand(True)
        paned.set_wide_handle(True)
        root.set_content(paned)

        # Left: column view
        self.list_store = Gio.ListStore(item_type=Note)
        self.selection = Gtk.MultiSelection.new(self.list_store)
        self.selection.connect('selection-changed', self._on_selection_changed)

        self.column_view = Gtk.ColumnView(model=self.selection)
        self.column_view.set_show_row_separators(True)
        self.column_view.set_show_column_separators(False)
        self.column_view.set_hexpand(True)
        self.column_view.set_vexpand(True)

        self._add_column(_('Date'), 'date', expand=False)
        self._add_column(_('Category'), 'category', expand=False)
        self._add_column(_('Status'), 'status', expand=False)
        self._add_column(_('Priority'), 'priority', expand=False)
        self._add_column(_('Summary'), 'summary', expand=True)

        scroll_left = Gtk.ScrolledWindow()
        scroll_left.set_hexpand(True)
        scroll_left.set_vexpand(True)
        scroll_left.set_child(self.column_view)

        # Empty state shown when the document has no notes yet.
        self.status_empty = Adw.StatusPage(
            icon_name='io.github.t00m.MiAZ-view-pin-symbolic',
            title=_('No notes yet'),
            description=_('Create the first note for this document.'))
        btn_empty_new = Gtk.Button(label=_('Add note'))
        btn_empty_new.add_css_class('suggested-action')
        btn_empty_new.add_css_class('pill')
        btn_empty_new.set_halign(Gtk.Align.CENTER)
        btn_empty_new.connect('clicked', self._on_new_clicked)
        self.status_empty.set_child(btn_empty_new)

        self.left_stack = Gtk.Stack()
        self.left_stack.set_hexpand(True)
        self.left_stack.set_vexpand(True)
        self.left_stack.add_named(scroll_left, 'list')
        self.left_stack.add_named(self.status_empty, 'empty')
        paned.set_start_child(self.left_stack)
        paned.set_resize_start_child(True)

        # Right: editor
        self.editor = NoteEditor(category_store=self.category_store)
        self.editor.connect('save-requested', self._on_save_requested)
        self.editor.connect('discard-requested', self._on_discard_requested)
        self.editor.connect('delete-requested', self._on_delete_requested)
        paned.set_end_child(self.editor)
        paned.set_resize_end_child(True)
        paned.set_position(380)

        self.editor.set_sensitive(False)

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

    @staticmethod
    def _on_factory_bind(_factory, list_item, prop: str):
        note = list_item.get_item()
        label = list_item.get_child()
        value = note.get_property(prop) if note is not None else ''
        label.set_label(value or '')

    # Data
    def refresh(self):
        self.list_store.remove_all()
        for note_path in self.store.list_for_document(self.document_id):
            note = self._note_from_path(note_path)
            if note is not None:
                self.list_store.append(note)
        self.left_stack.set_visible_child_name(
            'list' if self.list_store.get_n_items() > 0 else 'empty')
        self._draft_path = None
        self.editor.clear()
        self.editor.set_sensitive(False)

    def _notify_changed(self):
        if self._on_changed is not None:
            try:
                self._on_changed()
            except Exception as error:
                self.log.debug(f"on_changed callback failed: {error}")

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

    def _selected_notes(self) -> List[Note]:
        result = []
        bitset = self.selection.get_selection()
        if bitset is None:
            return result
        n = bitset.get_size()
        for i in range(n):
            position = bitset.get_nth(i)
            note = self.list_store.get_item(position)
            if note is not None:
                result.append(note)
        return result

    def _select_note_by_path(self, note_path: str):
        for i in range(self.list_store.get_n_items()):
            note = self.list_store.get_item(i)
            if note is not None and note.get_property('path') == note_path:
                self.selection.select_item(i, True)
                return

    # Callbacks
    def _on_selection_changed(self, *_args):
        notes = self._selected_notes()
        if len(notes) == 0:
            self.editor.clear()
            self.editor.set_sensitive(False)
            return
        if len(notes) > 1:
            self.editor.clear()
            self.editor.set_sensitive(False)
            return
        note = notes[0]
        note_path = note.get_property('path')
        header, body = self.store.read(note_path)
        self._draft_path = note_path
        self._original_header = dict(header)
        self._original_body = body
        self.editor.load(header, body, editable=False)

    def _on_new_clicked(self, _button):
        # Clear the selection before loading the draft. Unselecting fires
        # _on_selection_changed, which empties the editor and turns it off, so
        # doing it last wiped the draft that had just been loaded: the button
        # had to be pressed a second time to get an editable note.
        self.selection.unselect_all()
        header = self.store.default_header()
        self._draft_path = None
        self._original_header = dict(header)
        self._original_body = ''
        self.editor.load(header, '', editable=True)
        self.editor.set_sensitive(True)

    def _on_save_requested(self, _editor):
        header = self.editor.header()
        body = self.editor.body()
        if self._draft_path is None:
            note_path = self.store.create(self.document_id, header, body)
            for document_id in self.document_ids[1:]:
                self.store.create(document_id, header, body)
            if len(self.document_ids) > 1:
                self._show_toast(_('Note created for {n} documents').format(
                    n=len(self.document_ids)))
            else:
                self._show_toast(_('Note created'))
        else:
            note_path = self._draft_path
            self.store.update(note_path, header, body)
            self._show_toast(_('Note saved'))
        self.refresh()
        self._select_note_by_path(note_path)
        self._notify_changed()

    def _on_discard_requested(self, _editor):
        if self._draft_path is None:
            self.editor.clear()
            self.editor.set_sensitive(False)
            self._draft_path = None
        else:
            header, body = self.store.read(self._draft_path)
            self.editor.load(header, body, editable=False)

    def _on_delete_requested(self, _editor):
        notes = self._selected_notes()
        if not notes and self._draft_path is None:
            return
        if not notes and self._draft_path is not None:
            self.editor.clear()
            self.editor.set_sensitive(False)
            self._draft_path = None
            return
        self._confirm_delete(notes)

    def _confirm_delete(self, notes: List[Note]):
        srvdlg = self.app.get_service('dialogs')
        count = len(notes)
        title = _('Delete {count} note(s)?').format(count=count)
        body = _('This action cannot be undone. Use Backup to keep a copy first.')

        def _on_response(dialog, response, data=None):
            dialog.close()
            if response != 'apply':
                return
            for note in notes:
                self.store.delete(note.get_property('path'))
            self._show_toast(_('Deleted {count} note(s)').format(count=count))
            self.refresh()
            self._notify_changed()

        dialog = srvdlg.show_action(title=title, body=body, callback=_on_response)
        dialog.set_default_response('apply')
        dialog.set_close_response('cancel')
        dialog.present(self)

    def _on_backup_clicked(self, *_args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Backup notes'))
        dialog.set_initial_name(self.backup.default_backup_name())
        dialog.save(self, None, self._on_backup_chosen)

    def _on_backup_chosen(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except Exception as error:
            self.log.debug(f"Backup cancelled: {error}")
            return
        if gfile is None:
            return
        self._run_backup(gfile.get_path())

    def _on_restore_clicked(self, *_args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Restore notes from backup'))
        zip_filter = Gtk.FileFilter()
        zip_filter.set_name(_('Zip archives'))
        zip_filter.add_pattern('*.zip')
        dialog.set_default_filter(zip_filter)
        dialog.open(self, None, self._on_restore_chosen)

    def _on_restore_chosen(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except Exception as error:
            self.log.debug(f"Restore cancelled: {error}")
            return
        if gfile is None:
            return
        path = gfile.get_path()
        self._ask_restore_mode(path)

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
            self._run_restore(zip_path, merge=response == 'merge')

        dialog.connect('response', _on_response)
        dialog.present(self)

    def _run_backup(self, path):
        """Zip the notes behind the shared progress dialog.

        The UI is held back while it runs and the outcome stays on screen until
        the user closes it: services/progress.py does both.
        """
        backup = self.backup

        def work(report):
            count = backup.backup(path, progress=report)
            return _('{count} notes backed up to {name}.').format(
                count=count, name=os.path.basename(path))

        self._run(work, _('Backing up notes'))

    def _run_restore(self, zip_path, merge):
        backup = self.backup

        def work(report):
            count = backup.restore(zip_path, merge=merge, progress=report)
            return _('{count} notes restored from {name}.').format(
                count=count, name=os.path.basename(zip_path))

        def done(_ok, _result):
            self.refresh()
            self._notify_changed()

        self._run(work, _('Restoring notes'), on_close=done)

    def _run(self, work, title, on_close=None):
        progress = self.app.get_service('progress')
        if not progress.run(work, title=title, parent=self, on_close=on_close):
            self._show_toast(_('Another operation is already running'))

    def _show_toast(self, message: str):
        srvdlg = self.app.get_service('dialogs')
        try:
            srvdlg.show_toast(message)
        except Exception as error:
            self.log.debug(f"Toast unavailable: {error}")
