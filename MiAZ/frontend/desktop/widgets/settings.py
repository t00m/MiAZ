#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import gi
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV

class MiAZSettings(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, gui):
        super(MiAZSettings, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.gui = gui
        self.log = gui.log
        self.config = gui.config
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_bottom(margin=12)
        self.set_margin_start(margin=12)
        self.log.debug("MiAZSettings")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_vexpand(True)
        scrwin = Gtk.ScrolledWindow.new()
        scrwin.set_vexpand(True)
        box.append(child=scrwin)
        flowbox = Gtk.FlowBox.new()
        flowbox.set_margin_top(margin=12)
        flowbox.set_margin_end(margin=12)
        flowbox.set_margin_bottom(margin=12)
        flowbox.set_margin_start(margin=12)
        flowbox.set_valign(align=Gtk.Align.START)
        flowbox.set_max_children_per_line(n_children=1)
        flowbox.set_selection_mode(mode=Gtk.SelectionMode.NONE)
        scrwin.set_child(child=flowbox)
        self.append(box)

        # Setting buttons
        ## Select source directory
        hbox_filechooser = Gtk.Box(spacing = 3, orientation=Gtk.Orientation.HORIZONTAL)
        button = self.gui.create_button ('folder', 'Select repository folder', self.filechooser_show)
        hbox_filechooser.append(button)
        self.lblRepository = Gtk.Label()
        self.lblRepository.set_markup("<b>Repository</b>: %s" % self.gui.config.get('source'))
        hbox_filechooser.append(self.lblRepository)
        flowbox.insert(widget=hbox_filechooser, position=0)

    def filechooser_show(self, *args):
        dlgFileChooser = Gtk.Dialog()
        dlgFileChooser.set_transient_for(self.gui.win)
        dlgFileChooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        dlgFileChooser.connect("response", self.filechooser_response)
        contents = dlgFileChooser.get_content_area()
        wdgfilechooser = Gtk.FileChooserWidget()
        wdgfilechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        contents.append(wdgfilechooser)
        dlgFileChooser.show()

    def filechooser_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.lblRepository.set_markup("<b>Repository</b>: %s" % dirpath)
                self.config.set('source', dirpath)
                dialog.destroy()
                self.gui.workspace.refresh_view()
        else:
            dialog.destroy()
