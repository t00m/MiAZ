#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs for MiAZ

import re
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog

miaz_dialog = {
    'action': {
        'icon': 'io.github.t00m.MiAZ-document-edit-symbolic',
        'responses': [('cancel', _('Cancel')), ('apply', _('Apply'))],
        'class_name': 'accent'
        },
    'info': {
        'icon': 'dialog-information-symbolic',
        'responses': [('close', _('Close'))],
        'class_name': 'accent'
        },
    'warning': {
        'icon': 'dialog-warning-symbolic',
        'responses': [('close', _('Close'))],
        'class_name': 'warning'
        },
    'error': {
        'icon': 'io.github.t00m.MiAZ-dialog-error-symbolic',
        'responses': [('close', _('Close'))],
        'class_name': 'error'
        },
    'question': {
        'icon': 'dialog-question-symbolic',
        'responses': [('apply', _('Yes')), ('cancel', _('No'))],
        'class_name': ''
        },
    'noop': {
        'icon': '',
        'responses': [('close', _('Close'))],
        'class_name': 'accent'
        }
}

class MiAZDialog:
    # FIXME: to be replaced by Gtk.Window to let
    # Gtk.FileDialog have the proper parent
    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZ.Dialogs')

        self.factory = self.app.get_service('factory')

    def create( self,
                dtype: str = '',
                title: str = '',
                body: str = '',
                widget: Gtk.Widget = None,
                callback = None,
                data = None,
                width: int = -1,
                height: int = -1,
        ):

        dialog = Adw.AlertDialog.new()
        dialog.set_body_use_markup(True)
        dialog.set_heading_use_markup(True)
        dialog.set_heading(f"{title}")
        dialog.set_body(f"{body}")
        dialog.set_size_request(width, height)
        # ~ dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)

        # Trick to reduce body_label size
        adwgizmo = dialog.get_child()
        windowhandle = adwgizmo.get_first_child()
        label = self.app.find_widget(windowhandle, Gtk.Label, 'body_label')
        if label is not None:
            label.set_vexpand(False)
            label.add_css_class('toolbar')
            # And change color
            class_name = miaz_dialog[dtype]['class_name']
            if class_name:
                label.add_css_class(class_name)

        # Add custom widget
        box = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        if widget is not None:
            box.append(widget)
        dialog.set_extra_child(box)

        responses = miaz_dialog[dtype]['responses']
        for response in responses:
            respid, label = response
            dialog.add_response(respid, label)
            if respid in ['apply', 'close']:
                dialog.set_response_appearance(respid, Adw.ResponseAppearance.SUGGESTED)
            elif respid in ['cancel', 'no']:
                dialog.set_response_appearance(respid, Adw.ResponseAppearance.DESTRUCTIVE)

        # Enter triggers the primary action, Escape/dismiss the cancel one, so
        # add/edit/delete dialogs can be confirmed from the keyboard.
        response_ids = [pair[0] for pair in responses]
        for candidate in ('apply', 'close'):
            if candidate in response_ids:
                dialog.set_default_response(candidate)
                break
        for candidate in ('cancel', 'no', 'close'):
            if candidate in response_ids:
                dialog.set_close_response(candidate)
                break

        if callback is None:
            dialog.connect('response', self.close)
        else:
            dialog.connect('response', callback, data)

        return dialog

    def close(self, dialog, response):
        pass

    def show_noop(  self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1
                ):
        """Create a new dialog of type info"""
        dialog = self.create(title=title, body=body, dtype='noop', widget=widget, callback=callback, data=data, width=width, height=height)
        dialog.add_css_class('success')
        return dialog

    def show_toast(self, message: str, timeout: int = 3):
        overlay = self.app.get_widget('toast-overlay')
        if overlay is not None:
            toast = Adw.Toast(title=message)
            toast.set_timeout(timeout)
            overlay.add_toast(toast)

    def show_info(  self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1,
                    parent: Gtk.Widget = None
                ):
        """Create a new dialog of type info"""
        dialog = self.create(title=title, body=body, dtype='info', widget=widget, callback=callback, data=data, width=width, height=height)
        dialog.add_css_class('success')
        dialog.present(parent)

    def show_error( self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1,
                    parent: Gtk.Widget = None
                ):
        """Create a new dialog of type error"""
        if parent is None:
            parent = self.app.get_widget('window')
        dialog = self.create(title=title, body=body, dtype='error', widget=widget, callback=callback, data=data, width=width, height=height)
        dialog.add_css_class('error')
        dialog.set_default_response('close')
        dialog.set_close_response('close')
        dialog.present(parent)

    def show_action(self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1
                ):
        """Create a new dialog of type error"""
        dialog = self.create(title=title, body=body, dtype='action', widget=widget, callback=callback, data=data, width=width, height=height)
        # ~ dialog.get_style_context().add_class(class_name='accent')
        return dialog

    def show_warning(self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1,
                    parent: Gtk.Widget = None
                ):
        """Create a new dialog of type error"""
        dialog = self.create(title=title, body=body, dtype='warning', widget=widget, callback=callback, data=data, width=width, height=height)
        dialog.add_css_class('warning')
        dialog.present(parent)

    def show_question(self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1
                ):
        """Create a new dialog of type error"""
        dialog = self.create(title=title, body=body, dtype='question', widget=widget, callback=callback, data=data, width=width, height=height)
        return dialog

    def show_confirmation(self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    confirm_label: str = None,
                    confirm_id: str = 'apply',
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1
                ):
        """HIG destructive confirmation: Cancel is the default and the
        confirm button is styled as destructive (so Enter does not destroy)."""
        if confirm_label is None:
            confirm_label = _('Delete')
        dialog = Adw.AlertDialog.new()
        dialog.set_heading_use_markup(True)
        dialog.set_body_use_markup(True)
        dialog.set_heading(f"{title}")
        dialog.set_body(f"{body}")
        if width > 0 or height > 0:
            dialog.set_size_request(width, height)
        if widget is not None:
            box = self.factory.create_box_vertical(hexpand=True, vexpand=True)
            box.append(widget)
            dialog.set_extra_child(box)
        dialog.add_response('cancel', _('Cancel'))
        dialog.add_response(confirm_id, confirm_label)
        dialog.set_response_appearance(confirm_id, Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response('cancel')
        dialog.set_close_response('cancel')
        if callback is not None:
            dialog.connect('response', callback, data)
        return dialog

class MiAZDialogAdd(Adw.Dialog):
    """HIG-compliant input dialog (Adw.Dialog) to create or edit a
    key + description pair. Emits 'response' with 'apply' or 'cancel' so
    existing callers keep working."""
    __gtype_name__ = 'MiAZDialogAdd'
    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, app):
        super().__init__()
        self.log = MiAZLog('MiAZDialogAdd')
        self.app = app
        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')
        self._action_id = 'apply'
        self._responded = False
        self.connect('closed', self._on_closed)

    def create(self, parent=None, title='', key1='', key2='',
               width=-1, height=-1, action_label=None):
        if action_label is None:
            action_label = _('Apply')
        self.set_title(title)
        self.set_content_width(width if width > 0 else 420)
        if height > 0:
            self.set_content_height(height)

        toolbar_view = Adw.ToolbarView()
        headerbar = Adw.HeaderBar()
        headerbar.set_show_start_title_buttons(False)
        headerbar.set_show_end_title_buttons(False)

        btn_cancel = Gtk.Button(label=_('Cancel'))
        btn_cancel.connect('clicked', self._on_cancel_clicked)
        headerbar.pack_start(btn_cancel)

        self.btn_action = Gtk.Button(label=action_label)
        self.btn_action.add_css_class('suggested-action')
        self.btn_action.connect('clicked', self._on_action_clicked)
        headerbar.pack_end(self.btn_action)
        toolbar_view.add_top_bar(headerbar)

        group = Adw.PreferencesGroup()
        group.set_margin_top(12)
        group.set_margin_bottom(12)
        group.set_margin_start(12)
        group.set_margin_end(12)
        self.row_key = Adw.EntryRow(title=key1)
        self.row_value = Adw.EntryRow(title=key2)
        self.row_key.connect('entry-activated', self._on_action_clicked)
        self.row_value.connect('entry-activated', self._on_action_clicked)
        group.add(self.row_key)
        group.add(self.row_value)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_child(group)
        toolbar_view.set_content(clamp)
        self.set_child(toolbar_view)
        return self

    # Response plumbing
    def _on_cancel_clicked(self, *args):
        self._respond('cancel')

    def _on_action_clicked(self, *args):
        if not self.btn_action.get_sensitive():
            return
        self._respond(self._action_id)

    def _respond(self, response_id):
        if self._responded:
            return
        self._responded = True
        self.emit('response', response_id)
        self.close()

    def _on_closed(self, *args):
        # Escape or any other dismissal counts as cancel.
        if not self._responded:
            self._responded = True
            self.emit('response', 'cancel')

    # Value accessors (kept compatible with the previous API)
    def set_value1(self, value):
        self.row_key.set_text(value or '')

    def set_value2(self, value):
        self.row_value.set_text(value or '')

    def get_value1(self):
        return self.row_key.get_text()

    def get_value2(self):
        return self.row_value.get_text()

    def get_entry_key1(self):
        return self.row_key

    def set_response_enabled(self, response_id, enabled):
        self.btn_action.set_sensitive(enabled)


class MiAZDialogAddRepo(MiAZDialogAdd):
    """Add/edit a repository: name (EntryRow) + location (folder chooser)."""
    __gtype_name__ = 'MiAZDialogAddRepo'

    def create(self, title='', key1='', key2='',
               width=-1, height=-1, action_label=None):
        if action_label is None:
            action_label = _('Apply')
        if len(key2.strip()) == 0:
            key2 = _('Location')
        self._folder = GLib.get_home_dir()

        self.set_title(title)
        self.set_content_width(width if width > 0 else 460)
        if height > 0:
            self.set_content_height(height)

        toolbar_view = Adw.ToolbarView()
        headerbar = Adw.HeaderBar()
        headerbar.set_show_start_title_buttons(False)
        headerbar.set_show_end_title_buttons(False)

        btn_cancel = Gtk.Button(label=_('Cancel'))
        btn_cancel.connect('clicked', self._on_cancel_clicked)
        headerbar.pack_start(btn_cancel)

        self.btn_action = Gtk.Button(label=action_label)
        self.btn_action.add_css_class('suggested-action')
        self.btn_action.connect('clicked', self._on_action_clicked)
        headerbar.pack_end(self.btn_action)
        toolbar_view.add_top_bar(headerbar)

        group = Adw.PreferencesGroup()
        group.set_margin_top(12)
        group.set_margin_bottom(12)
        group.set_margin_start(12)
        group.set_margin_end(12)

        self.row_key = Adw.EntryRow(title=key1)
        self.row_key.connect('changed', self._check_user_input_key)
        self.row_key.connect('entry-activated', self._on_action_clicked)
        group.add(self.row_key)

        self.row_folder = Adw.ActionRow(title=key2)
        self.row_folder.set_subtitle(self._folder)
        btn_folder = Gtk.Button(icon_name='folder-symbolic')
        btn_folder.set_valign(Gtk.Align.CENTER)
        btn_folder.add_css_class('flat')
        btn_folder.connect('clicked', self.on_open_file)
        self.row_folder.add_suffix(btn_folder)
        self.row_folder.set_activatable_widget(btn_folder)
        group.add(self.row_folder)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(440)
        clamp.set_child(group)
        toolbar_view.set_content(clamp)
        self.set_child(toolbar_view)

        self.btn_action.set_sensitive(False)
        return self

    def disable_key1(self):
        self.row_key.set_sensitive(False)

    def set_value1(self, value):
        self.row_key.set_text(value or '')

    def get_value1(self):
        return self.row_key.get_text()

    def set_value2(self, value):
        self._folder = value or GLib.get_home_dir()
        self.row_folder.set_subtitle(self._folder)

    def get_value2(self):
        return self._folder

    def on_open_file(self, button):
        dirpath = self._folder or GLib.get_home_dir()
        self.factory.create_filechooser_for_directories(
            callback=self.on_folder_selected, dirpath=dirpath,
            parent=button.get_root())

    def on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self._folder = folder.get_path()
            self.row_folder.set_subtitle(self._folder)
        except GLib.Error as e:
            self.log.error(f"Selection cancelled or failed: {e.message}")

    def _check_user_input_key(self, entry):
        raw = entry.get_text()
        sanitized = self._sanitize_repo_id(raw)
        if sanitized != raw:
            pos = entry.get_position() if hasattr(entry, 'get_position') else len(sanitized)
            entry.set_text(sanitized)
            if hasattr(entry, 'set_position'):
                entry.set_position(min(pos, len(sanitized)))
        self.btn_action.set_sensitive(len(sanitized) > 1)

    @staticmethod
    def _sanitize_repo_id(value: str) -> str:
        # Mirrors MiAZUtil.valid_key: collapse whitespace/hyphens to '_' and
        # strip characters disallowed in repo identifiers, so the user sees
        # the canonical id as they type instead of after submit.
        cleaned = value.strip().replace('-', '_').replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', cleaned)

