#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: periodicity.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Periodicity plugin
"""

import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZModel
from MiAZ.backend.config import MiAZConfig
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnViewSelector
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
        'Module':        'periodicity',
        'Name':          'MiAZPeriodicity',
        'Loader':        'Python3',
        'Description':   _('Set document periodicity'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.6',
        'Category':      'Content Organisation',
        'Subcategory':   'Tagging and Classification'
    }


default_available_data = {
    '1D': _('Daily'),
    '1W': _('Weekly'),
    '1M': _('Monthly'),
    '1Q': _('Quarterly'),
    '1Y': _('Yearly'),
    '1H': _('Hourly'),
    '1T': _('Minutely'),
    '1S': _('Secondly'),
    'BD': _('Business Day'),
    'WE': _('Weekend'),
    '2W': _('Bi-Weekly'),
    '2M': _('Bi-Monthly'),
    '6M': _('Semi-Annual')
}

# Model
class Periodicity(MiAZModel):
    __gtype_name__ = 'Periodicity'
    __title__ = _('Periodicity')
    __title_plural__ = _('Periodicity')
    __config_name__ = 'periodicity'
    __config_name_available__ = 'periodicity'
    __config_name_used__ = 'periodicity'

item_type = Periodicity
i_title = item_type.__title__
i_confname = item_type.__config_name__


# Configuration
class MiAZConfigPeriodicity(MiAZConfig):
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
class MiAZColumnViewPeriodicity(MiAZColumnViewSelector):
    """ Custom ColumnView widget for MiAZ """
    __gtype_name__ = 'MiAZColumnViewPeriodicity'

    def __init__(self, app, available=True):
        super().__init__(app, item_type)
        self.cv.append_column(self.column_id)
        self.column_id.set_visible(False)
        self.column_title.set_title(_('{title} Id').format(title=i_title))
        self.cv.append_column(self.column_title)
        if available:
            title = _('{title} available').format(title=item_type.__title_plural__)
        else:
            title = _('{title} enabled').format(title=item_type.__title_plural__)
        self.column_title.set_title(title)


# Configuration view
class MiAZPeriodicityView(MiAZConfigView):
    """Manage purposes from Repo Settings"""
    __gtype_name__ = 'MiAZPeriodicityView'

    def __init__(self, app, plugin, config):
        self.plugin = plugin
        self.config = config
        self.log = self.plugin.log
        self.config_dir = self.plugin.get_config_dir()
        self.data_dir = self.plugin.get_data_dir()
        self.data_file = self.plugin.get_data_file()
        if self.config_dir is None:
            raise RuntimeError("MiAZPeriodicity: config_dir is None")
        super().__init__(app, config_name=f'{i_confname}', custom_config=config)

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPeriodicity(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPeriodicity(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)
        self.update_views()

# Plugin
class MiAZPeriodicityPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZPeriodicityPlugin'
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
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)
        self._filename_renamed_handler = self.util.connect('filename-renamed', self._on_filename_renamed)
        self._filename_deleted_handler = self.util.connect('filename-deleted', self._on_filename_deleted)

    def do_deactivate(self):
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        if dropdown is not None:
            dd_parent = dropdown.get_parent()
            if dd_parent is not None:
                dd_parent.remove(dropdown)
            dd_size_group = self.app.get_widget('sidebar-dropdown-size-group')
            if dd_size_group is not None:
                dd_size_group.remove_widget(dropdown)
            plugin_dropdowns = self.app.get_widget('plugin-dropdowns')
            if plugin_dropdowns is not None and dropdown in plugin_dropdowns:
                plugin_dropdowns.remove(dropdown)
            self.app.remove_widget(f'plugin-{plugin_name}-dropdown')
        section = self.app.get_widget('sidebar-plugin-section')
        if section is not None and hasattr(self, '_sidebar_item'):
            section.remove(self._sidebar_item)
        self.workspace.unregister_filter_view(f'{i_title}')
        if hasattr(self, '_used_updated_handler'):
            self.config.disconnect(self._used_updated_handler)
        if hasattr(self, '_selected_item_handler') and dropdown is not None:
            dropdown.disconnect(self._selected_item_handler)
        if hasattr(self, '_filename_renamed_handler'):
            self.util.disconnect(self._filename_renamed_handler)
        if hasattr(self, '_filename_deleted_handler'):
            self.util.disconnect(self._filename_deleted_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Always reinstall workspace menu entries (cleared by _on_plugins_updated)
            submenu = self.plugin.install_menu_entry()

            # Install plugin submenu
            plugin_menu = Gio.Menu()
            menuitem = self.factory.create_menuitem(f'{i_confname}-add', _('Set {i_confname}').format(i_confname=i_confname), self._set_property, None, [])
            plugin_menu.append_item(menuitem)
            menuitem = self.factory.create_menuitem(f'{i_confname}-del', _('Unset {i_confname}').format(i_confname=i_confname), self._unset_property, None, [])
            plugin_menu.append_item(menuitem)
            menuitem = self.factory.create_menuitem(f'{i_confname}-mgt', _('Manage {i_confname}').format(i_confname=i_confname), self.show_settings, None, [])
            plugin_menu.append_item(menuitem)
            submenu.append_submenu(_('{i_title}').format(i_title=i_title), plugin_menu)

            # One-time setup guarded by the dropdown widget sentinel
            plugin_name = self.plugin.get_name()
            if self.app.get_widget(f'plugin-{plugin_name}-dropdown') is None:
                ## Set factory data
                filepath = self.plugin.get_config_file_default_available_data()
                self.util.json_save(filepath, default_available_data)

                # Get config
                self.config = MiAZConfigPeriodicity(self.app, self.plugin)

                # Dropdown for custom filters
                dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
                self.app.add_widget(f'plugin-{plugin_name}-dropdown', dropdown)
                self.app.get_widget('plugin-dropdowns').append(dropdown)
                self._used_updated_handler = self.config.connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, True, True)
                self.actions.dropdown_populate(self.config, dropdown, item_type, True, True)
                self._selected_item_handler = dropdown.connect("notify::selected-item", self.workspace.update)
                dropdown.set_size_request(190, -1)
                dd_size_group = self.app.get_widget('sidebar-dropdown-size-group')
                if dd_size_group is not None:
                    dd_size_group.add_widget(dropdown)
                section = self.app.get_widget('sidebar-plugin-section')
                if section is not None:
                    icon_path = self.plugin.get_icon_path()
                    if icon_path:
                        img = Gtk.Image.new_from_file(icon_path)
                        img.set_pixel_size(16)
                        img.set_valign(Gtk.Align.CENTER)
                        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        box.set_hexpand(True)
                        box.append(img)
                        box.append(dropdown)
                        self._sidebar_item = box
                    else:
                        self._sidebar_item = dropdown
                    section.append(self._sidebar_item)
                self.workspace.register_filter_view(f'{i_title}', self._do_filter_view)
                self.log.info(f"Plugin {plugin_name} fully initialized")

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
        data = self._get_data()

        if pid == 'Any':
            display = True
        elif pid == 'None':
            display = False
        else:
            try:
                docs = data[f'{i_confname}'][pid]
                if doc_id in docs:
                    display = True
            except KeyError:
                display = False
        return display

    def _set_property(self, *args):
        parent = self.workspace.get_root()
        selected_items = self.workspace.get_selected_items()
        if len(selected_items) > 0:
            dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
            self.actions.dropdown_populate(self.config, dropdown, item_type, False, False)
            dialog = self.srvdlg.show_action(title=_('Manage {i_confname}').format(i_confname=i_confname), widget=dropdown)
            dialog.connect('response', self._on_set_property_response, dropdown)
            dialog.present(parent)
        else:
            self.srvdlg.show_error(title=_('Action ignored'), body=_('You must select at least one document'), parent=parent)

    def _get_data(self):
        datafile = self.plugin.get_data_file()
        try:
            data = self.util.json_load(filepath=datafile)
        except FileNotFoundError:
            self.log.debug(f"Creating new data file in {datafile}")
            data = {}
            data['documents'] = {}
            data[f'{i_confname}'] = {}
            self.util.json_save(filepath=datafile, adict=data)
        return data

    def _on_set_property_response(self, dialog, response, dropdown):
        parent = self.workspace.get_root()
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
                body = _('{i_title} {title} set to {count} documents').format(
                    i_title=i_title, title=config_item.title, count=len(selected_documents))
                self.srvdlg.show_toast(body)

    def _set_property_real(self, selected_documents, pid):
        change = False
        data = self._get_data()
        documents = data['documents']
        config_data = data[f'{i_confname}']

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
            data['documents'] = documents
            data[f'{i_confname}'] = config_data
            datafile = self.plugin.get_data_file()
            self.util.json_save(datafile, data)
        return change

    def _unset_property(self, *args):
        parent = self.workspace.get_root()
        selected_documents = []
        for item in self.workspace.get_selected_items():
            selected_documents.append(item.id)
        self._unset_property_real(selected_documents)
        self.srvdlg.show_toast(_('Removed {i_confname} for selected documents').format(i_confname=i_confname))

    def _unset_property_real(self, selected_documents):
        change = False
        data = self._get_data()
        documents = data['documents']
        config_data = data[f'{i_confname}']

        for doc_id in selected_documents:
            self.log.debug(f"Request to unset any {i_confname} for document '{doc_id}'")
            if doc_id in data.get("documents", {}):
                # Get the config key before deleting the document
                pid = data["documents"][doc_id]
                del data["documents"][doc_id]

                # Remove from config_data if the config key exists
                if pid in data.get(f'{i_confname}', {}):
                    # Remove all occurrences of the doc_id from the config_data list
                    doc_list = data[f'{i_confname}'][pid]
                    while doc_id in doc_list:
                        doc_list.remove(doc_id)
                change = True
                self.log.debug(f"{i_title} '{pid}' unset for document '{doc_id}'")

            # Additionally, check all other keys in case the document exists there
            # even if it wasn't in the documents dictionary
            for pid, doc_list in data.get(f'{i_confname}', {}).items():
                while doc_id in doc_list:
                    doc_list.remove(doc_id)
                    change = True

        # Save data
        if change:
            datafile = self.plugin.get_data_file()
            self.util.json_save(datafile, data)
            self.log.debug(f"{i_title} for {len(selected_documents)} documents removed")
            self.workspace.update()
        else:
            self.log.debug(f"No changes detected for {i_confname} for {len(selected_documents)}")
        return change

    def show_settings(self, *args):
        try:
            if isinstance(args[0], Gtk.Widget):
                widget = args[0]
            else:
                widget = None
        except (TypeError, IndexError):
            widget = None

        if widget is None:
            parent = self.workspace.get_root()
        else:
            parent = widget.get_root()

        config_dir = self.plugin.get_config_dir()
        configview = MiAZPeriodicityView(self.app, plugin=self.plugin, config=self.config)
        configview.update_views()
        dialog = self.srvdlg.show_noop(
            title=_('{i_confname} management').format(i_confname=i_confname),
            widget=configview, width=800, height=600)
        dialog.present(parent)

    def _get_pid(self, doc_id):
        """Return the property key associated to a document"""
        data = self._get_data()
        documents = data['documents']
        try:
            return documents[doc_id]
        except KeyError:
            return None

    def _on_filename_renamed(self, util, fp_source, fp_target):
        source = os.path.basename(fp_source)
        target = os.path.basename(fp_target)
        pid = self._get_pid(source)
        if pid is not None:
            self._unset_property_real([source])
            self._set_property_real([target], pid)
            self.log.debug(f"{i_title} {pid} unset for '{source}' and set to '{target}'")

    def _on_filename_deleted(self, util, filepaths):
        for fp_source in filepaths:
            source = os.path.basename(fp_source)
            pid = self._get_pid(source)
            if pid is not None:
                self._unset_property_real([source])
                self.log.debug(f"{i_title} {pid} unset for '{source}'")
