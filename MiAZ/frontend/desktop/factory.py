#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Pango

from MiAZ.frontend.desktop.icons import MiAZIconManager

class MiAZFactory:
    def __init__(self, app):
        self.app = app

    def create_action(self, name, callback):
        """ Add an Action and connect to a callback """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.app.add_action(action)

    def create_button(self, icon_name, title, callback=None, width=32, height=32, css_classes=['flat'], data=None):
        if len(icon_name.strip()) == 0:
            button = Gtk.Button(css_classes=css_classes)
            button.set_label(title)
            button.set_valign(Gtk.Align.CENTER)
        else:
            button = Gtk.Button(
                css_classes=css_classes,
                child=Adw.ButtonContent(
                    label=title,
                    icon_name=icon_name
                    )
                )
        # ~ button.get_style_context().add_class(class_name='success')
        button.set_has_frame(True)
        if callback is None:
            button.connect('clicked', self.noop, data)
        else:
            button.connect('clicked', callback, data)
        return button

    def create_dialog(self, parent, title, widget, width=-1, height=-1):
        dialog = Gtk.Dialog()
        dlgHeader = Gtk.HeaderBar()
        dialog.set_titlebar(dlgHeader)
        dialog.set_modal(True)
        dialog.set_title(title)
        if width != -1 and height != -1:
            dialog.set_size_request(width, height)
        dialog.set_transient_for(parent)
        contents = dialog.get_content_area()
        contents.set_margin_top(margin=12)
        contents.set_margin_end(margin=12)
        contents.set_margin_bottom(margin=12)
        contents.set_margin_start(margin=12)
        contents.append(widget)
        return dialog

    def create_dialog_question(self, parent, title, body, width=-1, height=-1):
        dialog = self.create_dialog(parent, title, body, width, height)
        dialog.add_buttons('No', Gtk.ResponseType.NO, 'Yes', Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.YES)
        btnYes = dialog.get_widget_for_response(Gtk.ResponseType.YES)
        btnYes.get_style_context().add_class(class_name='suggested-action')
        btnNo = dialog.get_widget_for_response(Gtk.ResponseType.NO)
        btnNo.get_style_context().add_class(class_name='destructive-action')
        return dialog

    def create_switch_button(self, icon_name, title, callback):
        button = Gtk.Switch()
        button.connect('activate', callback)
        return button

    def noop(self, *args):
        self.log.debug(args)