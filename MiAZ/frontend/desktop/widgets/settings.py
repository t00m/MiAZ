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
from MiAZ.frontend.desktop.widgets.collections import MiAZCollections
from MiAZ.frontend.desktop.widgets.purposes import MiAZPurposes

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

        box = Gtk.Box(spacing=24, orientation=Gtk.Orientation.VERTICAL)
        box.set_vexpand(True)
        scrwin = Gtk.ScrolledWindow.new()
        scrwin.set_vexpand(True)
        box.append(child=scrwin)
        self.flowbox = Gtk.FlowBox.new()
        self.flowbox.set_margin_top(margin=24)
        self.flowbox.set_margin_end(margin=12)
        self.flowbox.set_margin_bottom(margin=24)
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

        ## Repository
        section_resources = self.create_section_resources()
        self.flowbox.insert(widget=section_resources, position=1)

        ## Appearance
        section_appearance = self.create_section_appearance()
        self.flowbox.insert(widget=section_appearance, position=2)

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
        button = self.gui.create_button ('folder', 'Select repository folder', self.show_filechooser)
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

    def create_section_resources(self):
        frmRepository = Gtk.Frame()
        hbox_resources = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.HORIZONTAL)
        hbox_resources.set_margin_top(margin=24)
        hbox_resources.set_margin_end(margin=12)
        hbox_resources.set_margin_bottom(margin=12)
        hbox_resources.set_margin_start(margin=12)
        hbox_resources.set_homogeneous(True)
        button = self.gui.create_button ('', 'Collections', self.show_res_collections)
        button.set_has_frame(True)
        hbox_resources.append(button)
        button = self.gui.create_button ('', 'Purposes', self.show_res_purposes)
        button.set_has_frame(True)
        hbox_resources.append(button)
        button = self.gui.create_button ('', 'Organizations', self.show_res_collections)
        button.set_has_frame(True)
        hbox_resources.append(button)
        button = self.gui.create_button ('', 'File extensions', self.show_res_collections)
        button.set_has_frame(True)
        hbox_resources.append(button)
        lblFrmTitle = Gtk.Label()
        lblFrmTitle.set_markup("<b>Manage resources</b>")
        # ~ self.lblRepository = Gtk.Label()
        # ~ self.lblRepository.set_markup("<b>Current location</b>: %s" % self.gui.config.get('source'))
        # ~ hbox_resources.append(self.lblRepository)
        frmRepository.set_label_widget(lblFrmTitle)
        frmRepository.set_child(hbox_resources)
        return frmRepository

    def show_res_collections(self, *args):
        view = MiAZCollections(self.gui)
        local_config = ENV['FILE']['COLLECTIONS']
        global_config = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-collections.json')
        view.set_config_files(local_config, global_config)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Collections', view)
        dialog.show()

    def show_res_purposes(self, *args):
        view = MiAZPurposes(self.gui)
        local_config = ENV['FILE']['PURPOSES']
        global_config = os.path.join(ENV['GPATH']['RESOURCES'], 'miaz-purposes.json')
        view.set_config_files(local_config, global_config)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Purposes', view)
        dialog.show()
        # ~ dlgPurposes = Gtk.Dialog()
        # ~ dlgHeader = Gtk.HeaderBar()
        # ~ dlgPurposes.set_titlebar(dlgHeader)
        # ~ dlgPurposes.set_modal(True)
        # ~ dlgPurposes.set_title('Purposes')
        # ~ dlgPurposes.set_size_request(400, 500)
        # ~ dlgPurposes.set_transient_for(self.gui.win)
        # ~ contents = dlgPurposes.get_content_area()
        # ~ wdgPurposes = MiAZPurposes(self.gui)
        # ~ contents.append(wdgPurposes)
        # ~ dlgPurposes.show()

    def collections_accept(self, *args):
        self.log.debug(args)

    def collections_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            self.log.debug("Collections updated")
        else:
            self.log.debug("Collections not updated")
        dialog.destroy()

    def darkmode_switched(self, switch, state):
        if state is True:
            self.sm.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            self.sm.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

    def show_filechooser(self, *args):
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
