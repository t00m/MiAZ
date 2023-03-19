#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: settings.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage App and Repository settings
"""

import os

import gi
from gi.repository import Adw
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
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy, SentTo, Date
from MiAZ.backend.models import Extension, Project, Repository
from MiAZ.backend.config import MiAZConfigRepositories

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
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.actions = self.app.get_actions()
        self.config = self.backend.conf
        page = Adw.PreferencesPage.new()
        page.set_title("Settings - Repositories")
        page.add(self._get_group_repositories())
        self.append(page)
        self.repo_is_set = False

    def _get_group_repositories(self):
        self.row_repo_source = self._create_action_row_repo_source()
        group = Adw.PreferencesGroup()
        group.set_title("Repositories")
        group.add(self.row_repo_source)
        return group

    def _create_action_row_repo_source(self):
        row = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        hbox = self.factory.create_box_horizontal()
        lblActive = Gtk.Label()
        lblActive.set_markup("Current active")
        self.dd_repo = self.factory.create_dropdown_generic(item_type=Repository, ellipsize=False, enable_search=False)
        btnUseRepo = self.factory.create_button(icon_name='MiAZ', callback=self._on_use_repo)
        hbox.append(lblActive)
        hbox.append(self.dd_repo)
        hbox.append(btnUseRepo)
        self.actions.dropdown_populate(MiAZConfigRepositories, self.dd_repo, Repository, any_value=False, none_value=False)
        self.dd_repo.connect("notify::selected-item", self._on_selected_repo)
        self.config['Repository'].connect('used-updated', self.actions.dropdown_populate, self.dd_repo, Repository, False, False)

        # Load last active repo
        repos_used = self.config['Repository'].load_used()
        self.log.debug("Repositories in use: %s", ','.join(repos_used.keys()))
        repo_active = self.config['App'].get('current')
        self.log.debug("Current active: %s", repo_active)
        if repo_active in repos_used:
            model = self.dd_repo.get_model()
            n = 0
            for item in model:
                if item.id == repo_active:
                    self.dd_repo.set_selected(n)
                n += 1
        row.append(hbox)
        configview = MiAZRepositories(self.app)
        configview.update()
        row.append(configview)
        return row

    def _on_use_repo(self, *args):
        self.log.debug(args)
        workspace = self.app.get_widget('workspace')
        workspace.update()
        self.app.show_stack_page_by_name('workspace')

    def _on_selected_repo(self, dropdown, gparamobj):
        try:
            repo_id = dropdown.get_selected_item().id
            repo_dir = dropdown.get_selected_item().title
            self.log.debug("Repository selected: %s[%s]", repo_id, repo_dir)
            self.config['App'].set('current', repo_id)
            self.app.check_repository()
        except AttributeError:
            # Probably the repository was removed from used view
            pass

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

        def create_tab(item_type):
            i_type = item_type.__gtype_name__
            i_title = item_type.__title__
            page = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            page.set_vexpand(True)
            page.set_hexpand(True)
            selector = Configview[i_type](self.app)
            selector.set_vexpand(True)
            selector.update()
            box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
            box.append(selector)
            page.set_start_widget(box)
            wdgLabel = self.factory.create_box_horizontal()
            icon = self.app.icman.get_image_by_name('miaz-res-%s' % i_type.lower())
            icon.set_hexpand(False)
            label = self.factory.create_label("<b>%s</b>" % i_title)
            label.set_xalign(0.0)
            label.set_hexpand(True)
            wdgLabel.append(icon)
            wdgLabel.append(label)
            wdgLabel.set_hexpand(True)
            return page, wdgLabel

        for item_type in [Country, Group, Purpose, Project, SentBy, SentTo]:
            page, label = create_tab(item_type)
            self.notebook.append_page(page, label)


