#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs for MiAZ

from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog

miaz_dialog = {
    'action': {
        'icon': 'com.github.t00m.MiAZ-document-edit-symbolic',
        'type': Gtk.MessageType.INFO,
        'buttons': Gtk.ButtonsType.OK_CANCEL
        },
    'info': {
        'icon': 'dialog-information-symbolic',
        'type': Gtk.MessageType.INFO,
        'buttons': Gtk.ButtonsType.NONE
        },
    'warning': {
        'icon': 'dialog-warning-symbolic',
        'type': Gtk.MessageType.WARNING,
        'buttons': Gtk.ButtonsType.NONE
        },
    'error': {
        'icon': 'com.github.t00m.MiAZ-dialog-error-symbolic',
        'type': Gtk.MessageType.ERROR,
        'buttons': Gtk.ButtonsType.NONE
        },
    'question': {
        'icon': 'dialog-question-symbolic',
        'type': Gtk.MessageType.QUESTION,
        'buttons': Gtk.ButtonsType.YES_NO
        }
}

class MiAZDialog:
    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZ.Factory')

    def create( self,
                parent: Gtk.Window,
                dtype: str,
                title: str,
                body: str = '',
                widget: Gtk.Widget = None,
                callback = None,
                data = None,
                width: int = -1,
                height: int = -1,
                ):

        icm = self.app.get_service('icons')

        # Build dialog
        dialog = Gtk.MessageDialog(
                    transient_for=parent,
                    destroy_with_parent=False,
                    modal=True,
                    message_type=miaz_dialog[dtype]['type'],
                    secondary_text=body,
                    secondary_use_markup=True,
                    buttons=miaz_dialog[dtype]['buttons'])

        # Set header
        dialog.use_header_bar = True
        header = Gtk.HeaderBar()
        icon = icm.get_image_by_name(miaz_dialog[dtype]['icon'])
        header.pack_start(icon)
        # ~ lblType = Gtk.Label.new(dtype.title())
        # ~ lblType.get_style_context().add_class(class_name='title-3')
        # ~ header.pack_start(lblType)
        lblTitle = Gtk.Label.new(title)
        lblTitle.get_style_context().add_class(class_name='title-3')
        header.set_title_widget(lblTitle)
        dialog.set_titlebar(header)

        # Set custom size
        dialog.set_default_size(width, height)

        # Add custom widget
        if widget is not None:
            message_area = dialog.get_message_area()
            message_area.set_visible(False)
            content_area = dialog.get_content_area()
            content_area.set_spacing(0)
            content_area.append(child=widget)

        # Assign callback, if any. Otherwise, default is closing.
        if callback is None:
            dialog.connect('response', self.close)
        else:
            dialog.connect('response', callback, data)

        return dialog

    def close(self, dialog, response):
        dialog.destroy()



class MiAZDialogAdd:
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZDialogAdd'

    def __init__(self, app):
        self.log = MiAZLog('MiAZDialogAdd')
        self.app = app

        self.title = ''
        self.key1 = ''
        self.key2 = ''

    def create( self,
                parent: Gtk.Window,
                title: str,
                key1: str,
                key2: str,
                width: int=-1,
                height: int=-1):

        factory = self.app.get_service('factory')
        srvdlg = self.app.get_service('dialogs')

        self.title = title
        self.key1 = key1
        self.key2 = key2

        # Widget
        widget = factory.create_box_vertical(spacing=6)
        widget.set_margin_top(margin=12)
        widget.set_margin_end(margin=12)
        widget.set_margin_start(margin=12)


        fields = factory.create_box_horizontal(spacing=6)
        fields.set_margin_bottom(margin=12)

        ## Box Key 1
        self.boxKey1 = factory.create_box_vertical(spacing=6)
        self.lblKey1 = Gtk.Label()
        self.lblKey1.set_xalign(0.0)
        self.lblKey1.set_hexpand(False)
        self.lblKey1.set_markup(f"<b>{self.key1}</b>")
        self.etyValue1 = Gtk.Entry()
        self.etyValue1.set_hexpand(False)
        self.etyValue1.connect('activate', self.on_dialog_save)
        self.boxKey1.append(self.lblKey1)
        self.boxKey1.append(self.etyValue1)

        ## Box Key 2
        self.boxKey2 = factory.create_box_vertical(spacing=6)
        self.boxKey2.set_hexpand(True)
        self.lblKey2 = Gtk.Label()
        self.lblKey2.set_xalign(0.0)
        self.lblKey2.set_markup(f"<b>{self.key2}</b>")
        self.etyValue2 = Gtk.Entry()
        self.etyValue2.connect('activate', self.on_dialog_save)
        self.boxKey2.append(self.lblKey2)
        self.boxKey2.append(self.etyValue2)

        fields.append(self.boxKey1)
        fields.append(self.boxKey2)
        widget.append(fields)

        # Create dialog
        self.dialog = srvdlg.create( parent=parent,
                                dtype='action',
                                title=title,
                                widget=widget)
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
        button = self.dialog.get_widget_for_response(Gtk.ResponseType.OK)
        button.activate()

    def on_dialog_cancel(self, dialog, respone):
        button = self.dialog.get_widget_for_response(Gtk.ResponseType.CANCEL)
        button.activate()

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
