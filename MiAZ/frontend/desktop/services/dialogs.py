#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs for MiAZ

import re
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
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
            # Let the user select and copy the body text (for example a command
            # to run or an error message), and align it to the left instead of
            # the AlertDialog default centre.
            label.set_selectable(True)
            label.set_xalign(0)
            label.set_justify(Gtk.Justification.LEFT)
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


class MiAZWindowDialog(Adw.Window):
    """A movable, top-level replacement for Adw.AlertDialog.

    Since libadwaita 1.5 Adw.AlertDialog (and Adw.Dialog) render as an overlay
    inside the parent window's surface, so the user cannot drag them and they
    cannot leave the window. This is a real top-level Adw.Window: set it
    transient for the main window and it floats above the main window while
    staying freely movable by its header bar, even onto another monitor.

    Do NOT pair transient_for with set_modal(True): GNOME's
    "attach-modal-dialogs" then glues the window to the parent titlebar so it
    moves with the parent. To block the parent while this dialog is open,
    disable the parent (parent.set_sensitive(False)) and re-enable it on the
    'closed' signal instead.

    It mirrors the slice of the AlertDialog API the rename flow and the
    MiAZAutoScan plugin rely on: add_response(), set_response_appearance(),
    set_response_enabled(), set_default_response(), set_close_response(), the
    'response' signal, and the 'closed' signal. Unlike AlertDialog it does not
    auto-dismiss when a response fires; the handler decides whether to close().
    """
    __gtype_name__ = 'MiAZWindowDialog'
    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'closed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app, title='', body='', widget=None, width=-1, height=-1):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.WindowDialog')
        self.factory = self.app.get_service('factory')
        self._buttons = {}
        self._close_response = None
        self.set_title(title)
        self.set_destroy_with_parent(True)
        self.set_default_size(width if width > 0 else 600,
                              height if height > 0 else 480)

        headerbar = Adw.HeaderBar()
        headerbar.set_title_widget(Adw.WindowTitle(title=title, subtitle=''))
        self.headerbar = headerbar

        self._action_bar = Gtk.ActionBar()
        # Only shown once it has content, so a close-only window (headerbar close
        # button, no responses) does not carry an empty bottom bar.
        self._action_bar.set_revealed(False)

        content = self.factory.create_box_vertical(
            margin=12, spacing=12, hexpand=True, vexpand=True)
        if body:
            label = Gtk.Label()
            label.set_use_markup(True)
            label.set_markup(body)
            label.set_wrap(True)
            label.set_xalign(0)
            content.append(label)
        if widget is not None:
            content.append(widget)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(headerbar)
        toolbar_view.set_content(content)
        toolbar_view.add_bottom_bar(self._action_bar)
        self.set_content(toolbar_view)

        evk = Gtk.EventControllerKey.new()
        self.add_controller(evk)
        evk.connect('key-pressed', self._on_key_pressed)
        self.connect('close-request', self._on_close_request)

    # AlertDialog-compatible API

    def add_response(self, response_id, label):
        button = Gtk.Button(label=label)
        button.connect('clicked', self._on_button_clicked, response_id)
        self._buttons[response_id] = button
        # Dismiss-style actions on the left, affirmative ones on the right.
        if response_id in ('cancel', 'no', 'close'):
            self._action_bar.pack_start(button)
        else:
            self._action_bar.pack_end(button)
        self._action_bar.set_revealed(True)
        return button

    def pack_header_end(self, widget):
        # Place a widget on the right side of the header bar (e.g. a
        # suggested action that is not part of the bottom response buttons).
        self.headerbar.pack_end(widget)

    def pack_header_start(self, widget):
        # Place a widget on the left side of the header bar.
        self.headerbar.pack_start(widget)

    def set_title_widget(self, widget):
        # Replace the window title in the header bar, for a dialog that shows
        # something else there (a view switcher, for instance).
        self.headerbar.set_title_widget(widget)

    def pack_action_end(self, widget):
        # Place a widget on the right side of the bottom action bar, next to
        # the affirmative response buttons.
        self._action_bar.pack_end(widget)
        self._action_bar.set_revealed(True)

    def pack_action_start(self, widget):
        # Place a widget on the left side of the bottom action bar.
        self._action_bar.pack_start(widget)
        self._action_bar.set_revealed(True)

    def set_show_close_button(self, visible):
        # Toggle the window-control buttons (including close) in the header bar.
        self.headerbar.set_show_start_title_buttons(visible)
        self.headerbar.set_show_end_title_buttons(visible)

    def set_response_appearance(self, response_id, appearance):
        button = self._buttons.get(response_id)
        if button is None:
            return
        if appearance == Adw.ResponseAppearance.SUGGESTED:
            button.add_css_class('suggested-action')
        elif appearance == Adw.ResponseAppearance.DESTRUCTIVE:
            button.add_css_class('destructive-action')

    def set_response_enabled(self, response_id, enabled):
        button = self._buttons.get(response_id)
        if button is not None:
            button.set_sensitive(enabled)

    def set_default_response(self, response_id):
        button = self._buttons.get(response_id)
        if button is not None:
            self.set_default_widget(button)

    def set_close_response(self, response_id):
        self._close_response = response_id

    def present(self, parent=None):
        # Adw.AlertDialog.present() takes the parent; accept it here so the
        # existing call sites keep working and use it as the transient parent.
        if parent is not None and self.get_transient_for() is None:
            self.set_transient_for(parent)
            self.set_modal(True)
        super().present()

    # Signal handlers

    def _on_button_clicked(self, _button, response_id):
        self.emit('response', response_id)

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            if self._close_response is not None:
                self.emit('response', self._close_response)
            else:
                # No response buttons (e.g. a close-only management window):
                # Escape just closes.
                self.close()
            return True
        return False

    def _on_close_request(self, _window):
        self.emit('closed')
        return False


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
        # Both fields are mandatory: the action stays disabled until the key and
        # the value are both non-empty, so no field can be created with a blank
        # key or a blank description.
        self.row_key.connect('changed', self._validate_inputs)
        self.row_value.connect('changed', self._validate_inputs)
        group.add(self.row_key)
        group.add(self.row_value)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_child(group)
        toolbar_view.set_content(clamp)
        self.set_child(toolbar_view)
        self._validate_inputs()
        return self

    def _validate_inputs(self, *args):
        key = self.row_key.get_text().strip()
        value = self.row_value.get_text().strip()
        self.btn_action.set_sensitive(bool(key) and bool(value))

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

        self.row_description = Adw.EntryRow(title=_('Description'))
        self.row_description.connect('entry-activated', self._on_action_clicked)
        group.add(self.row_description)

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

    def set_value3(self, value):
        self.row_description.set_text(value or '')

    def get_value3(self):
        return self.row_description.get_text()

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

