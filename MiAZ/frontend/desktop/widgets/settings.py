#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json

import gi
from gi.repository import Gtk, Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.collections import MiAZCollections
from MiAZ.frontend.desktop.widgets.purposes import MiAZPurposes
from MiAZ.frontend.desktop.widgets.countries import MiAZCountries
from MiAZ.frontend.desktop.widgets.languages import MiAZLanguages
from MiAZ.frontend.desktop.widgets.extensions import MiAZExtensions
from MiAZ.frontend.desktop.widgets.organizations import MiAZOrganizations
from MiAZ.frontend.desktop.widgets.who import MiAZWho

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

        ## Defaults
        section_resources = self.create_section_resources()
        self.flowbox.insert(widget=section_resources, position=2)

        ## Backup & Restore
        section_bckres = self.create_section_bckres()
        self.flowbox.insert(widget=section_bckres, position=3)

        ## Appearance
        section_appearance = self.create_section_appearance()
        self.flowbox.insert(widget=section_appearance, position=4)

        # ~ self.log.debug("Settings view initialited")

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

    def create_section_repository(self):
        frmRepository = Gtk.Frame()
        lblSectionTitle = Gtk.Label()
        lblSectionTitle.set_markup("<big><b>Repositories</b></big>")
        frmRepository.set_label_widget(lblSectionTitle)
        boxRepository = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.HORIZONTAL)
        boxRepository.set_hexpand(True)
        boxRepository.set_margin_top(margin=24)
        boxRepository.set_margin_end(margin=12)
        boxRepository.set_margin_bottom(margin=12)
        boxRepository.set_margin_start(margin=12)

        # Source box
        boxRepoSource = Gtk.Box(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        boxRepoSource.set_hexpand(True)
        lblRepoSourceTitle = Gtk.Label()
        lblRepoSourceTitle.set_markup("<b>Source</b>")
        boxRepoSource.append(lblRepoSourceTitle)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        boxRepoSource.append(separator)
        boxRepoSourceButton = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        btnRepoSource = self.gui.create_button ('miaz-folder', '', self.show_filechooser_source)
        btnRepoSource.set_hexpand(False)
        # ~ btnRepoSource.set_has_frame(True)
        try:
            source = self.gui.config.get('source')
        except:
            source = '<i>Folder not set</i>'
        self.lblRepoSource = Gtk.Label()
        self.lblRepoSource.set_markup(source)
        boxRepoSourceButton.append(btnRepoSource)
        boxRepoSourceButton.append(self.lblRepoSource)
        boxRepoSource.append(boxRepoSourceButton)
        boxRepository.append(boxRepoSource)

        # Target box
        boxRepoTarget = Gtk.Box(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        boxRepoTarget.set_hexpand(True)
        lblRepoTargetTitle = Gtk.Label()
        lblRepoTargetTitle.set_markup("<b>Target</b>")
        boxRepoTarget.append(lblRepoTargetTitle)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        boxRepoTarget.append(separator)
        boxRepoTargetButton = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        btnRepoTarget = self.gui.create_button ('miaz-folder', '', self.show_filechooser_target)
        btnRepoTarget.set_hexpand(False)
        # ~ btnRepoTarget.set_has_frame(True)
        try:
            target = self.gui.config.get('target')
        except:
            target = '<i>Folder not set</i>'
        self.lblRepoTarget = Gtk.Label()
        self.lblRepoTarget.set_markup(target)
        boxRepoTargetButton.append(btnRepoTarget)
        boxRepoTargetButton.append(self.lblRepoTarget)
        boxRepoTarget.append(boxRepoTargetButton)
        boxRepository.append(boxRepoTarget)

        frmRepository.set_child(boxRepository)

        return frmRepository

    def create_section_resources(self):
        frmResources = Gtk.Frame()
        lblSectionTitle = Gtk.Label()
        lblSectionTitle.set_markup("<big><b>Resources</b></big>")
        frmResources.set_label_widget(lblSectionTitle)
        hbox_resources = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.HORIZONTAL)
        hbox_resources.set_margin_top(margin=24)
        hbox_resources.set_margin_end(margin=12)
        hbox_resources.set_margin_bottom(margin=12)
        hbox_resources.set_margin_start(margin=12)
        hbox_resources.set_homogeneous(True)

        flowbox = Gtk.FlowBox.new()
        flowbox.set_margin_top(margin=24)
        flowbox.set_margin_end(margin=12)
        flowbox.set_margin_bottom(margin=24)
        flowbox.set_margin_start(margin=12)
        flowbox.set_valign(align=Gtk.Align.START)
        flowbox.set_max_children_per_line(n_children=3)
        flowbox.set_selection_mode(mode=Gtk.SelectionMode.NONE)

        n = 0
        button = self.gui.create_button ('countries', 'Countries', self.show_res_countries)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=n)
        n += 1

        # ~ button = self.gui.create_button ('languages', 'Languages', self.show_res_languages)
        # ~ button.set_has_frame(True)
        # ~ flowbox.insert(widget=button, position=1)

        button = self.gui.create_button ('collections', 'Collections', self.show_res_collections)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=n)
        n += 1

        button = self.gui.create_button ('purposes', 'Purposes', self.show_res_purposes)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=n)
        n += 1

        button = self.gui.create_button ('organizations', 'Organizations', self.show_res_organizations)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=n)
        n += 1

        button = self.gui.create_button ('who', 'Who', self.show_res_who)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=5)
        n += 1

        button = self.gui.create_button ('extensions', 'File extensions', self.show_res_extensions)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=6)
        n += 1

        frmResources.set_child(flowbox)
        return frmResources

    def create_section_bckres(self):
        frmBckRes = Gtk.Frame()
        hbox_bckres = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.HORIZONTAL)
        hbox_bckres.set_margin_top(margin=24)
        hbox_bckres.set_margin_end(margin=12)
        hbox_bckres.set_margin_bottom(margin=12)
        hbox_bckres.set_margin_start(margin=12)
        hbox_bckres.set_homogeneous(True)

        flowbox = Gtk.FlowBox.new()
        flowbox.set_margin_top(margin=24)
        flowbox.set_margin_end(margin=12)
        flowbox.set_margin_bottom(margin=24)
        flowbox.set_margin_start(margin=12)
        flowbox.set_valign(align=Gtk.Align.START)
        flowbox.set_max_children_per_line(n_children=3)
        flowbox.set_selection_mode(mode=Gtk.SelectionMode.NONE)

        button = self.gui.create_button('miaz-backup', 'Backup', self.backup)
        # ~ button.set_has_frame(True)
        icon = self.gui.icman.get_image_by_name('miaz-backup', 128, 128)
        flowbox.insert(widget=icon, position=0)

        button = self.gui.create_button('miaz-restore', 'Restore', self.restore)
        # ~ button.set_has_frame(True)
        flowbox.insert(widget=button, position=1)

        lblFrmTitle = Gtk.Label()
        lblFrmTitle.set_markup("<b>Backup and Restore</b>")
        frmBckRes.set_label_widget(lblFrmTitle)
        frmBckRes.set_child(flowbox)
        return frmBckRes

    def show_res_countries(self, *args):
        view = MiAZCountries(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Countries', view, 600, 400)
        dialog.show()

    def show_res_languages(self, *args):
        view = MiAZLanguages(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Languages', view, 600, 400)
        dialog.show()

    def show_res_who(self, *args):
        view = MiAZWho(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, "Who's who", view, 600, 400)
        dialog.show()

    def show_res_collections(self, *args):
        view = MiAZCollections(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Collections', view)
        dialog.show()

    def show_res_purposes(self, *args):
        view = MiAZPurposes(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Purposes', view)
        dialog.show()

    def show_res_organizations(self, *args):
        view = MiAZOrganizations(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Organizations', view)
        dialog.show()

    def show_res_extensions(self, *args):
        view = MiAZExtensions(self.gui)
        view.update()
        dialog = self.gui.create_dialog(self.gui.win, 'Extensions', view)
        dialog.show()

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

    def show_filechooser_source(self, *args):
        dlgFileChooser = Gtk.Dialog()
        dlgFileChooser.set_transient_for(self.gui.win)
        dlgFileChooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        dlgFileChooser.connect('response', self.filechooser_response_source)
        contents = dlgFileChooser.get_content_area()
        wdgfilechooser = Gtk.FileChooserWidget()
        wdgfilechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        contents.append(wdgfilechooser)
        dlgFileChooser.show()

    def show_filechooser_target(self, *args):
        dlgFileChooser = Gtk.Dialog()
        dlgFileChooser.set_transient_for(self.gui.win)
        dlgFileChooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        dlgFileChooser.connect('response', self.filechooser_response_target)
        contents = dlgFileChooser.get_content_area()
        wdgfilechooser = Gtk.FileChooserWidget()
        wdgfilechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        contents.append(wdgfilechooser)
        dlgFileChooser.show()

    def filechooser_response_source(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.lblRepoSource.set_markup(dirpath)
                self.config.set('source', dirpath)
                dialog.destroy()
                self.gui.workspace.refresh_view()
        else:
            dialog.destroy()

    def filechooser_response_target(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.lblRepoTarget.set_markup(dirpath)
                self.config.set('target', dirpath)
                dialog.destroy()
                self.gui.workspace.refresh_view()
        else:
            dialog.destroy()

    def backup(self, *args):
        self.log.debug("MiAZ Backup")

    def restore(self, *args):
        self.log.debug("MiAZ Restore")
