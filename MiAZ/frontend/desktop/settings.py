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
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZSubgroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZOrganizations


class MiAZPrefsWindow(Adw.PreferencesWindow):
    def __init__(self, app):
        self.log = get_logger('MiAZ.Desktop.Settings')
        self.app = app
        self.factory = self.app.get_factory()
        self.config = self.app.get_config('App')
        self.win = self.app.win
        self.sm = self.app.get_style_manager()
        self.color_scheme = self.sm.get_color_scheme()
        super().__init__(title='Preferences')
        self.set_transient_for(self.app.win)
        page = Adw.PreferencesPage.new()
        page.set_title("Preferences")
        page.add(self.get_group_repositories())
        page.add(self.get_group_resources())
        self.add(page)
        self.show()

    def get_group_repositories(self):
        self.row_repo_source = self.create_action_row_repo_source()
        group = Adw.PreferencesGroup()
        group.set_title("Documents repository")
        group.add(self.row_repo_source)
        return group

    def get_group_resources(self):
        row_res_countries = self.create_action_row_res_countries()
        row_res_groups = self.create_action_row_res_groups()
        row_res_subgroups = self.create_action_row_res_subgroups()
        row_res_purposes = self.create_action_row_res_purposes()
        row_res_organizations = self.create_action_row_res_organizations()

        group = Adw.PreferencesGroup()
        group.set_title("Resources")
        group.add(row_res_countries)
        group.add(row_res_groups)
        group.add(row_res_subgroups)
        group.add(row_res_purposes)
        group.add(row_res_organizations)
        return group

    def create_action_row_res_countries(self):
        row = Adw.ActionRow.new()
        row.set_title("Countries")
        row.set_icon_name('miaz-res-country')
        button = self.factory.create_button('miaz-search', '', self.show_res_countries)
        box = row.get_child()
        box.append(button)
        return row

    def create_action_row_res_groups(self):
        row = Adw.ActionRow.new()
        row.set_title("Groups")
        row.set_icon_name('miaz-res-group')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_groups)
        box = row.get_child()
        box.append(button)
        return row

    def create_action_row_res_subgroups(self):
        row = Adw.ActionRow.new()
        row.set_title("Subgroups")
        row.set_icon_name('miaz-res-subgroup')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_subgroups)
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

    def show_res_countries(self, *args):
        view = MiAZCountries(self.app)
        view.update()
        dialog = self.factory.create_dialog(self, 'Countries', view, 600, 480)
        dialog.show()

    def show_res_groups(self, *args):
        view = MiAZGroups(self.app)
        view.update()
        dialog = self.factory.create_dialog(self.app.win, 'Groups', view, 600, 480)
        dialog.show()

    def show_res_subgroups(self, *args):
        view = MiAZSubgroups(self.app)
        view.update()
        dialog = self.factory.create_dialog(self.app.win, 'Subgroups', view, 600, 480)
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

    def create_action_row_repo_source(self):
        row = Adw.ActionRow.new()
        config = self.app.get_config('App')
        repo = config.get('source')
        if os.path.isdir(repo):
            title = os.path.basename(repo)
            subtitle = repo
        else:
            title = '<i>Folder not set</i>'
            subtitle = ''
        row.set_title(title)
        row.set_subtitle(subtitle)
        btnRepoSource = self.factory.create_button ('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        btnRepoSource.set_valign(Gtk.Align.CENTER)
        row.set_icon_name('folder-symbolic')
        row.add_suffix(widget=btnRepoSource)
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

    def filechooser_response_source(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                self.row_repo_source.set_title(os.path.basename(dirpath))
                self.row_repo_source.set_subtitle(dirpath)
                self.config.set('source', dirpath)
                backend = self.app.get_backend()
                watcher = backend.get_watcher_source()
                watcher.set_path(dirpath)
                watcher.set_active(True)
                dialog.destroy()
        else:
            dialog.destroy()


