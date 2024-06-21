#!/usr/bin/python3
# File: filechooser.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom filechooser dialog

# FIXME: Gtk.FileChooser is deprecated. Use Gtk.FileDialog
# FIXME: Available since Gtk 4.10: https://docs.gtk.org/gtk4/class.FileDialog.html
# FIXME: However, Debian 12.5 is still in 4.8.3
# FIXME: Choosing Gtk.FileChooser for compatibility

from gettext import gettext as _

from gi.repository import Gtk


class MiAZFileChooserDialog(Gtk.Dialog):
    """Custom Filechooser Dialog"""
    def __init__(self, app, parent, title, target, callback, data=None):
        super(Gtk.Dialog, self).__init__()
        self.app = app
        self.parent = parent
        self.title = title
        self.target = target
        self.callback = callback
        self.data = data
        self.factory = self.app.get_service('factory')
        self.build_ui()

    def build_ui(self):
        self.set_margin_start(0)
        self.set_margin_end(0)
        self.set_margin_top(0)
        self.set_margin_bottom(0)
        self.set_title(self.title)
        self.set_transient_for(self.parent)
        self.set_modal(True)
        self.add_buttons(_('Cancel'), Gtk.ResponseType.CANCEL, _('Accept'), Gtk.ResponseType.ACCEPT)
        btnCancel = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
        btnCancel.get_style_context ().add_class ('destructive-action')
        btnAccept = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        btnAccept.get_style_context ().add_class ('suggested-action')
        action_box = btnCancel.get_ancestor(Gtk.Box)
        action_box.set_spacing(6)
        action_box.set_margin_start(6)
        action_box.set_margin_end(6)
        action_box.set_margin_top(6)
        action_box.set_margin_bottom(6)
        self.connect('response', self.callback, self.data)
        contents = self.get_content_area()
        box = self.factory.create_box_vertical()
        self.w_filechooser = Gtk.FileChooserWidget()
        box.append(self.w_filechooser)
        contents.append(box)
        if self.target == 'FOLDER':
            self.w_filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        elif self.target == 'FILE':
            self.w_filechooser.set_action(Gtk.FileChooserAction.OPEN)
        elif self.target == 'SAVE':
            self.w_filechooser.set_action(Gtk.FileChooserAction.SAVE)

    def get_filechooser_widget(self):
        return self.w_filechooser


