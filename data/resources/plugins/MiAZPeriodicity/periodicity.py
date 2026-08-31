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
        'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
        'Version':       '0.6',
        'Category':      'Organise',
        'Subcategory':   'Tags'
    }


# Default value assigned to documents without an explicit periodicity
DEFAULT_PERIODICITY = 'OD'

default_available_data = {
    'OD': _('On demand'),
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

# Rename dialog tab
class MiAZPeriodicityTab(Gtk.Box):
    """Periodicity of a single document, shown as a tab in the rename dialog.

    The dropdown only holds the choice; the value is written by apply(), which
    the dialog calls after the rename went through, so cancelling changes
    nothing.
    """
    __gtype_name__ = 'MiAZPeriodicityTab'

    def __init__(self, app, plugin_ext):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         hexpand=True, vexpand=True)
        self.app = app
        self.ext = plugin_ext
        self.log = MiAZLog('MiAZ.PeriodicityTab')
        self.factory = self.app.get_service('factory')
        self.actions = self.app.get_service('actions')
        self.doc_id = None

        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)

        label = Gtk.Label()
        label.set_xalign(0.0)
        label.add_css_class('dim-label')
        label.set_text(_('How often this document is expected to arrive'))
        self.append(label)

        self.dropdown = self.factory.create_dropdown_generic(
            item_type=item_type, ellipsize=True, enable_search=True)
        self.actions.dropdown_populate(self.ext.config, self.dropdown, item_type, False, False)

        listbox = Gtk.ListBox.new()
        icm = self.app.get_service('icons')
        icon = icm.get_image_by_name('io.github.t00m.MiAZ-res-date')
        row = self.factory.create_actionrow(title=i_title, prefix=icon, suffix=self.dropdown)
        listbox.append(row)
        frame = Gtk.Frame()
        frame.set_child(listbox)
        self.append(frame)

    def _select(self, pid):
        model = self.dropdown.get_model()
        for position, item in enumerate(model):
            if item.id == pid:
                self.dropdown.set_selected(position)
                return
        self.dropdown.set_selected(0)

    # Document tab contract
    def set_document(self, doc_id):
        self.doc_id = doc_id
        pid = self.ext._get_pid(doc_id)
        self._select(pid if pid is not None else DEFAULT_PERIODICITY)

    def apply(self, old_id, new_id):
        """Write the chosen periodicity. True when something actually changed."""
        item = self.dropdown.get_selected_item()
        if item is None:
            return False
        if self.ext._get_pid(new_id) == item.id:
            return False
        self.ext._unset_property_real([new_id])
        self.ext._set_property_real([new_id], item.id)
        return True


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
        self._data = None
        self._data_file = None

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
        self._filename_added_handler = self.util.connect('filename-added', self._on_filename_added)
        self._filename_renamed_handler = self.util.connect('filename-renamed', self._on_filename_renamed)
        self._filename_deleted_handler = self.util.connect('filename-deleted', self._on_filename_deleted)

    def do_deactivate(self):
        # The sidebar dropdown, its size group, the plugin-dropdowns entry and
        # the widget key are all taken back by the plugin system, which owns
        # what add_sidebar_dropdown handed it.
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        self.workspace.unregister_filter_view(f'{i_title}')
        if hasattr(self, '_used_updated_handler'):
            self.config.disconnect(self._used_updated_handler)
        if hasattr(self, '_selected_item_handler') and dropdown is not None:
            dropdown.disconnect(self._selected_item_handler)
        if hasattr(self, '_filename_added_handler'):
            self.util.disconnect(self._filename_added_handler)
        if hasattr(self, '_filename_renamed_handler'):
            self.util.disconnect(self._filename_renamed_handler)
        if hasattr(self, '_filename_deleted_handler'):
            self.util.disconnect(self._filename_deleted_handler)
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.unregister_document_tabs()
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Always reinstall workspace menu entries (cleared by
            # _on_plugins_updated). Straight into the plugin's own entry: a
            # submenu named after the plugin, inside the entry already named
            # after the plugin, is one level of menu that says nothing.
            self.plugin.install_menu_entry(self.factory.create_menuitem(
                f'{i_confname}-add',
                _('Set {i_confname}').format(i_confname=i_confname),
                self._set_property, None, []))
            self.plugin.install_menu_entry(self.factory.create_menuitem(
                f'{i_confname}-del',
                _('Unset {i_confname}').format(i_confname=i_confname),
                self._unset_property, None, []))
            self.plugin.install_menu_entry(self.factory.create_menuitem(
                f'{i_confname}-mgt',
                _('Manage {i_confname}').format(i_confname=i_confname),
                self.show_settings, None, []))

            # One-time setup guarded by the dropdown widget sentinel
            plugin_name = self.plugin.get_name()
            if self.app.get_widget(f'plugin-{plugin_name}-dropdown') is None:
                ## Set factory data
                filepath = self.plugin.get_config_file_default_available_data()
                self.util.json_save(filepath, default_available_data)

                # Get config
                self.config = MiAZConfigPeriodicity(self.app, self.plugin)

                # Ensure the default value exists and assign it to every
                # document that has no periodicity yet (transparent to the user)
                self._ensure_default_value()
                self._apply_default_assignments()

                # Dropdown for custom filters
                dropdown = self.factory.create_dropdown_generic(item_type=item_type, ellipsize=True, enable_search=True)
                self._used_updated_handler = self.config.connect('used-updated', self.actions.dropdown_repopulate, dropdown, item_type, True, False)
                self.actions.dropdown_populate(self.config, dropdown, item_type, True, False)
                self._selected_item_handler = dropdown.connect("notify::selected-item", self.workspace.update)
                # Sizing, the shared size group, the plugin-dropdowns list, the
                # widget key and the icon row: all of it, and its teardown.
                self.plugin.add_sidebar_dropdown(dropdown)
                self.workspace.register_filter_view(f'{i_title}', self._do_filter_view)
                self.log.info(f"Plugin {plugin_name} fully initialized")

            # Periodicity of the document being renamed, as a tab in that dialog.
            self.plugin.register_document_tab(
                name='periodicity',
                title=i_title,
                factory=lambda app: MiAZPeriodicityTab(app, self),
                weight=200)

            # Plugin configured
            self.plugin.set_started(started=True)

    def _do_filter_view(self, item, filter_list_model):
        plugin_name = self.plugin.get_name()
        dropdown = self.app.get_widget(f'plugin-{plugin_name}-dropdown')
        selected_item = dropdown.get_selected_item()    # Property key selected to filter
        if selected_item is None:
            return True

        pid = selected_item.id
        # Inactive filter: skip reading the data file. This runs once per
        # document on every refilter, so returning early keeps free-text
        # search instant when no periodicity is selected.
        if pid == 'Any':
            return True

        doc_id = item.id
        data = self._get_data()
        if pid == 'None':
            return doc_id not in data.get('documents', {})
        try:
            return doc_id in data[f'{i_confname}'][pid]
        except KeyError:
            return False

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
        # Cache the parsed data file and reuse it until the active repository
        # (and therefore the data file path) changes. Writers mutate this same
        # object in place before saving, so the cache stays current.
        datafile = self.plugin.get_data_file()
        if self._data is not None and self._data_file == datafile:
            return self._data
        try:
            data = self.util.json_load(filepath=datafile)
        except FileNotFoundError:
            self.log.debug(f"Creating new data file in {datafile}")
            data = {}
            data['documents'] = {}
            data[f'{i_confname}'] = {}
            self.util.json_save(filepath=datafile, adict=data)
        self._data = data
        self._data_file = datafile
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

    def _ensure_default_value(self):
        """Make sure the default periodicity value is both available and used."""
        title = _('On demand')
        if not self.config.exists_available(DEFAULT_PERIODICITY):
            self.config.add_available(DEFAULT_PERIODICITY, title)
        if not self.config.exists_used(DEFAULT_PERIODICITY):
            self.config.add_used(DEFAULT_PERIODICITY, title)

    def _apply_default_assignments(self):
        """Assign the default periodicity to every repository document that has
        none. Runs on activation, transparent to the user, debug-logged only."""
        repository = self.app.get_service('repo')
        try:
            docs = self.util.get_files(repository.docs)
        except Exception:
            docs = []
        unassigned = [os.path.basename(fp) for fp in docs
                      if self._get_pid(os.path.basename(fp)) is None]
        if unassigned:
            self._set_property_real(unassigned, DEFAULT_PERIODICITY)
            self.log.debug(
                f"{i_title}: default '{DEFAULT_PERIODICITY}' applied to "
                f"{len(unassigned)} document(s) without periodicity")

    def _unset_property(self, *args):
        parent = self.workspace.get_root()
        selected_documents = []
        for item in self.workspace.get_selected_items():
            selected_documents.append(item.id)
        self._unset_property_real(selected_documents)
        # Documents must always keep a periodicity: fall back to the default
        if selected_documents:
            self._set_property_real(selected_documents, DEFAULT_PERIODICITY)
            self.workspace.update()
        self.srvdlg.show_toast(_('Reset {i_confname} to default for selected documents').format(i_confname=i_confname))

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

    def _on_filename_added(self, util, fp_target):
        target = os.path.basename(fp_target)
        if self._get_pid(target) is None:
            self._set_property_real([target], DEFAULT_PERIODICITY)
            self.log.debug(f"{i_title}: default '{DEFAULT_PERIODICITY}' assigned to new document '{target}'")

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
