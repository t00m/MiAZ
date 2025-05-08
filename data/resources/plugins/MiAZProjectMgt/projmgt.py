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

from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin
from MiAZ.backend.models import File
from MiAZ.backend.models import Project
from MiAZ.backend.models import Document
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewProject
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewDocuments

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
    plugin = None
    file = __file__.replace('.py', '.plugin')

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self.file, self)

        ## Get logger
        self.log = self.plugin.get_logger()
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def startup(self, *args):
        menuitem_name = f'plugin-menuitem-{self.plugin.get_name()}'
        menuitem = self.app.get_widget(menuitem_name)
        if menuitem is None:
            factory = self.app.get_service('factory')
            main_menu = self.app.get_widget('workspace-menu-selection')

            submenu_project = Gio.Menu.new()
            menu_project = Gio.MenuItem.new_submenu(
                label=_('Project management...'),
                submenu=submenu_project,
            )
            self.app.add_widget(menuitem_name, menu_project)
            self.app.add_widget('workspace-menu-selection-menu-project', menu_project)
            self.app.add_widget('workspace-menu-selection-submenu-project', submenu_project)
            menuitem = factory.create_menuitem('project-manage', _('... manage projects'), self.project_manage, None, [])
            submenu_project.append_item(menuitem)
            menuitem = factory.create_menuitem('project-assign', _('... assign to project'), self.project_assign, None, [])
            submenu_project.append_item(menuitem)
            menuitem = factory.create_menuitem('project-withdraw', _('... withdraw from project'), self.project_withdraw, None, [])
            submenu_project.append_item(menuitem)
            menuitem = factory.create_menuitem('project-view', _('... view documents per project'), self.project_view, None, [])
            submenu_project.append_item(menuitem)
            main_menu.append_item(menu_project)

    def project_assign(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        item_type = Project
        workspace = self.app.get_widget('workspace')
        srvdlg = self.app.get_service('dialogs')
        items = workspace.get_selected_items()
        if actions.stop_if_no_items(items):
            return

        def dialog_response(dialog, response, dropdown, items):
            if response == 'apply':
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                projects = self.app.get_service('Projects')
                projects.add_batch(pid, docs)
                workspace = self.app.get_widget('workspace')
                workspace.update()

        config = self.app.get_config_dict()
        i_type = item_type.__gtype_name__
        box = factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        dropdown = factory.create_dropdown_generic(Project)
        config[i_type].connect('used-updated', actions.dropdown_populate, dropdown, item_type, False, False)
        actions.dropdown_populate(config[i_type], dropdown, Project, any_value=False)
        btnManage = factory.create_button('io.github.t00m.MiAZ-res-projects', '')
        btnManage.connect('clicked', actions.manage_resource, Configview['Project'](self.app))
        label = factory.create_label(_('Assign the following documents to this project: '))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        # ~ cv.get_style_context().add_class(class_name='caption')
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
        dialog = srvdlg.show_question(title=_('Assign document(s) to a project'), widget=box, width=800, height=600)
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.present(window)

    def project_withdraw(self, *args):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        workspace = self.app.get_widget('workspace')
        srvdlg = self.app.get_service('dialogs')
        item_type = Project
        items = workspace.get_selected_items()
        if actions.stop_if_no_items(items):
            return

        def dialog_response(dialog, response, dropdown, items):
            if response == 'apply':
                projects = self.app.get_service('Projects')
                pid = dropdown.get_selected_item().id
                docs = []
                for item in items:
                    docs.append(os.path.basename(item.id))
                projects.remove_batch(pid, docs)
                workspace = self.app.get_widget('workspace')
                workspace.update()


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
        btnManage = factory.create_button('io.github.t00m.MiAZ-res-projects', '')
        btnManage.connect('clicked', actions.manage_resource, Configview['Project'](self.app))
        label = factory.create_label(_('Withdraw the following documents from this project: '))
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassProject(self.app)
        # ~ cv.get_style_context().add_class(class_name='caption')
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
        dialog = srvdlg.show_question(title=_('Withdraw from project'), widget=box, width=800, height=600)
        dialog.connect('response', dialog_response, dropdown, items)
        dialog.present(window)

    def project_manage(self, *args):
        actions = self.app.get_service('actions')
        actions.show_repository_settings()
        winRepoSettings = self.app.get_widget('settings-repo')
        if winRepoSettings is not None:
            notebook = self.app.get_widget('repository-settings-notebook')
            notebook.set_current_page(5)

    def project_view(self, *args):
        def _on_selected_project(dropdown, gparamobject, cv):
            srvprj = self.app.get_service('Projects')
            pid = dropdown.get_selected_item().id
            docs = srvprj.docs_in_project(pid)
            items = []
            for doc in docs:
                items.append(File(id=doc, title=doc))
            cv.update(items)
            self.log.warning(f"{len(docs)} documents in project {pid}")

        actions = self.app.get_service('actions')
        srvdlg = self.app.get_service('dialogs')
        factory = self.app.get_service('factory')

        # Documents columnview
        frame = Gtk.Frame()
        cv = MiAZColumnViewDocuments(self.app)
        frame.set_child(cv)
        cv.set_hexpand(True)
        cv.set_vexpand(True)

        # Get projects
        item_type = Project
        i_type = item_type.__gtype_name__
        config = self.app.get_config_dict()
        dropdown = factory.create_dropdown_generic(Project)
        dropdown.connect('notify::selected-item', _on_selected_project, cv)
        actions.dropdown_populate(config[i_type], dropdown, Project, any_value=False)

        # dialog
        box = factory.create_box_vertical(hexpand=True, vexpand=True)
        box.get_style_context().add_class(class_name='toolbar')
        box.append(dropdown)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = srvdlg.show_info(title=_('Documents per project'), widget=box, width=800, height=600)
        # ~ dialog.connect('response', dialog_response, dropdown, items)
        dialog.present(window)



