#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import gi
gi.require_version('Adw', '1')
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import get_logger

class MiAZDialogAdd(Gtk.Dialog):
    """ MiAZ Doc Browser Widget"""
    __gtype_name__ = 'MiAZDialogAdd'

    def __init__(self, app, parent, title, key1, key2, width=-1, height=-1):
        super(MiAZDialogAdd, self).__init__()
        self.app = app
        self.log = get_logger('MiAZDialogAdd')
        self.title = title
        self.key1 = key1
        self.key2 = key2
        self.factory = self.app.get_factory()
        self.set_transient_for(parent)
        self.set_size_request(width, height)
        self.set_modal(True)
        self.set_title(title)
        self.widget = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.widget.set_margin_top(margin=12)
        self.widget.set_margin_end(margin=12)
        self.widget.set_margin_start(margin=12)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        lblTitle = self.factory.create_label(title)
        header.set_title_widget(lblTitle)
        self.set_titlebar(header)
        btnSave = self.factory.create_button('', 'Save', self.on_dialog_save)
        # ~ btnSave.get_style_context().add_class(class_name='suggested-action')
        btnCancel = self.factory.create_button('', 'Cancel', self.on_dialog_cancel)
        # ~ btnCancel.get_style_context().add_class(class_name='destructive-action')
        self.boxButtons = Gtk.CenterBox()
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
        self.lblKey1.set_markup("<b>%s</b>" % key1)
        self.etyValue1 = Gtk.Entry()
        self.etyValue1.set_hexpand(False)
        self.etyValue1.connect('activate', self.on_dialog_save)
        self.boxKey1.append(self.lblKey1)
        self.boxKey1.append(self.etyValue1)
        self.boxKey2 = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.boxKey2.set_hexpand(True)
        self.lblKey2 = Gtk.Label()
        self.lblKey2.set_xalign(0.0)
        self.lblKey2.set_markup("<b>%s</b>" % self.key2)
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
        self.lblKey1 = Gtk.Label()
        self.lblKey1.set_xalign(0.0)
        self.lblKey1.set_hexpand(False)
        self.lblKey1.set_text(self.key1)
        self.boxKey1.append(self.lblKey1)
        self.boxKey2 = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.boxKey2.set_hexpand(False)
        btnRepoSource = self.factory.create_button('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        self.boxKey2.append(btnRepoSource)
        separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        self.fields.append(self.boxKey1)
        self.fields.append(self.boxKey2)
        self.widget.append(self.fields)
        self.widget.append(separator)
        self.widget.append(self.boxButtons)
        contents = self.get_content_area()
        contents.append(self.widget)

    def get_value1(self):
        return self.lblKey1.get_text()

    def set_value1(self, value):
        self.lblKey1.set_text(value)

    def show_filechooser_source(self, *args):
            filechooser = self.factory.create_filechooser(
                        parent=self,
                        title='Choose target directory',
                        target = 'FOLDER',
                        callback = self.on_filechooser_response_source
                        )
            filechooser.show()

    def on_filechooser_response_source(self, dialog, response, data=None):
        use_repo = False
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            box = content_area.get_first_child()
            filechooser = box.get_first_child()
            gfile = filechooser.get_file()
            try:
                gfile = filechooser.get_file()
            except AttributeError as error:
                self.log.error(error)
                raise
            if gfile is None:
                self.log.debug("No directory set. Do nothing.")
                # FIXME: Show warning message. Priority: low
                return
            self.set_value1(gfile.get_path())
        dialog.destroy()
