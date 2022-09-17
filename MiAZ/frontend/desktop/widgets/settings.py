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
from MiAZ.backend.log import get_logger

class MiAZSettings(Gtk.Box):
    """ Wrapper for Gtk.Stack with  with a StackSwitcher """

    def __init__(self, gui):
        super(MiAZSettings, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        self.gui = gui
        self.log = get_logger('MiAZ.GUI.Settings')
        self.config = gui.config
        self.set_vexpand(True)
        self.set_margin_top(margin=12)
        self.set_margin_end(margin=12)
        self.set_margin_bottom(margin=12)
        self.set_margin_start(margin=12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_vexpand(True)
        scrwin = Gtk.ScrolledWindow.new()
        scrwin.set_vexpand(True)
        box.append(child=scrwin)
        self.flowbox = Gtk.FlowBox.new()
        self.flowbox.set_margin_top(margin=12)
        self.flowbox.set_margin_end(margin=12)
        self.flowbox.set_margin_bottom(margin=12)
        self.flowbox.set_margin_start(margin=12)
        self.flowbox.set_valign(align=Gtk.Align.START)
        self.flowbox.set_max_children_per_line(n_children=1)
        self.flowbox.set_selection_mode(mode=Gtk.SelectionMode.NONE)
        scrwin.set_child(child=self.flowbox)
        self.append(box)

        # Sections
        ## Repository
        section_repository = self.create_section_repository()
        self.flowbox.insert(widget=section_repository, position=0)

        ## Appearance
        section_appearance = self.create_section_appearance()
        self.flowbox.insert(widget=section_appearance, position=1)

    def create_section_appearance(self):
        frmAppearance = Gtk.Frame()
        self.sm = self.gui.get_style_manager()
        self.color_scheme = self.sm.get_color_scheme()
        is_dark = self.color_scheme == self.sm.get_dark()
        hbox_darkmode = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.HORIZONTAL)
        hbox_darkmode.set_margin_top(margin=24)
        hbox_darkmode.set_margin_end(margin=12)
        hbox_darkmode.set_margin_bottom(margin=12)
        hbox_darkmode.set_margin_start(margin=12)
        button = Gtk.Switch()
        button.set_active(self.sm.get_dark())
        button.connect('state-set', self.darkmode_switched)
        hbox_darkmode.append(button)
        lblFrmTitle = Gtk.Label()
        lblFrmTitle.set_markup("<b>Appearance</b>")
        self.lblDarkMode = Gtk.Label()
        self.lblDarkMode.set_markup("<b>Switch Dark mode</b>")
        hbox_darkmode.append(self.lblDarkMode)
        frmAppearance.set_label_widget(lblFrmTitle)
        frmAppearance.set_child(hbox_darkmode)
        return frmAppearance


        self.log.debug("Settings view initialited")

    def create_section_repository(self):
        frmRepository = Gtk.Frame()
        hbox_filechooser = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.HORIZONTAL)
        hbox_filechooser.set_margin_top(margin=24)
        hbox_filechooser.set_margin_end(margin=12)
        hbox_filechooser.set_margin_bottom(margin=12)
        hbox_filechooser.set_margin_start(margin=12)
        button = self.gui.create_button ('folder', 'Select repository folder', self.filechooser_show)
        button.set_has_frame(True)
        hbox_filechooser.append(button)
        lblFrmTitle = Gtk.Label()
        lblFrmTitle.set_markup("<b>Repository</b>")
        self.lblRepository = Gtk.Label()
        self.lblRepository.set_markup("<b>Current location</b>: %s" % self.gui.config.get('source'))
        hbox_filechooser.append(self.lblRepository)
        frmRepository.set_label_widget(lblFrmTitle)
        frmRepository.set_child(hbox_filechooser)
        return frmRepository

    def darkmode_switched(self, switch, state):
        if state is True:
            self.sm.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            self.sm.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

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
                self.lblRepository.set_markup("<b>Current location</b>: %s" % dirpath)
                self.config.set('source', dirpath)
                dialog.destroy()
                self.gui.workspace.refresh_view()
        else:
            dialog.destroy()
