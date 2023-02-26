#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
# ~ import sys
# ~ import json

import gi
from gi.repository import Adw
# ~ from gi.repository.GdkPixbuf import Pixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories

from MiAZ.backend.models import MiAZItem, File, Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy, SentTo, Date
from MiAZ.backend.models import Extension, Project, Repository

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Project'] = MiAZProjects
# ~ Configview['Date'] = Gtk.Calendar

class MiAZAppSettings(Gtk.Box):
    __gtype_name__ = 'MiAZAppSettings'
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=12, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZAppSettings')
        self.app = app
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
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
        # ~ btnRepoSource = self.factory.create_button('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        btnRepoSource = self.factory.create_button('document-edit-symbolic', '', self.actions.manage_resource, css_classes=['flat'], data=MiAZRepositories(self.app))
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
                    callback = self.on_filechooser_response_source,
                    data = None
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response, data):
        dialog.destroy()
        return


class MiAZRepoSettings(Gtk.Box):
    __gtype_name__ = 'MiAZRepoSettings'
    def __init__(self, app):
        super(Gtk.Box, self).__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.log = get_logger('MiAZRepoSettings')
        self.app = app
        self.factory = self.app.get_factory()
        self.config = self.app.get_config('Country')
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_border(False)
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.append(self.notebook)

        def create_tab(name):
            page = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            page.set_vexpand(True)
            page.set_hexpand(True)
            selector = Configview[name](self.app)
            selector.set_vexpand(True)
            selector.update()
            box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
            box.append(selector)
            page.set_start_widget(box)
            wdgLabel = self.factory.create_box_horizontal()
            icon = self.app.icman.get_image_by_name('miaz-res-%s' % name.lower())
            label = self.factory.create_label(name)
            label.set_hexpand(True)
            # ~ label.set_vexpand(True)
            wdgLabel.append(icon)
            wdgLabel.append(label)
            wdgLabel.set_hexpand(True)
            # ~ wdgLabel.set_vexpand(True)
            return page, wdgLabel

        for item in ['Country', 'Group', 'Purpose', 'Project', 'SentBy', 'SentTo']:
            page, label = create_tab(item)
            self.notebook.append_page(page, label)


