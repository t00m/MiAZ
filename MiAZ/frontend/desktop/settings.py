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
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZPeople


class MiAZAppSettings(Gtk.Box):
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZAppSettings')
        self.app = app
        self.factory = self.app.get_factory()
        self.config = self.app.get_config('App')
        page = Adw.PreferencesPage.new()
        page.set_title("Settings")
        page.add(self._get_group_repositories())
        self.repo_is_set = False
        self.append(page)

    def _get_group_repositories(self):
        self.row_repo_source = self._create_action_row_repo_source()
        group = Adw.PreferencesGroup()
        group.set_title("Document repositories")
        group.add(self.row_repo_source)
        return group

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
        btnRepoSource = self.factory.create_button('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        row = self.factory.create_actionrow(title=title, subtitle=subtitle, suffix=btnRepoSource)
        return row

    def _update_action_row_repo_source(self, name, dirpath):
        self.row_repo_source.set_title(name)
        self.row_repo_source.set_subtitle(dirpath)
        self.repo_is_set = True

    def is_repo_set(self):
        return self.repo_is_set

    def show_filechooser_source(self, *args):
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title='Choose target directory',
                    target = 'FOLDER',
                    callback = self.on_filechooser_response_source
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response):
        dialog.destroy()
        return


class MiAZRepoSettings(Gtk.Box):
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZRepoSettings')
        self.app = app
        self.factory = self.app.get_factory()
        self.config = self.app.get_config('App')
        self.notebook = Gtk.Notebook()
        self.append(self.notebook)
