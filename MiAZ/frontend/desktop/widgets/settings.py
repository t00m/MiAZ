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
        # ~ self.set_default_size(600, 480)
        # ~ self.set_title('Settings')
        self.gui = gui
        self.log = gui.log
        self.config = gui.config
        # ~ self.set_transient_for(self.gui.win)
        # ~ self.set_modal(self)
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_bottom(margin=12)
        self.set_margin_start(margin=12)
        self.log.debug("MiAZSettings")
        # ~ self.connect("response", self.open_response)

        # ~ self.header = Gtk.HeaderBar()
        # ~ self.set_titlebar(self.header)
        # ~ label = Gtk.Label()
        # ~ label.set_markup('<b>Settings</b>')
        # ~ self.header.set_title_widget(label)

        # Add Refresh button to the titlebar (Left side)
        # ~ button = Gtk.Button.new_from_icon_name('preferences-system')
        # ~ icon = Gtk.Image.new_from_icon_name('preferences-system')
        # ~ self.header.pack_start(icon)

        # Add Cancel & Accept buttons to the titlebar (right side)
        # ~ button = self.gui.create_button('', 'Accept', self.accept)
        # ~ self.header.pack_end(button)
        # ~ button = self.gui.create_button('', 'Cancel', self.cancel)
        # ~ self.header.pack_start(button)

        # ~ contents = self.get_content_area()
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
        hbox = Gtk.Box(spacing = 3, orientation=Gtk.Orientation.HORIZONTAL)
        button = self.gui.create_button ('folder', 'Select repository folder', self.show_filechooser)
        hbox.append(button)
        lblRepository = Gtk.Label()
        lblRepository.set_markup("<b>Repository</b>: %s" % self.gui.config.get('source'))
        hbox.append(lblRepository)

        # ~ self.dialog = Gtk.Dialog.new("Select documents directory", self.gui.win, Gtk.FileChooserAction.SELECT_FOLDER, 'Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        # ~ self.filechooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.SELECT_FOLDER)
        # ~ self.filechooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Select', Gtk.ResponseType.ACCEPT)
        # ~ self.filechooser.set_default_size(400, 300)
        # ~ self.filechooser.connect("response", self.select_source_directory)
        # ~ self.filechooser.set_transient_for(self)
        # ~ self.expander.set_child(self.filechooser)


        # ~ label = Gtk.Label()
        # ~ label.set_markup("<b>Select documents folder</b>")
        # ~ hbox.append(label)
        # ~ button = self.gui.create_button('folder', '<b>Select documents folder</b>', self.show_filechooser)
        # ~ hbox.append(button)
        # ~ try:
            # ~ self.lblsrcdir = Gtk.Label.new(self.config.get('source'))
        # ~ except KeyError:
            # ~ self.lblsrcdir = Gtk.Label.new('Source directory not set!')
        # ~ self.lblsrcdir.set_hexpand(True)
        # ~ hbox.append(self.expander)
        flowbox.insert(widget=hbox, position=0)
        for n in range(1,100):
            button = Gtk.Button.new_with_label(label=f'Botão {n}')
            flowbox.insert(widget=button, position=n)


        # ~ self.filechooser = Gtk.FileChooserWidget()
        # ~ self.filechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        # ~ contents.append(self.filechooser)

    def show_filechooser(self, *args):
        dlgFileChooser = Gtk.Dialog()
        dlgFileChooser.set_transient_for(self.gui.win)
        dlgFileChooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        dlgFileChooser.connect("response", self.open_response)
        contents = dlgFileChooser.get_content_area()
        wdgfilechooser = Gtk.FileChooserWidget()
        wdgfilechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        contents.append(wdgfilechooser)
        dlgFileChooser.show()

    def select_source_directory(self, dialog, response):
        self.log.debug("Hi!")
        if response == Gtk.ResponseType.ACCEPT:
            gdir = dialog.get_file()
            source_directory = gdir.get_path()
            self.config.set('source', source_directory)
            self.lblsrcdir.set_text(source_directory)
            self.log.info("Source directory: %s", source_directory)
        self.filechooser.destroy()

    def open_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.log.info(dirpath)
                self.config.set('source', dirpath)
                dialog.destroy()
                # ~ self.workspace.refresh_view()
        else:
            dialog.destroy()

    def accept(self, *args):
        self.log.info("Settings updated")

    def cancel(self, *args):
        self.close()
