#!/usr/bin/python3
# File: dialogs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom dialogs

from gi.repository import Gio
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog

# FIXME: move to factory?

icon_name = {}
icon_name["info"] = "dialog-information-symbolic"
icon_name["warning"] = "dialog-warning-symbolic"
icon_name["error"] = "com.github.t00m.MiAZ-dialog-error-symbolic"
icon_name["question"] = "dialog-question-symbolic"

# ~ icon_name["info"] = "dialog-information-symbolic"
# ~ icon_name["warning"] = "dialog-warning-symbolic"
# ~ icon_name["error"] = "dialog-error-symbolic"
# ~ icon_name["question"] = "dialog-question-symbolic"


class CustomDialog(Gtk.Dialog):
    def __init__(self,
                    app,
                    parent: Gtk.Window,
                    use_header_bar: bool = True,
                    dtype: str = 'info', # [info|warning|error|question]
                    title: str = '',
                    text: str = '',
                    widget: Gtk.Widget = None,
                    callback = None
                ):
        super().__init__()
        self.set_default_size(600, 480)
        self.app = app
        self.set_transient_for(parent)
        self.set_title(title=title)
        self.use_header_bar = use_header_bar

        if callback is not None:
            self.connect('response', callback)
        else:
            self.connect('response', self.dialog_response)

        # Buttons
        if dtype in ['info', 'warning', 'error']:
            self.add_buttons(
            '_OK', Gtk.ResponseType.OK,
            )
            btn_ok = self.get_widget_for_response(response_id=Gtk.ResponseType.OK)
            btn_ok.get_style_context().add_class(class_name='suggested-action')
        else:
            self.add_buttons(
                '_Cancelar', Gtk.ResponseType.CANCEL,
                '_OK', Gtk.ResponseType.OK,
            )
            btn_ok = self.get_widget_for_response(response_id=Gtk.ResponseType.OK)
            btn_ok.get_style_context().add_class(class_name='suggested-action')
            btn_cancel = self.get_widget_for_response(response_id=Gtk.ResponseType.CANCEL)
            btn_cancel.get_style_context().add_class(class_name='destructive-action')

        action_box = btn_ok.get_ancestor(Gtk.Box)
        action_box.get_style_context ().add_class ('toolbar')
        action_box.set_homogeneous(True)

        # Content area
        content_area = self.get_content_area()
        content_area.set_orientation(orientation=Gtk.Orientation.VERTICAL)
        content_area.set_spacing(spacing=24)
        content_area.set_margin_top(margin=6)
        content_area.set_margin_end(margin=6)
        content_area.set_margin_bottom(margin=6)
        content_area.set_margin_start(margin=6)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True, vexpand=True)
        hbox_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, hexpand=True, vexpand=False)
        icman = self.app.get_service('icons')
        icon = icman.get_image_by_name(icon_name[dtype])
        icon.set_pixel_size(48)
        label = Gtk.Label()
        label.set_markup(dtype.title())
        label.get_style_context().add_class(class_name='title-1')
        hbox_title.append(icon)
        hbox_title.append(label)
        vbox.append(hbox_title)
        lblDesc = Gtk.Label()
        lblDesc.set_markup(text)
        lblDesc.set_xalign(0.0)
        lblDesc.get_style_context().add_class(class_name='title-5')
        vbox.append(lblDesc)
        if widget is not None:
            widget.set_vexpand(True)
            widget.set_hexpand(True)
            widget.get_style_context().add_class(class_name='caption')
            widget.get_style_context().add_class(class_name='monospace')
            frame = Gtk.Frame()
            frame.set_child(widget)
            vbox.append(frame)
        content_area.append(child=vbox)

    def dialog_response(self, dialog, response):
        dialog.hide()

    def get_entry_text(self):
        return self.entry.get_text()

class Question(CustomDialog):
    def __init__(self,
                    app,
                    parent: Gtk.Window,
                    title: str = '',
                    text: str = '',
                    callback = None
                ):
        super().__init__(app=app, parent=parent, use_header_bar=False, dtype='question', title=title, text=text, callback=callback)

    def dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            return True
        elif response == Gtk.ResponseType.CANCEL:
            return False
        dialog.hide()

class MiAZDialogAdd(Gtk.Dialog):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZDialogAdd'

    def __init__(self, app, parent, title, key1, key2, width=-1, height=-1):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZDialogAdd')
        self.title = title
        self.key1 = key1
        self.key2 = key2
        self.factory = self.app.get_service('factory')
        self.set_transient_for(parent)
        self.set_size_request(width, height)
        self.set_modal(True)
        self.set_title(title)
        self.widget = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.widget.set_margin_top(margin=12)
        self.widget.set_margin_end(margin=12)
        self.widget.set_margin_start(margin=12)

        header = Gtk.HeaderBar()
        # ~ header.set_show_end_title_buttons(False)
        # ~ header.set_show_start_title_buttons(False)
        lblTitle = self.factory.create_label(title)
        header.set_title_widget(lblTitle)
        self.set_titlebar(header)
        btnSave = self.factory.create_button(icon_name='', title='Save', callback=self.on_dialog_save)
        btnSave.get_style_context().add_class(class_name='suggested-action')
        btnCancel = self.factory.create_button(icon_name='', title='Cancel', callback=self.on_dialog_cancel)
        btnCancel.get_style_context().add_class(class_name='destructive-action')
        self.boxButtons = Gtk.CenterBox()
        self.boxButtons.set_halign(Gtk.Align.END)
        self.boxButtons.set_margin_bottom(6)
        self.boxButtons.set_start_widget(btnCancel)
        self.boxButtons.set_end_widget(btnSave)
        self.fields = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        self.fields.set_margin_bottom(margin=12)
        self.boxKey1 = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.boxKey1.set_hexpand(False)
        self._setup_widget()

    def _setup_widget(self):
        self.lblKey1 = Gtk.Label()
        self.lblKey1.set_xalign(0.0)
        self.lblKey1.set_hexpand(False)
        self.lblKey1.set_markup(f"<b>{self.key1}</b>")
        self.etyValue1 = Gtk.Entry()
        self.etyValue1.set_hexpand(False)
        self.etyValue1.connect('activate', self.on_dialog_save)
        self.boxKey1.append(self.lblKey1)
        self.boxKey1.append(self.etyValue1)
        self.boxKey2 = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.boxKey2.set_hexpand(True)
        self.lblKey2 = Gtk.Label()
        self.lblKey2.set_xalign(0.0)
        self.lblKey2.set_markup(f"<b>{self.key2}</b>")
        self.etyValue2 = Gtk.Entry()
        self.etyValue2.connect('activate', self.on_dialog_save)
        self.boxKey2.append(self.lblKey2)
        self.boxKey2.append(self.etyValue2)
        separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.fields.append(self.boxKey1)
        self.fields.append(self.boxKey2)
        self.widget.append(self.fields)
        self.widget.append(separator)
        self.widget.append(self.boxButtons)
        contents = self.get_content_area()
        contents.append(self.widget)

    def get_label_key1(self):
        return self.lblKey1

    def get_label_key2(self):
        return self.lblKey2

    def get_entry_key1(self):
        return  self.etyValue1

    def get_entry_key2(self):
        return  self.etyValue2

    def on_dialog_save(self, *args):
        self.emit('response', Gtk.ResponseType.ACCEPT)
        self.destroy()

    def on_dialog_cancel(self, *args):
        self.emit('response', Gtk.ResponseType.CANCEL)
        self.destroy()

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

    def __init__(self, app, parent, title, key1, key2, width=-1, height=-1):
        super(MiAZDialogAdd, self).__init__()
        super().__init__(app, parent, title, key1, key2)
        self.title = title
        self.key1 = key1

    def _setup_widget(self):
        vbox = self.factory.create_box_vertical(spacing=12)
        self.boxKey1.append(vbox)
        hbox = self.factory.create_box_horizontal()
        self.lblKey1 = Gtk.Label()
        self.lblKey1.set_xalign(0.0)
        self.lblKey1.set_hexpand(False)
        self.lblKey1.set_markup(f"<b>{self.key1}</b>")
        self.etyValue1 = Gtk.Entry()
        self.etyValue1.set_hexpand(False)
        hbox.append(self.lblKey1)
        hbox.append(self.etyValue1)
        vbox.append(hbox)
        frame = Gtk.Frame()
        self.filechooser = Gtk.FileChooserWidget()
        self.filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        frame.set_child(self.filechooser)
        vbox.append(frame)
        separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.fields.append(self.boxKey1)
        self.widget.append(self.fields)
        self.widget.append(separator)
        self.widget.append(self.boxButtons)
        contents = self.get_content_area()
        contents.append(self.widget)

    def get_value1(self):
        return self.etyValue1.get_text()

    def set_value1(self, value):
        self.etyValue1.set_text(value)

    def get_value2(self):
        gfile = self.filechooser.get_file()
        return gfile.get_path()

    def set_value2(self, value):
        gfile = Gio.File.new_for_path(value)
        self.filechooser.set_file(gfile)
