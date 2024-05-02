#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
import tempfile
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import File
from MiAZ.backend.models import Project
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPeople
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Project'] = MiAZProjects
Configview['Date'] = Gtk.Calendar


class MiAZToolbarProjectMgtPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarProjectMgtPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.ProjectMgt')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_service('actions')
        self.backend = self.app.get_service('backend')
        self.factory = self.app.get_service('factory')
        self.util = self.app.get_service('util')
        self.projects = self.backend.projects
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-menu", self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def add_menuitem(self, *args):
        section_common_in = self.app.get_widget('workspace-menu-selection-section-common-in')
        if self.app.get_widget('workspace-menu-selection-menu-project') is None:
            submenu_project = Gio.Menu.new()
            menu_project = Gio.MenuItem.new_submenu(
                label = _('Project management...'),
                submenu = submenu_project,
            )
            section_common_in.append_item(menu_project)
            self.app.add_widget('workspace-menu-selection-menu-project', menu_project)
            self.app.add_widget('workspace-menu-selection-submenu-project', submenu_project)
            menuitem = self.factory.create_menuitem('project-assign', _('...assign project'), self.project_assign, None, [])
            submenu_project.append_item(menuitem)
            menuitem = self.factory.create_menuitem('project-withdraw', _('...withdraw project'), self.project_withdraw, None, [])
            submenu_project.append_item(menuitem)


    def project_assign(self, *args):
        item_type = Project
        items = self.workspace.get_selected_items()

        def dialog_response(dialog, response, dropdown, items):
            if response == Gtk.ResponseType.ACCEPT:
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                self.projects.add_batch(pid, docs)
                workspace = self.app.get_widget('workspace')
                workspace.update()
            dialog.destroy()

        self.config = self.backend.conf
        i_type = item_type.__gtype_name__
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = self.factory.create_dropdown_generic(Project)
        self.config[i_type].connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, False, False)
        self.actions.dropdown_populate(self.config[i_type], dropdown, Project, any_value=False)
        btnManage = self.factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', self.actions.manage_resource, Configview['Project'](self.app))
        label = self.factory.create_label(_('Assign the following documents to this project: '))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='caption')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in items:
            projects = ', '.join([self.projects.description(pid) for pid in self.projects.assigned_to(item.id)])
            citems.append(File(id=item.id, title="<b>%s</b>" % projects))
        cv.update(citems)
        frame.set_child(cv)
        hbox = self.factory.create_box_horizontal(hexpand=False, vexpand=False)
        hbox.append(label)
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, _('Assign to a project'), box, width=1024, height=600)
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.show()

    def project_withdraw(self, *args):
        item_type = Project
        items = self.workspace.get_selected_items()

        def dialog_response(dialog, response, dropdown, items):
            if response == Gtk.ResponseType.ACCEPT:
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                self.projects.remove_batch(pid, docs)
                workspace = self.app.get_widget('workspace')
                workspace.update()
            dialog.destroy()

        self.config = self.backend.conf
        i_type = item_type.__gtype_name__
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = self.factory.create_dropdown_generic(Project)
        self.config[i_type].connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, False, False)

        # Get projects
        projects = set()
        for item in items:
            for project in self.backend.projects.assigned_to(item.id):
                projects.add(project)

        self.actions.dropdown_populate(self.config[i_type], dropdown, Project, any_value=False, only_include=list(projects))
        btnManage = self.factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', self.actions.manage_resource, Configview['Project'](self.app))
        label = self.factory.create_label(_('Withdraw the following documents from this project: '))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='caption')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in items:
            projects = ', '.join([self.projects.description(pid) for pid in self.projects.assigned_to(item.id)])
            citems.append(File(id=item.id, title="<b>%s</b>" % projects))
        cv.update(citems)
        frame.set_child(cv)
        hbox = self.factory.create_box_horizontal(hexpand=False, vexpand=False)
        hbox.append(label)
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        dialog = self.factory.create_dialog_question(self.app.win, _('Assign to a project'), box, width=1024, height=600)
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.show()

