#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: projmgt.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for project management
"""

import os
from gettext import gettext as _


from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.config import MiAZConfig
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File
from MiAZ.backend.models import MiAZModel
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPlugin
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnViewSelector
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewDocuments

plugin_info = {
        'Module':        'projmgt',
        'Name':          'MiAZProjectMgt',
        'Loader':        'Python3',
        'Description':   _('Project management'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Content Organisation',
        'Subcategory':   'Tagging and Classification'
    }

default_available_data = {}

# Model
class Project(MiAZModel):
    __gtype_name__ = 'Project'
    __title__ = _('Project')
    __title_plural__ = _('Projects')
    __config_name__ = 'projects'
    __config_name_available__ = 'projects'
    __config_name_used__ = 'projects'

item_type = Project
i_title = item_type.__title__
i_confname = item_type.__config_name__

# Configuration
class MiAZConfigProjects(MiAZConfig):
    def __init__(self, app, plugin):
        self.plugin = plugin
        config_dir = self.plugin.get_config_dir()
        config_file_setup = self.plugin.get_config_file_default_available_data()
        ENV = app.get_env()
        super().__init__(
            app=app,
            log=MiAZLog(f'MiAZ.Config.{i_title}'),
            config_for=f'{i_confname}',
            used=os.path.join(config_dir, f'{i_confname}-used.json'),
            available=os.path.join(config_dir, f'{i_confname}-available.json'),
            default=config_file_setup,
            model=item_type,
            must_copy=False
        )

# Columnview
class MiAZColumnViewProject(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewProject'

    def __init__(self, app, available=True):
        item_type = Project
        super().__init__(app, item_type)
        self.cv.append_column(self.column_id)
        self.column_id.set_visible(False)
        self.column_title.set_title(_('Project Id'))
        self.cv.append_column(self.column_title)
        if available:
            title = _('{title} available').format(title=item_type.__title_plural__)
        else:
            title = _('{title} enabled').format(title=item_type.__title_plural__)
        self.column_title.set_title(title)

# Configuration view
class MiAZProjectsView(MiAZConfigView):
    """Manage projects from Repo Settings"""
    __gtype_name__ = 'MiAZProjectsView'

    def __init__(self, app, plugin, config):
        self.plugin = plugin
        self.config = config
        self.log = self.plugin.log
        self.config_dir = self.plugin.get_config_dir()
        self.data_dir = self.plugin.get_data_dir()
        self.data_file = self.plugin.get_data_file()
        if self.config_dir is None:
            raise
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, config_name=f'{i_confname}', custom_config=config)

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewProject(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewProject(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

    def _on_item_used_remove(self, *args):
        self.log.debug("_on_item_used_remove:: start")
        items_available = self.config.load_available()
        items_used = self.config.load_used()
        selected_item = self.viewSl.get_selected()
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')
        item_desc = selected_item.title.replace('_', ' ')
        srvprj = self.app.get_service('Projects')
        srvdlg = self.app.get_service('dialogs')
        docs = srvprj.docs_in_project(selected_item.id)
        if len(docs) == 0:
            self.log.debug("_on_item_used_remove:: no dependencies")
            items_available[selected_item.id] = selected_item.title
            self.log.debug(f"{i_title} {item_id} added back to the list of available items")
            self.config.remove_used(selected_item.id)
            self.log.debug(f"{i_title} {item_id} removed from de list of used items")
            self.config.save_available(items=items_available)
            self.update_views()
            title = _('{i_title} management').format(i_title=i_title)
            body = _('{i_title} {item_desc} disabled').format(i_title=i_title, item_desc=item_desc)
            self.srvdlg.show_warning(title=title, body=body, parent=self)

        else:
            text = _('{i_title} {item_desc} is still being used by {count} documents').format(
                i_title=i_title, item_desc=item_desc, count=len(docs))
            self.log.error(text)
            window = self.viewSl.get_root()
            title = _('Action not possible')
            items = []
            for doc in docs:
                items.append(File(id=doc, title=os.path.basename(doc)))
            view = MiAZColumnViewDocuments(self.app)
            view.update(items)
            widget = Gtk.Frame()
            widget.set_child(view)
            self.srvdlg.show_error(title=title, body=text, widget=widget, width=600, height=480, parent=window)


class MiAZProjectMgt(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZProjectMgt'
    object = GObject.Property(type=GObject.Object)
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')
        self.util = self.app.get_service('util')

        # Connect signals to startup
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Get submenu for this plugin (subcategory)
            submenu = self.plugin.install_menu_entry()

            # Install plugin submenu
            plugin_menu = Gio.Menu()
            menuitem = self.factory.create_menuitem(
                f'{i_confname}-add',
                _('Assign document(s) to {i_confname}').format(i_confname=i_confname),
                self._set_property, None, [])
            plugin_menu.append_item(menuitem)
            menuitem = self.factory.create_menuitem(
                f'{i_confname}-del',
                _('Unassign document(s) from any {i_confname}').format(i_confname=i_confname),
                self._unset_property, None, [])
            plugin_menu.append_item(menuitem)
            menuitem = self.factory.create_menuitem(
                f'{i_confname}-mgt',
                _('Manage {i_confname}').format(i_confname=i_confname),
                self._manage_properties, None, [])
            plugin_menu.append_item(menuitem)
            submenu.append_submenu(f"{i_title}", plugin_menu)

            ## Set factory data
            filepath = self.plugin.get_config_file_default_available_data()
            self.util.json_save(filepath, default_available_data)

            # Get config
            self.config = MiAZConfigProjects(self.app, self.plugin)

            # Dropdown for custom filters
            plugin_name = self.plugin.get_name()
            dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
            self.app.add_widget(f'plugin-{plugin_name}-dropdown', dropdown)
            dropdown.connect("notify::selected-item", self.workspace.update)
            self.config.connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, True, True)
            self.actions.dropdown_populate(self.config, dropdown, item_type, True, True)
            dropdown.set_hexpand(True)
            boxDropdown = self.factory.create_box_filter(f'{i_title}', dropdown)
            row = self.app.get_widget('sidebar-box-custom-filters')
            row.append(boxDropdown)

            self.workspace.register_filter_view(f'{i_title}', self._do_filter_view)

            # Load plugin data
            self._get_data()

            # Plugin configured
            self.plugin.set_started(started=True)

    def _do_filter_view(self, item, filter_list_model):
        display = False         # set display to false
        doc_id = item.id         # Document to display (or not)
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        selected_item = dropdown.get_selected_item()    # Property key selected to filter
        if selected_item is None:
            return True

        pid = selected_item.id

        if pid == 'Any':
            display = True
        elif pid == 'None':
            display = False
        else:
            try:
                docs = self.data[f'{i_confname}'][pid]
                if doc_id in docs:
                    display = True
            except KeyError:
                display = False
        return display

    def _set_property(self, *args):
        selected_items = self.workspace.get_selected_items()
        if len(selected_items) > 0:
            dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
            self.actions.dropdown_populate(self.config, dropdown, item_type, False, False)
            dialog = self.srvdlg.show_action(
                title=_('Manage {i_confname}').format(i_confname=i_confname),
                widget=dropdown)
            dialog.connect('response', self._on_set_property_response, dropdown)
            dialog.present(self.workspace.get_root())
        else:
            parent = self.app.get_widget('window')
            title = _('Project management')
            body1 = _('Action ignored')
            body2 = _('You must select at least one document')
            body = body1 + '\n' + body2
            self.srvdlg.show_error(title=title, body=body, parent=parent)

    def _get_data(self):
        datafile = self.plugin.get_data_file()
        try:
            self.data = self.util.json_load(filepath=datafile)
        except FileNotFoundError:
            self.log.debug(f"Creating new data file in {datafile}")
            self.data = {}
            self.data['documents'] = {}
            self.data[f'{i_confname}'] = {}
            self.util.json_save(filepath=datafile, adict=self.data)

    def _on_set_property_response(self, dialog, response, dropdown):
        if response == 'apply':
            selected_documents = []
            for item in self.workspace.get_selected_items():
                selected_documents.append(item.id)
            config_item = dropdown.get_selected_item()

            # Unset documents property first
            self._unset_property_real(selected_documents)

            # Set property to selected documents
            change = self._set_property_real(selected_documents, config_item.id)
            if change:
                self.workspace.update()
                self.log.debug(f"{i_title} {config_item.title} set to {len(selected_documents)} documents")
                title = _('{i_title} management').format(i_title=i_title)
                body = _('{i_title} {title} set to {count} documents').format(
                    i_title=i_title, title=config_item.title, count=len(selected_documents))
                self.srvdlg.show_info(title=title, body=body, parent=dialog.get_root())

    def _set_property_real(self, selected_documents, pid):
        change = False
        documents = self.data['documents']
        config_data = self.data[f'{i_confname}']

        for doc_id in selected_documents:
            self.log.debug(f"Request to set {i_confname} '{pid}' for document '{doc_id}'")
            documents[doc_id] = pid
            if pid in config_data:
                s = set(config_data[pid])
                s.add(doc_id)
                config_data[pid] = list(s)
            else:
                config_data[pid] = [doc_id]
            change = True
            self.log.debug(f"{i_title} for document '{doc_id}' set to '{pid}'")

        # Save data
        if change:
            self.data['documents'] = documents
            self.data[f'{i_confname}'] = config_data
            datafile = self.plugin.get_data_file()
            self.util.json_save(datafile, self.data)
        return change

    def _unset_property(self, *args):
        selected_documents = []
        for item in self.workspace.get_selected_items():
            selected_documents.append(item.id)
        self._unset_property_real(selected_documents)
        title = _('{i_title} management').format(i_title=i_title)
        body = _('Removed {i_confname} for selected documents').format(i_confname=i_confname)
        self.srvdlg.show_info(title=title, body=body, parent=self.workspace.get_root())

    def _unset_property_real(self, selected_documents):
        change = False
        documents = self.data['documents']
        config_data = self.data[f'{i_confname}']

        for doc_id in selected_documents:
            self.log.debug(f"Request to unset any {i_confname} for document '{doc_id}'")
            if doc_id in self.data.get("documents", {}):
                # Get the config key before deleting the document
                pid = self.data["documents"][doc_id]
                del self.data["documents"][doc_id]

                # Remove from config_data if the config key exists
                if pid in self.data.get(f'{i_confname}', {}):
                    # Remove all occurrences of the doc_id from the config_data list
                    doc_list = self.data[f'{i_confname}'][pid]
                    while doc_id in doc_list:
                        doc_list.remove(doc_id)
                change = True
                self.log.debug(f"{i_title} '{pid}' unset for document '{doc_id}'")

            # Additionally, check all other keys in case the document exists there
            # even if it wasn't in the documents dictionary
            for pid, doc_list in self.data.get(f'{i_confname}', {}).items():
                while doc_id in doc_list:
                    doc_list.remove(doc_id)
                    change = True

        # Save data
        if change:
            datafile = self.plugin.get_data_file()
            self.util.json_save(datafile, self.data)
            self.log.debug(f"{i_title} for {len(selected_documents)} documents removed")
            self.workspace.update()
        else:
            self.log.debug(f"No changes detected for {i_confname} for {len(selected_documents)}")
        return change

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

        # Documents columnview
        frame = Gtk.Frame()
        cv = MiAZColumnViewDocuments(self.app)
        frame.set_child(cv)
        cv.set_hexpand(True)
        cv.set_vexpand(True)

        # Get projects
        item_type = Project
        config = self.app.get_config_dict()
        dropdown = self.factory.create_dropdown_generic(Project)
        dropdown.connect('notify::selected-item', _on_selected_project, cv)
        self.actions.dropdown_populate(self.config, dropdown, Project, any_value=False)

        # dialog
        box = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        box.add_css_class('toolbar')
        box.append(dropdown)
        box.append(frame)
        window = self.app.get_widget('window')
        self.srvdlg.show_info(title=_('Documents per project'), widget=box, width=800, height=600, parent=window)

    def _manage_properties(self, *args):
        parent = self.app.get_widget('window')
        self.show_settings(widget=parent)

    def show_settings(self, widget: Gtk.Widget = None):
        config_dir = self.plugin.get_config_dir()
        configview = MiAZProjectsView(self.app, plugin=self.plugin, config=self.config)
        configview.update_views()
        dialog = self.srvdlg.show_noop(
            title=_('Manage {i_confname}').format(i_confname=i_confname),
            widget=configview, width=800, height=600)
        dialog.present(widget.get_root())
