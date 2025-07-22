#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs for MiAZ

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

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
        'responses': [],
        'class_name': 'accent'
        }
}

class MiAZDialog:
    # FIXME: to be replace by Gtk.Window in order to allow
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
            label.get_style_context().add_class(class_name='toolbar')
        # And change color
        label.get_style_context().add_class(class_name=miaz_dialog[dtype]['class_name'])

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
        dialog.get_style_context().add_class(class_name='success')
        return dialog

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
        dialog.get_style_context().add_class(class_name='success')
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
        dialog.get_style_context().add_class(class_name='error')
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
        dialog.get_style_context().add_class(class_name='warning')
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

class MiAZDialogAdd:
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZDialogAdd'

    def __init__(self, app):
        self.log = MiAZLog('MiAZDialogAdd')
        self.app = app

        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')

        self.title = ''
        self.key1 = ''
        self.key2 = ''

        self.boxKey1 = self.factory.create_box_vertical(spacing=6)
        self.lblKey1 = Gtk.Label()
        self.lblKey1.set_xalign(0.0)
        self.lblKey1.set_hexpand(False)
        self.etyValue1 = Gtk.Entry()
        self.etyValue1.set_hexpand(False)
        # ~ self.etyValue1.connect('activate', self.on_dialog_save)

        self.boxKey2 = self.factory.create_box_vertical(spacing=6)
        self.boxKey2.set_hexpand(True)
        self.lblKey2 = Gtk.Label()
        self.lblKey2.set_xalign(0.0)
        self.etyValue2 = Gtk.Entry()
        # ~ self.etyValue2.connect('activate', self.on_dialog_save)

        self.fields = self.factory.create_box_horizontal(spacing=6)
        self.fields.set_margin_bottom(margin=12)

        self.widget = self.factory.create_box_vertical(spacing=6)
        self.widget.set_margin_top(margin=12)
        self.widget.set_margin_end(margin=12)
        self.widget.set_margin_start(margin=12)

    def create( self,
                parent: Gtk.Window,
                title: str,
                key1: str,
                key2: str,
                width: int=-1,
                height: int=-1):

        self.title = title
        self.key1 = key1
        self.key2 = key2

        # Widget
        self.boxKey1.append(self.lblKey1)
        self.boxKey1.append(self.etyValue1)
        self.boxKey2.append(self.lblKey2)
        self.boxKey2.append(self.etyValue2)

        ## Box Key 1
        self.lblKey1.set_markup(f"<b>{self.key1}</b>")

        ## Box Key 2
        self.lblKey2.set_markup(f"<b>{self.key2}</b>")

        self.fields.append(self.boxKey1)
        self.fields.append(self.boxKey2)
        self.widget.append(self.fields)

        # Create dialog
        self.dialog = self.srvdlg.show_action(title=title, widget=self.widget)
        return self.dialog

    def get_label_key1(self):
        return self.lblKey1

    def get_label_key2(self):
        return self.lblKey2

    def get_entry_key1(self):
        return  self.etyValue1

    def get_entry_key2(self):
        return  self.etyValue2

    def on_dialog_save(self, *args):
        self.log.error(f"FIXME: {args}")

    def on_dialog_cancel(self, dialog, respone):
        self.log.error(f"FIXME: {args}")

    def get_boxKey1(self):
        return self.boxKey1

    def get_boxKey2(self):
        return self.boxKey2

    def get_value1(self):
        return self.etyValue1.get_text()

    def get_value1_widget(self):
        return self.etyValue1

    def set_value1(self, value):
        self.etyValue1.set_text(value)

    def get_value2(self):
        return self.etyValue2.get_text()

    def set_value2(self, value):
        self.etyValue2.set_text(value)

    def get_value2_widget(self):
        return self.etyValue2


class MiAZDialogAddRepo(MiAZDialogAdd):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZDialogAddRepo'

    def __init__(self, app):
        self.log = MiAZLog('MiAZDialogAdd')
        self.app = app
        super(MiAZDialogAdd, self).__init__()
        super().__init__(app)

        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')

        self.title = ''
        self.key1 = ''
        self.key2 = ''

    def create( self,
                title: str='',
                key1: str='',
                key2: str='',
                width: int = -1,
                height: int = -1):

        self.title = title

        if len(key2.strip()) == 0:
            key2 = GLib.get_home_dir()

        # Repository key
        self.key1 = key1
        self.lblKey1.set_markup(f"<b>{self.key1}</b>")
        vbox = self.factory.create_box_vertical(spacing=12, vexpand=True)
        self.boxKey1.append(vbox)
        hbox = self.factory.create_box_horizontal()
        hbox.append(self.lblKey1)
        hbox.append(self.etyValue1)
        self.etyValue1.connect('changed', self._check_user_input_key)
        vbox.append(hbox)

        # Repository directory
        self.key2 = key2
        self.button = Gtk.Button()
        self.button.set_label(self.key2)
        label = self.button.get_child()
        label.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        self.button.connect("clicked", self.on_open_file)
        vbox.append(self.button)

        self.fields.append(self.boxKey1)
        self.widget.append(self.fields)

        # Create dialog
        self.dialog = self.srvdlg.show_action(title=title, widget=self.widget)
        self.dialog.set_response_enabled('apply', False)
        return self.dialog

    def disable_key1(self):
        self.etyValue1.set_sensitive(False)

    def hide_key1(self):
        self.etyValue1.set_visible(False)

    def on_open_file(self, button):
        dirpath = button.get_label()
        if len(dirpath.strip()) == 0 or dirpath is None:
            dirpath = GLib.get_home_dir()
            folder = Gio.File.new_for_path(dirpath)
        else:
            folder = Gio.File.new_for_path(dirpath)
        button.set_label(dirpath)
        dialog = self.factory.create_filechooser_for_directories(callback=self.on_folder_selected, dirpath=dirpath, parent=button.get_root())

    def on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self.button.set_label(folder.get_path())
        except GLib.Error as e:
            self.log.error(f"Selection cancelled or failed: {e.message}")

    def _check_user_input_key(self, entry):
        key = entry.get_text()
        key_valid = len(key) > 1
        dir_valid = True

        if key_valid and dir_valid:
            user_input_valid = True
        else:
            user_input_valid = False

        self.dialog.set_response_enabled('apply', user_input_valid)

    def get_entry_key1(self):
        return  self.etyValue1

    def get_value1(self):
        return self.etyValue1.get_text()

    def set_value1(self, value):
        if value is None:
            value = ''
        self.etyValue1.set_text(value)

    def get_value2(self):
        return self.button.get_label()

    def set_value2(self, value):
        if value is None:
            value = ''
        self.button.set_label(value)

