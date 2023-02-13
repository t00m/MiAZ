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


class MiAZSettings(Gtk.Box):
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZ.Desktop.Settings')
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

        # ~ backend = self.app.get_backend()
        # ~ use_repo = False
        # ~ if response == Gtk.ResponseType.ACCEPT:
            # ~ content_area = dialog.get_content_area()
            # ~ filechooser = content_area.get_first_child()
            # ~ try:
                # ~ gfile = filechooser.get_file()
            # ~ except AttributeError as error:
                # ~ self.log.error(error)
                # ~ raise
            # ~ if gfile is None:
                # ~ self.log.debug("No directory set. Do nothing.")
                # ~ # FIXME: Show warning message. Priority: low
                # ~ return
            # ~ dirpath = gfile.get_path()
            # ~ if dirpath is not None:
                # ~ if backend.repo_validate(dirpath):
                    # ~ self.log.debug("Directory '%s' is a MiAZ Repository", dirpath)
                    # ~ use_repo = True
                # ~ else:
                    # ~ self.log.debug("Directory '%s' is not a MiAZ repository", dirpath)
                    # ~ import glob
                    # ~ normal_files = glob.glob(os.path.join(dirpath, '*'))
                    # ~ hidden_files = glob.glob(os.path.join(dirpath, '.*'))
                    # ~ if len(normal_files) == 0 and len(hidden_files) == 0:
                        # ~ self.log.debug("Initializing repository for directory '%s'", dirpath)
                        # ~ backend.repo_init(dirpath)
                        # ~ use_repo = True
                    # ~ else:
                        # ~ self.log.warning("Directory '%s' can't be used as repository. It is not empty", dirpath)
            # ~ if use_repo:
                # ~ self.config.set('source', dirpath)
                # ~ backend.repo_load(dirpath)
                # ~ self.app.setup_workspace_page()
                # ~ self._update_action_row_repo_source(os.path.basename(dirpath), dirpath)
                # ~ self.log.debug("Repo correctly setup")


