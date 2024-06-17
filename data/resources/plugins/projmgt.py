#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2csv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to CSV
"""

import os
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File
from MiAZ.backend.models import Project
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
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
        self.log = MiAZLog('Plugin.ProjectMgt')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_menuitem)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def add_menuitem(self, *args):
        factory = self.app.get_service('factory')
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
            menuitem = factory.create_menuitem('project-manage', _('...Manage projects'), self.project_manage, None, [])
            submenu_project.append_item(menuitem)
            menuitem = factory.create_menuitem('project-assign', _('...assign to project'), self.project_assign, None, [])
            submenu_project.append_item(menuitem)
            menuitem = factory.create_menuitem('project-withdraw', _('...withdraw from project'), self.project_withdraw, None, [])
            submenu_project.append_item(menuitem)


    def project_assign(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        item_type = Project
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items()

        def dialog_response(dialog, response, dropdown, items):
            if response == Gtk.ResponseType.ACCEPT:
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                projects = self.app.get_service('Projects')
                projects.add_batch(pid, docs)
                workspace = self.app.get_widget('workspace')
                workspace.update()
            dialog.destroy()

        config = self.app.get_config_dict()
        i_type = item_type.__gtype_name__
        box = factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = factory.create_dropdown_generic(Project)
        config[i_type].connect('used-updated', actions.dropdown_populate, dropdown, item_type, False, False)
        actions.dropdown_populate(config[i_type], dropdown, Project, any_value=False)
        btnManage = factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', actions.manage_resource, Configview['Project'](self.app))
        label = factory.create_label(_('Assign the following documents to this project: '))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='caption')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        projects = self.app.get_service('Projects')
        for item in items:
            tprojects = ', '.join([projects.description(pid) for pid in projects.assigned_to(item.id)])
            citems.append(File(id=item.id, title=f"<b>{tprojects}</b>"))
        cv.update(citems)
        frame.set_child(cv)
        hbox = factory.create_box_horizontal(hexpand=False, vexpand=False)
        hbox.append(label)
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = factory.create_dialog_question(window, _('Assign to a project'), box, width=1024, height=600)
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.show()

    def project_withdraw(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        workspace = self.app.get_widget('workspace')
        item_type = Project
        items = workspace.get_selected_items()

        def dialog_response(dialog, response, dropdown, items):
            if response == Gtk.ResponseType.ACCEPT:
                projects = self.app.get_service('Projects')
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                projects.remove_batch(pid, docs)
                workspace = self.app.get_widget('workspace')
                workspace.update()
            dialog.destroy()

        config = self.app.get_config_dict()
        i_type = item_type.__gtype_name__
        box = factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = factory.create_dropdown_generic(Project)
        config[i_type].connect('used-updated', actions.dropdown_populate, dropdown, item_type, False, False)

        # Get projects
        projects = self.app.get_service('Projects')
        sprojects = set()
        for item in items:
            for project in projects.assigned_to(item.id):
                sprojects.add(project)

        actions.dropdown_populate(config[i_type], dropdown, Project, any_value=False, only_include=list(sprojects))
        btnManage = factory.create_button('miaz-res-manage', '')
        btnManage.connect('clicked', actions.manage_resource, Configview['Project'](self.app))
        label = factory.create_label(_('Withdraw the following documents from this project: '))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        cv.get_style_context().add_class(class_name='caption')
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        citems = []
        for item in items:
            tprojects = ', '.join([projects.description(pid) for pid in projects.assigned_to(item.id)])
            citems.append(File(id=item.id, title=f"<b>{tprojects}</b>"))
        cv.update(citems)
        frame.set_child(cv)
        hbox = factory.create_box_horizontal(hexpand=False, vexpand=False)
        hbox.append(label)
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = factory.create_dialog_question(window, _('Assign to a project'), box, width=1024, height=600)
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.show()

    def project_manage(self, *args):
        actions = self.app.get_service('actions')
        actions.show_repository_settings()
        winRepoSettings = self.app.get_widget('settings-repo')
        if winRepoSettings is not None:
            notebook = self.app.get_widget('repository-settings-notebook')
            notebook.set_current_page(5)
