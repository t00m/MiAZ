#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs for MiAZ

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog

miaz_dialog = {
    'action': {
        'icon': 'io.github.t00m.MiAZ-document-edit-symbolic',
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
        'icon': 'io.github.t00m.MiAZ-dialog-error-symbolic',
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
        self.log = MiAZLog('MiAZ.Dialogs')

    def create( self,
                enable_response: bool = False,
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

        dialog = Adw.AlertDialog.new(title, body)
        dialog.set_body_use_markup(True)
        dialog.set_heading_use_markup(True)
        # ~ dialog.set_body(body)

        # Add custom widget
        if widget is not None:
            dialog.set_extra_child(widget)

        # Assign callback, if any. Otherwise, default is closing.
        if enable_response:
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("apply", _("Apply"))
            dialog.set_response_appearance("cancel", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            dialog.add_response("cancel", _("Ok"))
            dialog.set_response_appearance("cancel", Adw.ResponseAppearance.SUGGESTED)

        if callback is None:
            dialog.connect('response', self.close)
        else:
            dialog.connect('response', callback, data)

        return dialog

    def close(self, dialog, response):
        pass


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
        self.dialog = srvdlg.create(    enable_response=True,
                                        dtype='action',
                                        title=title,
                                        widget=self.widget)
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
                parent:Gtk.Window,
                title: str,
                key1: str,
                key2: str,
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
        self.filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        vbox.append(self.filechooser)
        self.fields.append(self.boxKey1)
        self.widget.append(self.fields)

        # Create dialog
        self.dialog = srvdlg.create(    enable_response=False,
                                        dtype='action',
                                        title=title,
                                        widget=self.widget)
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
                parent: Gtk.Window,
                title: str,
                target: str,
                callback=None,
                data=None):

        srvdlg = self.app.get_service('dialogs')

        self.parent = parent
        self.title = title
        self.target = target
        self.callback = callback
        self.data = data

        # Widget
        self.w_filechooser = Gtk.FileChooserWidget()
        if self.target == 'FOLDER':
            self.w_filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        elif self.target == 'FILE':
            self.w_filechooser.set_action(Gtk.FileChooserAction.OPEN)
        elif self.target == 'SAVE':
            self.w_filechooser.set_action(Gtk.FileChooserAction.SAVE)

        # Create dialog
        self.dialog = srvdlg.create(enable_response=True,
                                    dtype='action',
                                    title=title,
                                    widget=self.w_filechooser,
                                    callback=callback,
                                    data=data)

        return self.dialog

    def get_filechooser_widget(self):
        return self.w_filechooser
