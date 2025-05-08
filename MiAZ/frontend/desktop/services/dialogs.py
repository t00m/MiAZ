#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs for MiAZ

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
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
        'responses': [],
        'class_name': 'success'
        }
}

class MiAZDialog:
    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZ.Dialogs')

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

        factory = self.app.get_service('factory')
        icm = self.app.get_service('icons')

        dialog = Adw.AlertDialog.new()
        dialog.set_body_use_markup(True)
        dialog.set_heading_use_markup(True)
        dialog.set_heading(f"{title}")
        dialog.set_body(f"<big>{body}</big>")
        dialog.set_size_request(width, height)
        dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)

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
        box = factory.create_box_vertical(hexpand=True, vexpand=True)
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
                    height: int = -1
                ):
        """Create a new dialog of type info"""
        dialog = self.create(title=title, body=body, dtype='info', widget=widget, callback=callback, data=data, width=width, height=height)
        dialog.get_style_context().add_class(class_name='success')
        return dialog

    def show_error( self,
                    title: str = '',
                    body: str = '',
                    widget: Gtk.Widget = None,
                    callback = None,
                    data = None,
                    width: int = -1,
                    height: int = -1
                ):
        """Create a new dialog of type error"""
        dialog = self.create(title=title, body=body, dtype='error', widget=widget, callback=callback, data=data, width=width, height=height)
        dialog.get_style_context().add_class(class_name='error')
        return dialog

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
        dialog.get_style_context().add_class(class_name='accent')
        return dialog

    def show_warning(self,
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
        dialog.get_style_context().add_class(class_name='warning')
        return dialog

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

        factory = self.app.get_service('factory')
        srvdlg = self.app.get_service('dialogs')

        self.title = ''
        self.key1 = ''
        self.key2 = ''

        self.boxKey1 = factory.create_box_vertical(spacing=6)
        self.lblKey1 = Gtk.Label()
        self.lblKey1.set_xalign(0.0)
        self.lblKey1.set_hexpand(False)
        self.etyValue1 = Gtk.Entry()
        self.etyValue1.set_hexpand(False)
        # ~ self.etyValue1.connect('activate', self.on_dialog_save)

        self.boxKey2 = factory.create_box_vertical(spacing=6)
        self.boxKey2.set_hexpand(True)
        self.lblKey2 = Gtk.Label()
        self.lblKey2.set_xalign(0.0)
        self.etyValue2 = Gtk.Entry()
        # ~ self.etyValue2.connect('activate', self.on_dialog_save)

        self.fields = factory.create_box_horizontal(spacing=6)
        self.fields.set_margin_bottom(margin=12)

        self.widget = factory.create_box_vertical(spacing=6)
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

        srvdlg = self.app.get_service('dialogs')

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
        self.dialog = srvdlg.show_action(title=title, widget=self.widget)
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

        self.title = ''
        self.key1 = ''
        self.key2 = ''

    def create( self,
                title: str='',
                key1: str='',
                key2: str='',
                width: int = -1,
                height: int = -1):

        factory = self.app.get_service('factory')
        srvdlg = self.app.get_service('dialogs')
        self.title = title
        self.key1 = key1

        self.lblKey1.set_markup(f"<b>{self.key1}</b>")
        vbox = factory.create_box_vertical(spacing=12, vexpand=True)
        self.boxKey1.append(vbox)
        hbox = factory.create_box_horizontal()
        hbox.append(self.lblKey1)
        hbox.append(self.etyValue1)
        vbox.append(hbox)
        self.filechooser = Gtk.FileChooserWidget()
        self.filechooser.get_style_context().add_class(class_name='frame')
        self.filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        vbox.append(self.filechooser)
        self.fields.append(self.boxKey1)
        self.widget.append(self.fields)

        # Create dialog
        self.dialog = srvdlg.show_action(title=title, widget=self.widget)
        return self.dialog

    def get_entry_key1(self):
        return  self.etyValue1

    def get_value1(self):
        return self.etyValue1.get_text()

    def set_value1(self, value):
        self.etyValue1.set_text(value)

    def get_value2(self):
        gfile = self.filechooser.get_file()
        try:
            return gfile.get_path()
        except AttributeError:
            return None

    def set_value2(self, value):
        gfile = Gio.File.new_for_path(value)
        self.filechooser.set_file(gfile)


class MiAZFileChooserDialog(MiAZDialog):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZFileChooserDialog'

    def __init__(self, app):
        self.log = MiAZLog('MiAZ.FileChooserDialog')
        self.app = app

    def create( self,
                title: str = '',
                target: str = '',
                callback=None,
                data=None):

        srvdlg = self.app.get_service('dialogs')

        self.title = title
        self.target = target
        self.callback = callback
        self.data = data

        # Widget
        self.w_filechooser = Gtk.FileChooserWidget()
        self.w_filechooser.get_style_context().add_class(class_name='frame')
        if self.target == 'FOLDER':
            self.w_filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        elif self.target == 'FILE':
            self.w_filechooser.set_action(Gtk.FileChooserAction.OPEN)
        elif self.target == 'SAVE':
            self.w_filechooser.set_action(Gtk.FileChooserAction.SAVE)

        # Create dialog
        self.dialog = srvdlg.show_action(   title=title,
                                            widget=self.w_filechooser,
                                            callback=callback,
                                            data=data)

        return self.dialog

    def get_filechooser_widget(self):
        return self.w_filechooser
