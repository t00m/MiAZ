#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json

import gi
from gi.repository import Adw
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.collections import MiAZCollections
from MiAZ.frontend.desktop.widgets.purposes import MiAZPurposes
from MiAZ.frontend.desktop.widgets.countries import MiAZCountries
from MiAZ.frontend.desktop.widgets.languages import MiAZLanguages
from MiAZ.frontend.desktop.widgets.extensions import MiAZExtensions
from MiAZ.frontend.desktop.widgets.organizations import MiAZOrganizations


class MiAZPrefsWindow(Adw.PreferencesWindow):
    def __init__(self, app):
        self.log = get_logger('MiAZ.Desktop.Settings')
        self.app = app
        self.factory = self.app.get_factory()
        self.config = self.app.get_config('app')
        self.win = self.app.win
        self.sm = self.app.get_style_manager()
        self.color_scheme = self.sm.get_color_scheme()
        super().__init__(title='Preferences')
        self.connect('close-request', self.on_window_close)
        self.set_transient_for(self.app.win)
        page = Adw.PreferencesPage.new()
        page.set_title("Preferences")
        page.add(self.get_group_repositories())
        page.add(self.get_group_resources())
        page.add(self.get_group_appearance())
        self.add(page)
        self.show()

    def get_group_repositories(self):
        self.row_repo_source = self.create_action_row_repo_source()
        self.row_repo_target = self.create_action_row_repo_target()

        group = Adw.PreferencesGroup()
        group.set_title("Repositories")
        group.add(self.row_repo_source)
        group.add(self.row_repo_target)
        return group

    def get_group_resources(self):
        row_res_countries = self.create_action_row_res_countries()
        row_res_collections = self.create_action_row_res_collections()
        row_res_purposes = self.create_action_row_res_purposes()
        row_res_organizations = self.create_action_row_res_organizations()
        row_res_extensions = self.create_action_row_res_extensions()

        group = Adw.PreferencesGroup()
        group.set_title("Resources")
        group.add(row_res_countries)
        group.add(row_res_collections)
        group.add(row_res_purposes)
        group.add(row_res_organizations)
        group.add(row_res_extensions)
        return group

    def get_group_appearance(self):
        row_repo_theme = self.create_action_row_gui_theme()
        group = Adw.PreferencesGroup()
        group.set_title("Appearance")
        group.add(row_repo_theme)
        return group

    def create_action_row_gui_theme(self):
        switch = Gtk.Switch.new()
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect('notify::active', self.on_theme_switched)
        row = Adw.ActionRow.new()
        row.set_title("Dark mode theme")
        row.set_icon_name('miaz-theme')
        button = self.factory.create_switch_button('', '', self.on_theme_switched)
        is_dark = self.color_scheme == self.sm.get_dark()
        button.set_active(is_dark)
        row.add_suffix(widget=switch)
        return row

    def on_theme_switched(self, switch, state):
        print("State: %s" % state)
        if state is True:
            self.sm.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            self.sm.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

    def create_action_row_res_countries(self):
        row = Adw.ActionRow.new()
        row.get_style_context().add_class(class_name='error')
        row.set_title("Countries")
        row.set_icon_name('miaz-res-country')
        button = self.factory.create_button('miaz-search', '', self.show_res_countries)
        box = row.get_child()
        box.append(button)
        return row

    def create_action_row_res_collections(self):
        row = Adw.ActionRow.new()
        row.set_title("Collections")
        row.set_icon_name('miaz-res-collection')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_collections)
        box = row.get_child()
        box.append(button)
        return row

    def create_action_row_res_purposes(self):
        row = Adw.ActionRow.new()
        row.set_title("Purposes")
        row.set_icon_name('miaz-res-purpose')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_purposes)
        box = row.get_child()
        box.append(button)
        return row

    def create_action_row_res_organizations(self):
        row = Adw.ActionRow.new()
        row.set_title("Organizations")
        row.set_icon_name('miaz-res-organization')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_organizations)
        box = row.get_child()
        box.append(button)
        return row

    def create_action_row_res_extensions(self):
        row = Adw.ActionRow.new()
        row.set_title("Extensions")
        row.set_icon_name('miaz-res-extension')
        button = self.factory.create_button('miaz-search', '', self.show_res_extensions)
        box = row.get_child()
        box.append(button)
        return row

    def show_res_countries(self, *args):
        view = MiAZCountries(self.app)
        view.update()
        dialog = self.factory.create_dialog(self, 'Countries', view, 600, 480)
        dialog.show()

    def show_res_collections(self, *args):
        view = MiAZCollections(self.app)
        view.update()
        dialog = self.factory.create_dialog(self.app.win, 'Collections', view, 600, 480)
        dialog.show()

    def show_res_purposes(self, *args):
        view = MiAZPurposes(self.app)
        view.update()
        dialog = self.factory.create_dialog(self.app.win, 'Purposes', view, 600, 480)
        dialog.show()

    def show_res_organizations(self, *args):
        view = MiAZOrganizations(self.app)
        view.update()
        dialog = self.factory.create_dialog(self.app.win, 'Organizations', view, 600, 480)
        dialog.show()

    def show_res_extensions(self, *args):
        view = MiAZExtensions(self.app)
        view.update()
        dialog = self.factory.create_dialog(self.app.win, 'Extensions', view, 600, 480)
        dialog.show()

    def create_action_row_repo_source(self):
        config = self.app.get_config('app')
        source = config.get('source')
        if source is None:
            source = '<i>Folder not set</i>'
        btnRepoSource = self.factory.create_button ('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        btnRepoSource.set_valign(Gtk.Align.CENTER)
        row = Adw.ActionRow.new()
        row.get_style_context().add_class(class_name='error')
        row.set_title("Source")
        row.set_subtitle(source)
        row.set_icon_name('folder-symbolic')
        row.add_suffix(widget=btnRepoSource)
        return row

    def create_action_row_repo_target(self):
        config = self.app.get_config('app')
        target = config.get('target')
        if target is None:
            target = '<i>Folder not set</i>'
        row = Adw.ActionRow.new()
        row.get_style_context().add_class(class_name='warning')
        row.set_title("Target")
        row.set_subtitle(target)
        row.set_icon_name('folder-symbolic')
        boxRepoTargetButton = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btnRepoTarget = self.factory.create_button ('document-edit-symbolic', '', self.show_filechooser_target, css_classes=['flat'])
        btnRepoTarget.set_valign(Gtk.Align.CENTER)
        btnRepoTarget.set_hexpand(False)
        box = row.get_child()
        box.append(btnRepoTarget)
        return row

    def show_filechooser_source(self, *args):
        dlgFileChooser = Gtk.Dialog()
        dlgFileChooser.set_transient_for(self)
        dlgFileChooser.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Accept', Gtk.ResponseType.ACCEPT)
        dlgFileChooser.connect('response', self.filechooser_response_source)
        contents = dlgFileChooser.get_content_area()
        wdgfilechooser = Gtk.FileChooserWidget()
        wdgfilechooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        contents.append(wdgfilechooser)
        dlgFileChooser.show()

    def show_filechooser_target(self, *args):
        dlgFileChooser = Gtk.Dialog()
        dlgFileChooser.set_transient_for(self)
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
                self.row_repo_source.set_title(dirpath)
                self.config.set('source', dirpath)
                backend = self.app.get_backend()
                watcher = backend.get_watcher_source()
                watcher.set_path(dirpath)
                watcher.set_active(True)
                dialog.destroy()
                self.app.check_basic_settings()
        else:
            dialog.destroy()

    def filechooser_response_target(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.row_repo_target.set_title(dirpath)
                backend = self.app.get_backend()
                watcher = backend.get_watcher_target()
                watcher.set_path(dirpath)
                watcher.set_active(True)
                self.config.set('target', dirpath)
                dialog.destroy()
                self.app.check_basic_settings()
        else:
            dialog.destroy()

    def create_section_repository(self):
        boxRepository = Gtk.Box(spacing = 24, orientation=Gtk.Orientation.VERTICAL)
        boxRepository.set_hexpand(True)
        boxRepository.set_margin_top(margin=24)
        boxRepository.set_margin_end(margin=12)
        boxRepository.set_margin_bottom(margin=12)
        boxRepository.set_margin_start(margin=12)

        # Source box
        boxRepoSource = Gtk.Box(spacing=12, orientation=Gtk.Orientation.HORIZONTAL)
        boxRepoSource.set_hexpand(True)
        lblRepoSourceTitle = Gtk.Label()
        lblRepoSourceTitle.set_markup("<b>Source</b>")
        boxRepoSource.append(lblRepoSourceTitle)
        boxRepoSourceButton = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        btnRepoSource = self.factory.create_button ('miaz-folder', '', self.show_filechooser_source)
        btnRepoSource.set_hexpand(False)
        try:
            source = self.app.config.get('source')
        except:
            source = '<i>Folder not set</i>'
        self.lblRepoSource = Gtk.Label()
        self.lblRepoSource.set_markup(source)
        boxRepoSourceButton.append(btnRepoSource)
        boxRepoSourceButton.append(self.lblRepoSource)
        boxRepoSource.append(boxRepoSourceButton)
        boxRepository.append(boxRepoSource)

        # Target box
        boxRepoTarget = Gtk.Box(spacing=12, orientation=Gtk.Orientation.HORIZONTAL)
        boxRepoTarget.set_hexpand(True)
        lblRepoTargetTitle = Gtk.Label()
        lblRepoTargetTitle.set_markup("<b>Target</b>")
        boxRepoTarget.append(lblRepoTargetTitle)
        boxRepoTargetButton = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        btnRepoTarget = self.factory.create_button ('miaz-folder', '', self.show_filechooser_target)
        btnRepoTarget.set_hexpand(False)

        try:
            target = self.app.config.get('target')
        except:
            target = '<i>Folder not set</i>'
        self.lblRepoTarget = Gtk.Label()
        self.lblRepoTarget.set_markup(target)
        boxRepoTargetButton.append(btnRepoTarget)
        boxRepoTargetButton.append(self.lblRepoTarget)
        boxRepoTarget.append(boxRepoTargetButton)
        boxRepository.append(boxRepoTarget)

        return boxRepository

    def on_window_close(self, *args):
        # ~ self.destroy()
        self.log.debug("Checking new settings")
        self.app.check_basic_settings()
        # ~ self.app.win.present()
