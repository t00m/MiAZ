#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: editor.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: NoteEditor widget for MiAZNotes (libadwaita rows, HIG compliant)
"""

from gettext import gettext as _
from typing import List, Optional

from gi.repository import Adw
from gi.repository import GObject
from gi.repository import Gtk

from lib.model import CATEGORIES, PRIORITIES, STATUSES
from MiAZ.frontend.desktop.widgets.markdownview import MiAZMarkdownView


OTHER_LABEL = _('Other…')


class NoteEditor(Gtk.Box):
    """Form to view / edit a single note, built from libadwaita rows.

    Metadata (Author, Date, Category, Priority, Status) lives in an
    Adw.PreferencesGroup; the body is raw Markdown in a monospace TextView.
    Public API (load/clear/header/body/set_editable/is_editable and the
    save/discard/delete signals) is unchanged.
    """

    __gsignals__ = {
        'save-requested':    (GObject.SignalFlags.RUN_LAST, None, ()),
        'discard-requested': (GObject.SignalFlags.RUN_LAST, None, ()),
        'delete-requested':  (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, category_store=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self._editable = False
        self._builtin_categories = list(CATEGORIES)
        self._priorities = list(PRIORITIES)
        self._statuses = list(STATUSES)
        self._category_store = category_store
        self._category_items: List[str] = []
        self._build()
        self._reload_category_items()

    # Construction
    def _build(self):
        group = Adw.PreferencesGroup()

        # Details are collapsed by default so the Markdown viewer below gets
        # most of the vertical space. The user expands this row to edit them.
        self.details_expander = Adw.ExpanderRow(title=_('Details'))
        self.details_expander.set_expanded(False)
        group.add(self.details_expander)

        self.row_author = Adw.EntryRow(title=_('Author'))
        self.details_expander.add_row(self.row_author)

        self.row_date = Adw.ActionRow(title=_('Date'))
        self.row_date.add_css_class('property')
        self.details_expander.add_row(self.row_date)

        self.row_category = Adw.ComboRow(title=_('Category'))
        self.row_category.set_model(Gtk.StringList.new([]))
        self.row_category.connect('notify::selected', self._on_category_changed)
        self.btn_category_delete = Gtk.Button(icon_name='user-trash-symbolic',
                                              tooltip_text=_('Delete this custom category'))
        self.btn_category_delete.add_css_class('flat')
        self.btn_category_delete.set_valign(Gtk.Align.CENTER)
        self.btn_category_delete.connect('clicked', self._on_delete_category_clicked)
        self.btn_category_delete.set_sensitive(False)
        self.row_category.add_suffix(self.btn_category_delete)
        self.details_expander.add_row(self.row_category)

        self.row_category_other = Adw.EntryRow(title=_('New category name'))
        self.row_category_other.set_visible(False)
        self.details_expander.add_row(self.row_category_other)

        self.row_priority = Adw.ComboRow(title=_('Priority'))
        self.row_priority.set_model(Gtk.StringList.new(self._priorities))
        self.details_expander.add_row(self.row_priority)

        self.row_status = Adw.ComboRow(title=_('Status'))
        self.row_status.set_model(Gtk.StringList.new(self._statuses))
        self.details_expander.add_row(self.row_status)

        self.append(group)

        # Body
        body_label = Gtk.Label(label=_('Note (Markdown)'), xalign=0.0)
        body_label.add_css_class('heading')
        self.append(body_label)

        self.body_buffer = Gtk.TextBuffer()
        self.body_view = Gtk.TextView(buffer=self.body_buffer)
        self.body_view.set_monospace(True)
        self.body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.body_view.set_left_margin(8)
        self.body_view.set_right_margin(8)
        self.body_view.set_top_margin(8)
        self.body_view.set_bottom_margin(8)
        self.body_view.set_hexpand(True)
        self.body_view.set_vexpand(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_child(self.body_view)

        edit_frame = Gtk.Frame()
        edit_frame.add_css_class('card')
        edit_frame.set_child(scroll)
        edit_frame.set_vexpand(True)

        # View mode shows the rendered Markdown; edit mode shows the raw
        # Markdown in the TextView above. A stack swaps between the two.
        self.body_rendered = MiAZMarkdownView()
        view_frame = Gtk.Frame()
        view_frame.add_css_class('card')
        view_frame.set_child(self.body_rendered)
        view_frame.set_vexpand(True)

        self.body_stack = Gtk.Stack()
        self.body_stack.set_vexpand(True)
        self.body_stack.add_named(view_frame, 'view')
        self.body_stack.add_named(edit_frame, 'edit')
        self.append(self.body_stack)

        # Actions
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_delete = Gtk.Button(label=_('Delete'))
        self.btn_delete.add_css_class('destructive-action')
        actions.append(self.btn_delete)

        spacer = Gtk.Box(hexpand=True)
        actions.append(spacer)

        self.btn_edit = Gtk.Button(label=_('Edit'))
        self.btn_discard = Gtk.Button(label=_('Discard'))
        self.btn_save = Gtk.Button(label=_('Save'))
        self.btn_save.add_css_class('suggested-action')
        actions.append(self.btn_edit)
        actions.append(self.btn_discard)
        actions.append(self.btn_save)
        self.append(actions)

        self.btn_edit.connect('clicked', self._on_edit_clicked)
        self.btn_save.connect('clicked', self._on_save_clicked)
        self.btn_discard.connect('clicked', self._on_discard_clicked)
        self.btn_delete.connect('clicked', self._on_delete_clicked)

        self.set_editable(False)

    # API
    def load(self, header: dict, body: str, editable: bool = False) -> None:
        self.row_author.set_text(header.get('Author', '') or '')
        self.row_date.set_subtitle(header.get('Date', '') or '')
        self._set_category(header.get('Category', '') or '')
        self._set_combo(self.row_priority, self._priorities, header.get('Priority', ''))
        self._set_combo(self.row_status, self._statuses, header.get('Status', ''))
        self.body_buffer.set_text(body or '')
        self.set_editable(editable)
        self.set_sensitive(True)

    def clear(self) -> None:
        self.row_author.set_text('')
        self.row_date.set_subtitle('')
        self._set_category('')
        self.row_priority.set_selected(0)
        self.row_status.set_selected(0)
        self.body_buffer.set_text('')
        self.set_editable(False)

    def header(self) -> dict:
        return {
            'Author': self.row_author.get_text().strip(),
            'Category': self._current_category(),
            'Date': self.row_date.get_subtitle() or '',
            'Priority': self._get_combo(self.row_priority, self._priorities),
            'Status': self._get_combo(self.row_status, self._statuses),
        }

    def body(self) -> str:
        start = self.body_buffer.get_start_iter()
        end = self.body_buffer.get_end_iter()
        return self.body_buffer.get_text(start, end, True)

    def set_editable(self, editable: bool) -> None:
        self._editable = editable
        self.row_author.set_editable(editable)
        self.row_category.set_sensitive(editable)
        self.row_category_other.set_editable(editable)
        self.row_priority.set_sensitive(editable)
        self.row_status.set_sensitive(editable)
        self.body_view.set_editable(editable)
        self.body_view.set_cursor_visible(editable)
        if editable:
            self.body_stack.set_visible_child_name('edit')
        else:
            # Refresh the rendered Markdown from the current buffer content.
            self.body_rendered.set_markdown(self.body())
            self.body_stack.set_visible_child_name('view')
        self.btn_edit.set_visible(not editable)
        self.btn_save.set_visible(editable)
        self.btn_discard.set_visible(editable)
        self._update_delete_category_sensitivity()

    def is_editable(self) -> bool:
        return self._editable

    # Callbacks
    def _on_edit_clicked(self, _button):
        self.set_editable(True)

    def _on_save_clicked(self, _button):
        self.emit('save-requested')

    def _on_discard_clicked(self, _button):
        self.emit('discard-requested')

    def _on_delete_clicked(self, _button):
        self.emit('delete-requested')

    # ComboRow helpers
    @staticmethod
    def _set_combo(combo: Adw.ComboRow, items: List[str], value: str) -> None:
        if value and value in items:
            combo.set_selected(items.index(value))
        else:
            combo.set_selected(0)

    @staticmethod
    def _get_combo(combo: Adw.ComboRow, items: List[str]) -> str:
        idx = combo.get_selected()
        if 0 <= idx < len(items):
            return items[idx]
        return ''

    # Category dropdown / Other... / delete custom
    def _custom_categories(self) -> List[str]:
        if self._category_store is None:
            return []
        try:
            return self._category_store.list()
        except Exception:
            return []

    def _reload_category_items(self, prefer_value: Optional[str] = None) -> None:
        custom = [c for c in self._custom_categories()
                  if c not in self._builtin_categories]
        items = list(self._builtin_categories) + custom + [OTHER_LABEL]
        self._category_items = items
        self.row_category.set_model(Gtk.StringList.new(items))
        if prefer_value is not None:
            self._set_category(prefer_value)
        self._update_delete_category_sensitivity()

    def _set_category(self, value: str) -> None:
        value = (value or '').strip()
        if value and value in self._category_items and value != OTHER_LABEL:
            self.row_category.set_selected(self._category_items.index(value))
            self.row_category_other.set_text('')
            self.row_category_other.set_visible(False)
        elif value:
            self.row_category.set_selected(self._category_items.index(OTHER_LABEL))
            self.row_category_other.set_text(value)
            self.row_category_other.set_visible(True)
        else:
            self.row_category.set_selected(0)
            self.row_category_other.set_text('')
            self.row_category_other.set_visible(False)
        self._update_delete_category_sensitivity()

    def _current_category(self) -> str:
        idx = self.row_category.get_selected()
        if idx < 0 or idx >= len(self._category_items):
            return ''
        label = self._category_items[idx]
        if label == OTHER_LABEL:
            new_value = self.row_category_other.get_text().strip()
            if new_value and self._category_store is not None:
                if new_value not in self._builtin_categories \
                        and not self._category_store.has(new_value):
                    self._category_store.add(new_value)
                    self._reload_category_items(prefer_value=new_value)
            return new_value
        return label

    def _on_category_changed(self, _combo, _pspec):
        idx = self.row_category.get_selected()
        if idx < 0 or idx >= len(self._category_items):
            return
        label = self._category_items[idx]
        is_other = label == OTHER_LABEL
        self.row_category_other.set_visible(is_other)
        if is_other and self._editable:
            self.row_category_other.grab_focus()
        self._update_delete_category_sensitivity()

    def _update_delete_category_sensitivity(self) -> None:
        idx = self.row_category.get_selected()
        deletable = False
        if 0 <= idx < len(self._category_items):
            label = self._category_items[idx]
            deletable = (
                self._editable
                and label != OTHER_LABEL
                and label not in self._builtin_categories
                and self._category_store is not None
                and self._category_store.has(label)
            )
        self.btn_category_delete.set_sensitive(deletable)

    def _on_delete_category_clicked(self, _button):
        if self._category_store is None:
            return
        idx = self.row_category.get_selected()
        if idx < 0 or idx >= len(self._category_items):
            return
        label = self._category_items[idx]
        if label == OTHER_LABEL or label in self._builtin_categories:
            return
        if self._category_store.remove(label):
            self._reload_category_items(prefer_value='')
