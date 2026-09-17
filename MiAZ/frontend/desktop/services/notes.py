"""
# File: notes.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: notes attached to documents, wired into the window

Notes were MiAZNotes, a plugin, until 0.3. The store moved to
MiAZ/backend/notes.py and this is what used to be the plugin's activation:
the menu entries, the All Notes page, the header bar indicator, the sidebar
filter and the workspace column.

Being a service rather than a plugin removes the whole teardown half. A plugin
has to give back everything it added, because it can be switched off in the
middle of a session; core cannot, so the column, the page and the filter are
installed once and stay.
"""

import os
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject  # noqa: F401
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.notes import (CategoryStore, NotesBackup, NotesStore,
                                notes_dir)
from MiAZ.frontend.desktop.widgets.notesallview import NotesAllView
from MiAZ.frontend.desktop.widgets.noteslistview import NotesListView
from MiAZ.frontend.desktop.widgets.notespostit import NotesPostItBoard


NOTES_CSS = b"""
.miaz-postit {
  background-image: linear-gradient(160deg, #fff7bd 0%, #ffe97a 100%);
  color: #3a3208;
  border: none;
  border-radius: 3px;
  padding: 10px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.28);
  min-width: 165px;
  min-height: 118px;
}
.miaz-postit:hover {
  background-image: linear-gradient(160deg, #ffface 0%, #fff093 100%);
  box-shadow: 0 3px 9px rgba(0,0,0,0.34);
}
.miaz-postit-summary { font-weight: bold; }
.miaz-postit-meta { font-size: 0.84em; opacity: 0.7; }
.miaz-postit-pin { color: #c0392b; }
.miaz-postit-prio-high { border-top: 3px solid #e08600; }
.miaz-postit-prio-critical { border-top: 3px solid #c0392b; }
.miaz-note-count { font-size: 0.72em; font-weight: bold; }
"""

# Name of the workspace filter that restricts the view to documents with notes.
ONLY_NOTES_FILTER = 'MiAZNotes-only-with-notes'
ONLY_NOTES_ROW_ID = 'notes-onlynotes-row'


class MiAZNotes(GObject.GObject):
    """Notes, as the window sees them."""

    __gtype_name__ = 'MiAZNotes'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Notes')
        self._started = False

        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.srvdlg = self.app.get_service('dialogs')
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')

        data_dir = notes_dir(self.repository.docs) if self.repository.docs else ''
        self.store = NotesStore(data_dir, self.log)
        self.backup = NotesBackup(data_dir, self.log)
        self.categories = CategoryStore(data_dir, self.log)

        self._win_per_doc = None
        self._postit_board = None
        # The all-notes workspace page, built by startup() once the workspace
        # is there. It is named here because the service is registered before
        # the window: the first repository switch happens in between and reads
        # this attribute.
        self._all_notes = None
        self._indicator_count = None
        self._current_doc_id = None
        self._css_provider = None
        # "Only documents with notes" sidebar filter state.
        self._only_notes_switch = None
        self._only_notes_active = False
        self._docs_with_notes = set()
        # {document id: note count} for the notes column cell, and the column
        # added to the workspace view.
        self._note_counts = {}
        self._notes_column = None
        self._notes_factory = None
        self._install_css()

        self.workspace = None
        self._bind_workspace()

        self.util.connect('filename-renamed', self._on_renamed)
        self.util.connect('filename-deleted', self._on_deleted)
        self.util.connect('filename-added', self._on_added)
        self.repository.connect('repository-switched', self._on_repo_switched)

        watcher = self.app.get_service('watcher')
        if watcher is not None:
            watcher.connect('repository-updated', self._on_repo_updated)

    def _bind_workspace(self, *_args):
        """Attach to the workspace, whenever it turns up.

        A plugin never had to think about this: plugins load after the window
        is built, so the workspace was always there. A service registered
        during startup runs earlier than that, and reading the widget once in
        __init__ found None and left Notes with no column, no page, no filter
        and no indicator, silently.
        """
        if self.workspace is not None:
            return
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            # Fires once the window and its repository are up.
            self.app.connect('application-started', self._bind_workspace)
            return
        self.workspace = workspace
        if workspace.is_loaded():
            self.startup()
        else:
            workspace.connect('workspace-loaded', self.startup)

    def started(self):
        return self._started

    # The four actions Notes offers, in menu order. Backup and Restore sit
    # with the others because they act on the notes, and hanging them off
    # entries of their own put two submenus in the workspace menu holding one
    # item each.
    MENU_ENTRIES = (
        ('doc', _('Create a new note'), ['<Ctrl>N']),
        ('all', _('See all notes…'), None),
        ('backup', _('Backup notes'), None),
        ('restore', _('Restore notes'), None),
    )

    def menu(self):
        """The Notes submenu, for the main window to append.

        Built rather than installed, because the workspace selection menu is
        thrown away and rebuilt whenever plugins load or unload. The mass
        rename and clipboard items are re-appended the same way; Notes stopped
        being a plugin and has no plugins section to sit in.

        The actions themselves are registered once. Registering the same name
        twice is harmless (the second replaces the first) but the accelerator
        would be set again on every rebuild for no reason.
        """
        callbacks = {
            'doc': self._on_new_doc_note,
            'all': self._on_open_all_notes,
            'backup': self._on_menu_backup,
            'restore': self._on_menu_restore,
        }
        menu = Gio.Menu.new()
        for entry_id, label, shortcuts in self.MENU_ENTRIES:
            key = f'notes-{entry_id}'
            menuitem = self.app.get_widget(f'menuitem-{key}')
            if menuitem is None:
                menuitem = self.factory.create_menuitem(
                    key, label, callbacks[entry_id], None, shortcuts)
                self.app.add_widget(f'menuitem-{key}', menuitem)
            menu.append_item(menuitem)
        return menu

    # Startup (workspace ready)
    def startup(self, *_args):
        if self._started:
            return

        # The menu is built by menu() and appended by the main window. It is
        # not installed here: the workspace selection menu is rebuilt whenever
        # plugins load or unload, and the core items are re-appended each time.

        # All notes workspace page.
        self._all_notes = NotesAllView(
            self.app, self.store, self.backup, self.log,
            on_open_document=self._open_doc_window,
            existing_document_ids=self._existing_document_ids(),
            compute_existing_document_ids=self._existing_document_ids,
            compute_visible_document_ids=self._visible_document_ids,
        )
        self._all_notes.refresh()
        self.workspace.add_stack_page(
            self._all_notes, 'notes-all', _('Notes'),
            'accessories-text-editor-symbolic')

        # Headerbar pushpin indicator: visible only when the single selected
        # document actually has notes. Clicking it shows the post-it board.
        if self.app.get_widget('headerbar-button-notes-indicator') is None:
            button = self._build_indicator_button()
            button.set_visible(False)
            box = self.app.get_widget('headerbar-right-box')
            if box is not None:
                box.append(button)
                self.app.add_widget('headerbar-button-notes-indicator', button)

        # Sidebar toggle: "Only documents with notes". Registers a workspace
        # filter that is a no-op until the switch is turned on.
        if self.app.get_widget(ONLY_NOTES_ROW_ID) is None:
            row = self._build_only_notes_row()
            # The core filter section, above the separator that divides the
            # built-in filters from the ones plugins add. Notes is no longer
            # one of those.
            section = (self.app.get_widget('sidebar-core-section')
                       or self.app.get_widget('sidebar-plugin-section'))
            if section is not None:
                section.append(row)
                self.app.add_widget(ONLY_NOTES_ROW_ID, row)
                self.workspace.register_filter_view(
                    ONLY_NOTES_FILTER, self._do_filter_notes)

        # Track selection so the button appears only on a single selection
        view = self.app.get_widget('workspace-view')
        self._view_selection = None
        self._h_selection_changed = None
        if view is not None:
            selection = view.get_selection() if hasattr(view, 'get_selection') else None
            if selection is not None:
                self._view_selection = selection
                self._h_selection_changed = selection.connect(
                    'selection-changed', self._on_selection_changed)
        self._h_view_updated = self.workspace.connect(
            'workspace-view-updated', self._on_workspace_view_changed)
        self._h_view_filtered = self.workspace.connect(
            'workspace-view-filtered', self._on_workspace_view_changed)

        # Add a leftmost column showing a pin icon and note count for documents
        # that have notes. The counts are computed up front and kept current by
        # _refresh_notes_filter(); the column cell reads self._note_counts.
        self._docs_with_notes = self._compute_docs_with_notes()
        self._install_notes_column()
        # Re-bind so the column populates immediately. Not update(): that
        # lists the repository, rebuilds the index and parses every
        # filename, which is 367 ms on a 1322 document repository to
        # paint a column whose cell reads the dictionary above.
        self.workspace.refresh_rows()

        self._started = True
        self._on_workspace_view_changed()

    # Concept-cell highlight (documents with notes)
    def _install_notes_column(self):
        """Add a leftmost workspace column that shows a pin icon and note count
        for documents that have notes. The column belongs to this plugin and is
        removed again on do_deactivate."""
        wsview = self.app.get_widget('workspace-view')
        if wsview is None or self._notes_column is not None:
            return
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_notes_cell_setup)
        factory.connect('bind', self._on_notes_cell_bind)
        column = Gtk.ColumnViewColumn.new(_('Notes'), factory)
        column.set_resizable(False)
        wsview.cv.insert_column(0, column)
        self._notes_factory = factory
        self._notes_column = column

    def _on_notes_cell_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER)
        icon = Gtk.Image.new_from_icon_name('io.github.t00m.MiAZ-view-pin-symbolic')
        label = Gtk.Label()
        label.add_css_class('miaz-note-count')
        box.append(icon)
        box.append(label)
        list_item.set_child(box)

    def _on_notes_cell_bind(self, factory, list_item):
        box = list_item.get_child()
        item = list_item.get_item()
        if box is None or item is None:
            return
        icon = box.get_first_child()
        label = box.get_last_child()
        count = self._note_counts.get(getattr(item, 'id', None), 0)
        if count > 0:
            icon.set_visible(True)
            label.set_text(str(count))
            label.set_visible(True)
        else:
            # Reset recycled cells so empty rows show nothing.
            icon.set_visible(False)
            label.set_visible(False)
            label.set_text('')

    # Public API (for other plugins, e.g. MiAZOCR)
    def add_note(self, document_id, body, category='General',
                 priority=None, status=None):
        """Create a note linked to a document and refresh the UI.

        Safe to call from a worker thread: the file write runs inline (plain
        I/O) and the UI refresh is marshalled to the GTK main loop.
        Returns the created note path, or None on failure.
        """
        if not document_id:
            return None
        header = {'Category': category}
        if priority:
            header['Priority'] = priority
        if status:
            header['Status'] = status
        try:
            note_path = self.store.create(document_id, header, body or '')
        except Exception as error:
            self.log.error(f"Could not create note for '{document_id}': {error}")
            return None
        GLib.idle_add(self._notes_changed)
        return note_path

    # Helpers
    def _selected_items(self):
        if self.workspace is None:
            return []
        try:
            return self.workspace.get_selected_items() or []
        except Exception:
            return []

    def _existing_document_ids(self) -> set:
        repo_dir = None
        if self.repository is not None:
            try:
                repo_dir = self.repository.docs
            except Exception:
                repo_dir = None
        if not repo_dir or not os.path.isdir(repo_dir):
            return set()
        ids = set()
        for path in self.util.get_files(repo_dir):
            basename = os.path.basename(path)
            if basename:
                ids.add(basename)
        return ids

    def _visible_document_ids(self) -> set:
        """IDs of the documents currently displayed in the workspace view."""
        view = self.app.get_widget('workspace-view')
        if view is None or not hasattr(view, 'filter_model'):
            return set()
        ids = set()
        model = view.filter_model
        for i in range(model.get_n_items()):
            item = model.get_item(i)
            doc_id = getattr(item, 'id', None)
            if doc_id:
                ids.add(doc_id)
        return ids

    def _close_windows(self):
        for attr in ('_win_per_doc',):
            win = getattr(self, attr, None)
            if win is not None:
                try:
                    win.destroy()
                except Exception as error:
                    self.log.debug(f"Close {attr}: {error}")
                setattr(self, attr, None)

    def _build_indicator_button(self) -> Gtk.Button:
        icons = self.app.get_service('icons')
        button = Gtk.Button()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        pin = icons.get_image_by_name('io.github.t00m.MiAZ-view-pin-symbolic', size=16)
        pin.set_valign(Gtk.Align.CENTER)
        box.append(pin)
        self._indicator_count = Gtk.Label()
        self._indicator_count.add_css_class('miaz-note-count')
        self._indicator_count.set_valign(Gtk.Align.CENTER)
        box.append(self._indicator_count)
        button.set_child(box)
        button.connect('clicked', self._on_show_postits)
        return button

    def _build_only_notes_row(self) -> Gtk.Widget:
        icons = self.app.get_service('icons')
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_hexpand(True)
        row.set_tooltip_text(_('Show only documents that have notes'))

        pin = icons.get_image_by_name('io.github.t00m.MiAZ-view-pin-symbolic', size=16)
        pin.set_valign(Gtk.Align.CENTER)
        row.append(pin)

        label = Gtk.Label(label=_('Only with notes'), xalign=0.0)
        label.set_hexpand(True)
        label.set_valign(Gtk.Align.CENTER)
        row.append(label)

        self._only_notes_switch = Gtk.Switch()
        self._only_notes_switch.set_valign(Gtk.Align.CENTER)
        self._only_notes_switch.set_active(self._only_notes_active)
        self._only_notes_switch.connect('state-set', self._on_only_notes_toggled)
        row.append(self._only_notes_switch)
        return row

    def _on_only_notes_toggled(self, _switch, state):
        self._only_notes_active = bool(state)
        if self._only_notes_active:
            self._docs_with_notes = self._compute_docs_with_notes()
        if self.workspace is not None:
            # Turning a filter on and off decides which rows are shown. The
            # documents behind them have not changed, so there is nothing to
            # re-read.
            self.workspace.refresh_rows()
        return False  # let the switch update its visual state

    def _compute_docs_with_notes(self) -> set:
        """Documents with at least one note. Also refreshes self._note_counts,
        the {document id: note count} map the notes column cell reads."""
        counts = {}
        try:
            for note_path in self.store.list_all():
                doc_id = self.store.document_id_of(note_path)
                if doc_id:
                    counts[doc_id] = counts.get(doc_id, 0) + 1
        except Exception as error:
            self.log.debug(f"Could not compute documents with notes: {error}")
        self._note_counts = counts
        return set(counts)

    def _do_filter_notes(self, item, _filter_list_model) -> bool:
        if not self._only_notes_active:
            return True
        return getattr(item, 'id', None) in self._docs_with_notes

    def _on_show_postits(self, button, *_args):
        if not self._current_doc_id:
            return
        if self._postit_board is None:
            self._postit_board = NotesPostItBoard(
                self.app, self.store, self.log,
                on_open_document=self._open_doc_window)
            self._postit_board.set_parent(button)
        self._postit_board.store = self.store
        self._postit_board.set_document(self._current_doc_id)
        self._postit_board.refresh()
        self._postit_board.popup()

    def _install_css(self):
        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(NOTES_CSS)
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(
                    display, provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                self._css_provider = provider
        except Exception as error:
            self.log.debug(f"Could not install CSS: {error}")

    def _uninstall_css(self):
        if self._css_provider is None:
            return
        try:
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.remove_provider_for_display(
                    display, self._css_provider)
        except Exception as error:
            self.log.debug(f"Could not remove CSS: {error}")
        self._css_provider = None

    def _open_doc_window(self, document_id: str, select_note=None,
                         start_new: bool = False, document_ids=None):
        if not document_id:
            return
        if self._win_per_doc is not None:
            try:
                self._win_per_doc.destroy()
            except Exception as error:
                self.log.debug(f"Destroy previous per-doc window: {error}")
            self._win_per_doc = None
        win = NotesListView(self.app, self.store, self.backup,
                            document_id, self.log,
                            select_note=select_note,
                            category_store=self.categories,
                            on_changed=self._notes_changed,
                            start_new=start_new,
                            document_ids=document_ids)
        win.connect('close-request', self._on_per_doc_closed)
        self._win_per_doc = win
        win.present()

    def _on_per_doc_closed(self, *_args):
        self._win_per_doc = None
        # Notes may have been created or deleted while the window was open.
        self._notes_changed()
        return False

    # Callbacks
    def _on_selection_changed(self, *_args):
        self._update_indicator()

    def _update_indicator(self, *_args):
        """Show the pushpin only when a single selected document has notes."""
        button = self.app.get_widget('headerbar-button-notes-indicator')
        if button is None:
            return
        items = self._selected_items()
        doc_id = getattr(items[0], 'id', None) if len(items) == 1 else None
        count = self.store.count_for_document(doc_id) if doc_id else 0
        self._current_doc_id = doc_id if count > 0 else None
        if count > 0:
            if self._indicator_count is not None:
                self._indicator_count.set_text(str(count))
            button.set_tooltip_text(
                _('{n} note(s) for this document').format(n=count))
            button.set_visible(True)
            # If the board is open for this doc, keep it fresh.
            if self._postit_board is not None and self._postit_board.get_visible():
                self._postit_board.set_document(doc_id)
                self._postit_board.refresh()
        else:
            button.set_visible(False)
            if self._postit_board is not None and self._postit_board.get_visible():
                self._postit_board.popdown()

    def _notes_changed(self, *_args):
        """Recompute the indicator and refresh the all-notes page after a
        note was created, edited or removed."""
        self._update_indicator()
        self._refresh_notes_filter()
        if self._all_notes is not None:
            self._all_notes.refresh()

    def _refresh_notes_filter(self):
        """Recompute the documents-with-notes set and refresh the workspace so
        both the optional 'only with notes' filter and the row highlight track
        the current notes."""
        self._docs_with_notes = self._compute_docs_with_notes()
        if self.workspace is not None:
            # The filter predicate and the highlight both read the set
            # above, so re-binding the rows is the whole job.
            self.workspace.refresh_rows()

    def _on_workspace_view_changed(self, *_args):
        self._update_indicator()
        if self._all_notes is not None:
            self._all_notes.update_visible_documents()

    def _on_new_doc_note(self, *_args):
        """Open the notes window on a blank note for the selection.

        With more than one document selected the note is written once per
        document when it is saved: the same text filed against each of them.
        The action used to return silently unless exactly one document was
        selected, which looked like a dead menu entry.
        """
        if self.actions is not None and self.actions.stop_if_no_items():
            return
        document_ids = [doc_id for doc_id in
                        (getattr(item, 'id', None) for item in self._selected_items())
                        if doc_id]
        if not document_ids:
            return
        self._open_doc_window(document_ids[0], start_new=True,
                              document_ids=document_ids)

    def _on_open_all_notes(self, *_args):
        if self._all_notes is not None:
            self._all_notes.set_existing_document_ids(self._existing_document_ids())
            self._all_notes.refresh()
        self.workspace.show_stack_page('notes-all')

    def _on_menu_backup(self, *_args):
        dialog = self._file_dialog_save_zip()
        dialog.save(self.app.get_widget('window'), None, self._on_menu_backup_chosen)

    def _on_menu_backup_chosen(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except Exception as error:
            self.log.debug(f"Backup cancelled: {error}")
            return
        if gfile is None:
            return
        path = gfile.get_path()
        backup = self.backup

        def work(report):
            count = backup.backup(path, progress=report)
            return _('{count} notes backed up to {name}.').format(
                count=count, name=os.path.basename(path))

        self._run(work, _('Backing up notes'))

    def _on_menu_restore(self, *_args):
        dialog = self._file_dialog_open_zip()
        dialog.open(self.app.get_widget('window'), None, self._on_menu_restore_chosen)

    def _on_menu_restore_chosen(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except Exception as error:
            self.log.debug(f"Restore cancelled: {error}")
            return
        if gfile is None:
            return
        path = gfile.get_path()
        backup = self.backup

        def work(report):
            count = backup.restore(path, merge=True, progress=report)
            return _('{count} notes restored from {name}.').format(
                count=count, name=os.path.basename(path))

        def done(_ok, _result):
            if self._win_per_doc is not None:
                self._win_per_doc.refresh()
            if self._all_notes is not None:
                self._all_notes.refresh()

        self._run(work, _('Restoring notes'), on_close=done)

    def _on_renamed(self, _util, source, target):
        old_id = os.path.basename(source) if source else ''
        new_id = os.path.basename(target) if target else ''
        if not old_id or not new_id or old_id == new_id:
            return
        self.store.rename_for_document(old_id, new_id)
        if self._win_per_doc is not None:
            try:
                if self._win_per_doc.document_id == old_id:
                    self._win_per_doc.document_id = new_id
                    self._win_per_doc.set_title(
                        _('Notes - {document}').format(document=new_id))
                self._win_per_doc.refresh()
            except Exception as error:
                self.log.debug(f"Refresh per-doc after rename: {error}")
        if self._all_notes is not None:
            self._all_notes.refresh()
        self._refresh_notes_filter()

    def _on_deleted(self, _util, _filepaths):
        if self._all_notes is not None:
            self._all_notes.refresh()

    def _on_added(self, _util, _filepath):
        if self._all_notes is not None:
            self._all_notes.refresh()

    def _on_repo_updated(self, *_args):
        if self._all_notes is not None:
            self._all_notes.refresh()
        self._refresh_notes_filter()

    def _on_repo_switched(self, *_args):
        self._close_windows()
        try:
            data_dir = notes_dir(self.repository.docs)
        except Exception as error:
            self.log.error(f"Could not resolve data dir on repo switch: {error}")
            return
        self.store = NotesStore(data_dir, self.log)
        self.backup = NotesBackup(data_dir, self.log)
        self.categories = CategoryStore(data_dir, self.log)
        if self._all_notes is not None:
            self._all_notes.store = self.store
            self._all_notes.backup = self.backup
            self._all_notes.set_existing_document_ids(self._existing_document_ids())
            GLib.idle_add(self._all_notes.refresh)
        # Recompute the "only with notes" set against the new repository.
        GLib.idle_add(self._refresh_notes_filter)

    # File dialog helpers
    def _file_dialog_save_zip(self):
        from gi.repository import Gtk
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Backup notes'))
        dialog.set_initial_name(self.backup.default_backup_name())
        return dialog

    def _file_dialog_open_zip(self):
        from gi.repository import Gtk
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Restore notes from backup'))
        zip_filter = Gtk.FileFilter()
        zip_filter.set_name(_('Zip archives'))
        zip_filter.add_pattern('*.zip')
        dialog.set_default_filter(zip_filter)
        return dialog

    def _run(self, work, title, on_close=None):
        """Run a backup or a restore behind the shared progress dialog.

        The UI is held back while it runs and the outcome stays on screen until
        the user closes it: services/progress.py does both.
        """
        progress = self.app.get_service('progress')
        parent = self.app.get_widget('window')
        if not progress.run(work, title=title, parent=parent, on_close=on_close):
            self._toast(_('Another operation is already running'))

    def _toast(self, message: str):
        try:
            self.srvdlg.show_toast(message)
        except Exception as error:
            self.log.debug(f"Toast unavailable: {error}")
