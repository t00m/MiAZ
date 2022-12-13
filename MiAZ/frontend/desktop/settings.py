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
        page.add(self._get_group_repositories())
        page.add(self._get_group_resources())
        self.add(page)
        # ~ self.show()

    def _get_group_repositories(self):
        self.row_repo_source = self._create_action_row_repo_source()
        group = Adw.PreferencesGroup()
        group.set_title("Documents repository")
        group.add(self.row_repo_source)
        return group

    def _get_group_resources(self):
        row_res_countries = self._create_action_row_res_countries()
        row_res_groups = self._create_action_row_res_groups()
        row_res_subgroups = self._create_action_row_res_subgroups()
        row_res_purposes = self._create_action_row_res_purposes()
        row_res_organizations = self._create_action_row_res_organizations()

        group = Adw.PreferencesGroup()
        group.set_title("Resources")
        group.add(row_res_countries)
        group.add(row_res_groups)
        group.add(row_res_subgroups)
        group.add(row_res_purposes)
        group.add(row_res_organizations)
        return group

    def _create_action_row_res_countries(self):
        row = Adw.ActionRow.new()
        row.set_title("Countries")
        row.set_icon_name('miaz-res-country')
        button = self.factory.create_button('miaz-search', '', self.show_res_countries)
        box = row.get_child()
        box.append(button)
        return row

    def _create_action_row_res_groups(self):
        row = Adw.ActionRow.new()
        row.set_title("Groups")
        row.set_icon_name('miaz-res-group')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_groups)
        box = row.get_child()
        box.append(button)
        return row

    def _create_action_row_res_subgroups(self):
        row = Adw.ActionRow.new()
        row.set_title("Subgroups")
        row.set_icon_name('miaz-res-subgroup')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_subgroups)
        box = row.get_child()
        box.append(button)
        return row

    def _create_action_row_res_purposes(self):
        row = Adw.ActionRow.new()
        row.set_title("Purposes")
        row.set_icon_name('miaz-res-purpose')
        button = self.factory.create_button('document-edit-symbolic', '', self.show_res_purposes)
        box = row.get_child()
        box.append(button)
        return row

    def _create_action_row_res_organizations(self):
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

    def _create_action_row_repo_source(self):
        row = Adw.ActionRow.new()
        config = self.app.get_config('App')
        repo = config.get('source')
        if os.path.isdir(repo):
            title = os.path.basename(repo)
            subtitle = repo
        else:
            title = '<i>Folder not set</i>'
            subtitle = 'Choose an empty folder'
        row.set_title(title)
        row.set_subtitle(subtitle)
        btnRepoSource = self.factory.create_button ('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        btnRepoSource.set_valign(Gtk.Align.CENTER)
        row.set_icon_name('folder-symbolic')
        row.add_suffix(widget=btnRepoSource)
        return row

    def show_filechooser_source(self, *args):
        filechooser = self.factory.create_filechooser(
                    parent=self,
                    title='Choose target directory',
                    target = 'FOLDER',
                    callback = self.on_filechooser_response_source
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response):
        backend = self.app.get_backend()
        use_repo = False
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_last_child()
            gfile = filechooser.get_file()
            dirpath = gfile.get_path()
            if dirpath is not None:
                if backend.is_repo(dirpath):
                    self.log.debug("Directory '%s' is a MiAZ Repository", dirpath)
                    watcher = backend.get_watcher_source()
                    watcher.set_path(dirpath)
                    watcher.set_active(True)
                    self.config.set('source', dirpath)
                    use_repo = True
                else:
                    self.log.debug("Directory '%s' is not a MiAZ repository", dirpath)
                    import glob
                    normal_files = glob.glob(os.path.join(dirpath, '*'))
                    hidden_files = glob.glob(os.path.join(dirpath, '.*'))
                    if len(normal_files) == 0 and len(hidden_files) == 0:
                        self.log.debug("Initializing repository for directory '%s'", dirpath)
                        backend.init_repo(dirpath)
                        use_repo = True
                    else:
                        self.log.warning("Directory '%s' can't be used as repository. It is not empty", dirpath)
            if use_repo:
                self.row_repo_source.set_title(os.path.basename(dirpath))
                self.row_repo_source.set_subtitle(dirpath)
                backend.load_repo(dirpath)
                self.app.setup_workspace_page()

        dialog.destroy()


