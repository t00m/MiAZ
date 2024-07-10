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

