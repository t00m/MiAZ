#!/usr/bin/python3
# File: configview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom selector views to manage configuration

import os
import glob
import time
from gettext import gettext as _
import threading

import requests

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File, Plugin
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPluginType
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewDocuments
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewCountry
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewGroup
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPurpose
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPerson
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewProject
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewRepo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.services.dialogs import MiAZDialogAddRepo


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    config_for = None

    def __init__(self, app, config_name=None, custom_config=None):
        # ~ super(MiAZSelector, self).__init__(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZConfigView')
        self.repository = self.app.get_service('repo')
        self.srvdlg = self.app.get_service('dialogs')
        self.config_name = config_name
        try:
            self.conf = self.app.get_config_dict()
            self.config = self.conf[config_name]
        except Exception as error:
            self.config = custom_config
        self._setup_view_finish()
        self.config.connect('used-updated', self.update_views)
        self.config.connect('available-updated', self.update_views)
        self.set_vexpand(True)
        # ~ self.log.debug(f"Configview for {config_name} initialited")
        item_type = self.config.model
        tooltip=f'Enable selected {item_type.__title__.lower()}'
        self.btnAddToUsed.set_tooltip_markup(tooltip)
        tooltip=f'Disable selected {item_type.__title__.lower()}'
        self.btnRemoveFromUsed.set_tooltip_markup(tooltip)

    def update_config(self):
        self.config = self.conf[self.config_name]

    def get_config_for(self):
        return self.config.config_for

    def _setup_view(self):
        selector = MiAZSelector(self.app)
        frmView = Gtk.Frame()
        self.view = MiAZColumnView(self.app)
        self.view.set_filter(self._do_filter_view)
        frmView.set_child(self.view)
        return selector

    def _on_config_import(self, *args):
        self.log.debug(f"Import configuration for '{self.config.config_for}'")

    def _add_config_menubutton(self, name: str):
        return
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        widgets = []
        btnConfigImport = factory.create_button(icon_name='io.github.t00m.MiAZ-document-open-symbolic',
                                                     title=f'Import config for {self.config.config_for.lower()}',
                                                     callback=actions.import_config,
                                                     data=self.config.model,
                                                     css_classes=['flat'])
        widgets.append(btnConfigImport)
        btnConfigImport = factory.create_button(icon_name='io.github.t00m.MiAZ-document-save-symbolic',
                                                     title=f'Export config for {self.config.config_for.lower()}',
                                                     callback=actions.export_config,
                                                     data=self.config.model,
                                                     css_classes=['flat'])
        widgets.append(btnConfigImport)
        button = factory.create_button_popover(icon_name='io.github.t00m.MiAZ-emblem-system-symbolic',
                                                    title='',
                                                    widgets=widgets)

        boxEmpty = factory.create_box_horizontal(hexpand=True)
        self.boxOper.append(boxEmpty)

        # ~ FIXME: hidden until the import/export functionality is fixed
        # ~ self.boxOper.append(button)

    # ~ def _on_item_available_remove(self, *args):
        # ~ selected_item = self.viewAv.get_selected()
        # ~ if selected_item is None:
            # ~ return

        # ~ items_available = self.config.load_available()
        # ~ item_type = self.config.model
        # ~ i_title = item_type.__title__
        # ~ item_id = selected_item.id.replace('_', ' ')
        # ~ item_dsc = selected_item.title

        # ~ is_used = self.config.exists_used(selected_item.id)
        # ~ if not is_used:
            # ~ title = f"{i_title} management"
            # ~ body = f"Your about to delete <i>{i_title.lower()} {item_dsc}</i>.\n\nAre you sure?"
            # ~ dialog = self.srvdlg.show_question(title=title, body=body)
            # ~ dialog.connect('response', self._on_item_available_remove_response, selected_item)
            # ~ dialog.present(self)
        # ~ else:
            # ~ window = self.viewSl.get_root()
            # ~ title = "Action not possible"
            # ~ body = f"{i_title} {item_dsc} can't be removed because it is still being used"
            # ~ self.srvdlg.show_error(title=title, body=body, parent=window)

    # ~ def _on_item_available_remove_response(self, dialog, response, selected_item):
        # ~ item_type = self.config.model
        # ~ i_title = item_type.__title__
        # ~ item_id = selected_item.id.replace('_', ' ')
        # ~ item_dsc = selected_item.title
        # ~ if response == 'apply':
            # ~ self.config.remove_available(selected_item.id)
            # ~ title = f"{i_title} management"
            # ~ body = f"{i_title} {item_dsc} removed from de list of available {item_type.__title_plural__.lower()}"
            # ~ self.srvdlg.show_warning(title=title, body=body, parent=self)
        # ~ else:
            # ~ title = f"{i_title} management"
            # ~ body = f"{i_title} {item_dsc} not deleted from the list of available {item_type.__title_plural__.lower()}"
            # ~ self.srvdlg.show_info(title=title, body=body, parent=self)

    # ~ def _on_item_used_add(self, *args):
        # ~ items_used = self.config.load_used()
        # ~ selected_item = self.viewAv.get_selected()
        # ~ is_used = selected_item.id in items_used
        # ~ item_type = self.config.model
        # ~ i_title = item_type.__title__
        # ~ if not is_used:
            # ~ items_used[selected_item.id] = selected_item.title
            # ~ self.config.save_used(items=items_used)
            # ~ self.update_views()
            # ~ self.srvdlg.show_info(title=f"{i_title} management", body=f"{i_title} {selected_item.title} has been enabled", parent=self)
        # ~ else:
            # ~ self.srvdlg.show_error('Action not possible', f"{i_title} {selected_item.title} is already enabled", parent=self)

class MiAZRepositories(MiAZConfigView):
    """Manage Repositories"""
    __gtype_name__ = 'MiAZRepositories'
    current = None

    def __init__(self, app):
        self.app = app
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Repository')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewRepo(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewRepo(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

    def _on_item_available_add(self, *args):
        window = self.viewSl.get_root()
        title = 'Add a new repository'
        key1 = '<big><b>Repository name</b></big>'
        key2 = 'Select target folder'
        # ~ search_term = self.entry.get_text()
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2)
        this_repo.set_value1('')
        this_repo.set_value2(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS))
        dialog.connect('response', self._on_response_item_available_add, this_repo)
        dialog.present(window)

    def _on_response_item_available_add(self, dialog, response, this_repo):
        srvdlg = self.app.get_service('dialogs')
        if response == 'apply':
            repo_name = this_repo.get_value1()
            repo_path = this_repo.get_value2()
            if len(repo_name) > 0 and os.path.exists(repo_path):
                self.config.add_available(repo_name, repo_path)
                self.log.debug(f"Repo '{repo_name}' added to list of available repositories")
                self.update_views()
            else:
                srvdlg.show_error(title='Action not possible', body='No repository added. Invalid input.\n\nTry again by setting a repository name and a valid target directory', parent=dialog)

    def _on_item_available_edit(self, *args):
        item = self.viewAv.get_selected()
        if item is None:
            return

        item_type = self.config.model
        i_title = item_type.__title__
        parent = self.viewSl.get_root()
        title = 'Add a new repository'
        key1 = '<big><b>Repository name</b></big>'
        key2 = '<big><b>Directory</b></big>'
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2)
        this_repo.disable_key1()
        this_repo.set_value1(item.id)
        this_repo.set_value2(item.title)
        dialog.connect('response', self._on_item_available_edit_description, item, this_repo)
        dialog.present(parent)

    def _on_item_available_edit_description(self, dialog, response, item, this_item):
        item_type = self.config.model
        i_title = item_type.__title__

        if response == 'apply':
            oldkey = item.id
            oldval = item.title
            newkey = this_item.get_value1()
            newval = this_item.get_value2()
            self.log.debug(f"{oldval} == {newval}? {newval != oldval}")
            if newval != oldval:
                items_used = self.config.load_used()
                if oldkey in items_used:
                    items_used[oldkey] = newval
                    self.config.save_used(items_used)
                items_available = self.config.load_available()
                items_available[oldkey] = newval
                self.config.save_available(items_available)
                self.update_views()
                title = f"{i_title} management"
                body = f"Repository {item.id} has changed its directory:\n\nFrom: {oldval}\n\nTo: {newval}"
                self.srvdlg.show_info(title=title, body=body, parent=dialog)
            else:
                title = "Action not possible"
                body = f"Old and new {i_title.lower()} directories are the same"
                self.srvdlg.show_error(title=title, body=body, parent=dialog)

    def _on_item_available_remove(self, *args):
        srvdlg = self.app.get_service('dialogs')
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_available = self.config.load_available()
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')

        is_used = self.config.exists_used(selected_item.id)
        if not is_used:
            del items_available[selected_item.id]
            self.config.save_available(items=items_available)
            self.log.debug(f"{i_title} {item_id} removed from de list of available items")
        else:
            text = _(f'<big>{i_title} {item_id} is still being used</big>')
            window = self.viewSl.get_root()
            title = "Action not possible"
            srvdlg.show_error(title=title, body=text, widget=None, parent=window)

    def _on_item_used_add(self, *args):
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        signal = self.app.get_widget('signal-dd_repo')
        dd_repo.handler_block(signal)
        items_used = self.config.load_used()
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        is_used = selected_item.id in items_used
        item_type = self.config.model
        i_title = item_type.__title__
        if not is_used:
            items_used[selected_item.id] = selected_item.title
            self.config.save_used(items=items_used)
            self.update_views()
            self.log.debug(f"{i_title} {selected_item.id} not used yet. Can be used now")
        else:
            self.log.debug(f"{i_title} {selected_item.id} is already being used")
        dd_repo.handler_unblock(signal)

    def _on_item_used_remove(self, *args):
        # Trick to avoid restart app when repos are enabled/disabled
        ## Block signal "dd_repo > notify::selected-item"
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        signal = self.app.get_widget('signal-dd_repo')
        dd_repo.handler_block(signal)

        items_available = self.config.load_available()
        items_used = self.config.load_used()
        selected_item = self.viewSl.get_selected()
        if selected_item is None:
            return

        item_type = self.config.model
        i_title = item_type.__title__
        items_available[selected_item.id] = selected_item.title
        self.log.debug(f"{i_title} {selected_item.id} added back to the list of available items")
        del items_used[selected_item.id]
        self.log.debug(f"{i_title} {selected_item.id} removed from de list of used items")
        self.config.save_used(items=items_used)
        self.config.save_available(items=items_available)
        self.update_views()
        ## Unblock signal "dd_repo > notify::selected-item"
        dd_repo.handler_unblock(signal)


class MiAZCountries(MiAZConfigView):
    """Manage countries from Repo Settings. Edit disabled"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Country')

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewCountry(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewCountry(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

        # FIXME: allow Countries CRUD operations on demand
        self.btnAvAdd.set_visible(False)
        self.btnAvRemove.set_visible(False)
        self.btnAvEdit.set_visible(False)

    def _update_view_available(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_available()
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon=f'{code}.svg'))
        self.viewAv.update(items)

    def _update_view_used(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_used()
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon=f'{code}.svg'))
        self.viewSl.update(items)


class MiAZGroups(MiAZConfigView):
    """Manage groups from Repo Settings"""
    __gtype_name__ = 'MiAZGroups'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Group')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewGroup(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewGroup(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

class MiAZPeople(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZPeople'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'People')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

class MiAZPeopleSentBy(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZSentBy'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'SentBy')
        # Trick to keep People sync for SentBy/SentTo
        self.config_paired = self.conf['SentTo']
        # ~ self.config_paired.connect('available-updated', self.update_views)

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

class MiAZPeopleSentTo(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZSentTo'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'SentTo')
        # Trick to keep People sync for SentBy/SentTo
        self.config_paired = self.conf['SentBy']
        # ~ self.config_paired.connect('available-updated', self.update_views)

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

class MiAZPurposes(MiAZConfigView):
    """Manage purposes from Repo Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Purpose')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPurpose(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPurpose(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

class MiAZProjects(MiAZConfigView):
    """Manage projects from Repo Settings"""
    __gtype_name__ = 'MiAZProjects'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Project')

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
            title = f"{i_title} management"
            body = f"{i_title} {item_desc} disabled"
            self.srvdlg.show_warning(title=title, body=body, parent=self)

        else:
            text = _(f'{i_title} {item_desc} is still being used by {len(docs)} documents')
            self.log.error(text)
            window = self.viewSl.get_root()
            title = f"{i_title} {item_desc} can't be removed"
            title = "Action not possible"
            items = []
            for doc in docs:
                items.append(File(id=doc, title=os.path.basename(doc)))
            view = MiAZColumnViewDocuments(self.app)
            view.update(items)
            widget = Gtk.Frame()
            widget.set_child(view)
            srvdlg.show_error(title=title, body=text, widget=widget, width=600, height=480, parent=window)

class MiAZUserPlugins(MiAZConfigView):
    """
    Manage user plugins from Repo Settings. Edit disabled
    Only display those plugins found in ENV['APP']['PLUGINS']['USER_INDEX']
    """
    __gtype_name__ = 'MiAZUserPlugins'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app, 'Plugin')
        boxopers = self.app.get_widget('selector-box-operations')
        factory = self.app.get_service('factory')

        # Available view buttons
        btnInfo = factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', callback=self._show_plugin_info, css_classes=['flat'])
        btnInfo.set_valign(Gtk.Align.CENTER)
        btnInfo.set_has_frame(False)
        self.toolbar_buttons_Av.append(btnInfo)

        btnRefresh = factory.create_button(icon_name='io.github.t00m.MiAZ-view-refresh-symbolic', callback=self._refresh_index_plugin_file, css_classes=['flat'])
        btnRefresh.set_valign(Gtk.Align.CENTER)
        self.app.add_widget('repository-settings-plugins-av-btnRefresh', btnRefresh)
        self.toolbar_buttons_Av.append(btnRefresh)

        # Used view buttons
        self.btnConfig = factory.create_button(icon_name='io.github.t00m.MiAZ-config-symbolic', callback=self._configure_plugin_options, css_classes=['flat', 'suggested-action'])
        self.btnConfig.set_valign(Gtk.Align.CENTER)
        # ~ self.btnConfig.set_visible(False)
        self.toolbar_buttons_Sl.append(self.btnConfig)

        # Action to be done when selecting an used plugin
        # ~ selection_model = self.viewSl.cv.get_model()
        # ~ selection_model.connect('selection-changed', self._on_plugin_used_selected)

    def _on_plugin_used_selected(self, selection_model, position, n_items):
        selected_plugin = selection_model.get_selected_item()
        plugin_id = f"plugin-{selected_plugin.id}"
        plugin = self.app.get_widget(plugin_id)
        has_settings = False
        if plugin is not None:
            has_settings = hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings'))
        self.btnConfig.set_visible(has_settings)

    def _refresh_index_plugin_file(self, *args):
        threading.Thread(target=self.download_plugins, daemon=True).start()

    def download_plugins(self):
        banner = self.app.get_widget('repository-settings-banner')
        banner.set_revealed(True)
        banner.set_button_label('')
        banner.set_title("")
        toolbarAv = self.app.get_widget('settings-repository-toolbar-av')
        toolbarSl = self.app.get_widget('settings-repository-toolbar-sl')
        toolbarAv.set_sensitive(False)
        toolbarSl.set_sensitive(False)

        util = self.app.get_service('util')
        ENV = self.app.get_env()
        source = ENV['APP']['PLUGINS']['SOURCE']
        url_base = ENV['APP']['PLUGINS']['REMOTE_INDEX']
        url = url_base % source
        url_plugin_base = ENV['APP']['PLUGINS']['DOWNLOAD']
        user_plugins_dir = ENV['LPATH']['PLUGINS']

        try:
            response = requests.get(url)
            response.raise_for_status()
            plugin_index = response.json()
            util.json_save(ENV['APP']['PLUGINS']['USER_INDEX'], plugin_index)
            plugin_system = self.app.get_service('plugin-system')
            user_plugins = plugin_system.get_user_plugins()
        except Exception as error:
            # FIXME: display error dialog
            self.log.error(error)
            return

        urls = []
        plugin_list = []
        for pid in plugin_index:
            url_plugin = url_plugin_base % (source, pid)
            urls.append(url_plugin)
            self.log.debug(f"Appending plugin {url_plugin}")
        total_files = len(urls)

        for i, url_plugin in enumerate(urls):
            if hasattr(self, 'cancelled') and self.cancelled:
                break

            # Update progress
            progress = (i + 1) / total_files
            self.log.debug(f"Downloading plugin from {url_plugin}")
            GLib.idle_add(self.update_progress, progress, f"Downloading file {i+1}/{total_files}")

            try:
                util.download_and_unzip(url_plugin, user_plugins_dir)
                # ~ time.sleep(1) # Comment above line and disable this one for testing
            except HTTPError as http_error:
                self.log.error(f"HTTP error occurred: {http_error}")
            except Exception as error:
                self.log.error(f"Another error occurred: {error}")

    def update_progress(self, fraction, text):
        percentage = int(fraction*100)
        banner = self.app.get_widget('repository-settings-banner')
        banner.set_title(f"{text} ({percentage}%) done")
        if fraction == 1.0:
            banner = self.app.get_widget('repository-settings-banner')
            banner.set_revealed(True)
            banner.set_title("One or more plugins were updated. Application restart needed")
            banner.set_button_label('Restart')
            self.update_views()

    def _configure_plugin_options(self, *args):
        selected_plugin = self.viewSl.get_selected()
        if selected_plugin is None:
            return
        self.log.debug(f"Open configuration dialog for plugin {selected_plugin.id}")
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        plugin_system = self.app.get_service('plugin-system')
        user_plugins = util.json_load(ENV['APP']['PLUGINS']['USER_INDEX'])
        plugin_id = f"plugin-{selected_plugin.id}"
        plugin = self.app.get_widget(plugin_id)
        if plugin is not None:
            if hasattr(plugin, 'show_settings') and callable(getattr(plugin, 'show_settings')):
                try:
                    plugin.show_settings(widget=self)
                except Exception as error:
                    self.log.error(error)
                    raise
            else:
                self.log.info(f"Plugin {selected_plugin.id} doesn't have a settings dialog")
        else:
            self.log.error(f"Can't find plugin object for {plugin_id}!!")

    def update_user_plugins(self):
        ENV = self.app.get_env()
        plugin_system = self.app.get_service('plugin-system')
        plugin_system.rescan_plugins()
        view = self.app.get_widget('app-settings-plugins-user-view')
        items = []
        item_type = Plugin
        for plugin in plugin_system.plugins:
            ptype = plugin_system.get_plugin_type(plugin)
            if ptype == MiAZPluginType.USER:
                base_dir = plugin.get_name()
                module_name = plugin.get_module_name()
                plugin_path = os.path.join(ENV['LPATH']['PLUGINS'], base_dir, f"{module_name}.plugin")
                if os.path.exists(plugin_path):
                    title = plugin.get_description()
                    items.append(item_type(id=module_name, title=title))
        self.update_views()

    def plugins_updated(self, *args):
        self._update_view_available()

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewPlugin(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPlugin(self.app)
        self._add_columnview_used(self.viewSl)

    def _on_item_used_remove(self, *args):
        selected_plugin = self.viewSl.get_selected()
        if selected_plugin is None:
            return

        ENV = self.app.get_env()
        ENV['APP']['STATUS']['RESTART_NEEDED'] = True
        self.config.remove_used(selected_plugin.id)
        banner = self.app.get_widget('repository-settings-banner')
        banner.set_revealed(True)
        self.update_views()

    def _on_item_used_add(self, *args):
        workflow = self.app.get_service('workflow')
        plugin_manager = self.app.get_service('plugin-system')
        plugins_used = self.config.load_used()
        selected_plugin = self.viewAv.get_selected()
        if selected_plugin is None:
            return

        plugin_used = self.config.exists_used(selected_plugin.id)
        item_type = self.config.model
        i_title = item_type.__title__
        if not plugin_used:
            util = self.app.get_service('util')
            ENV = self.app.get_env()
            user_plugins = util.json_load(ENV['APP']['PLUGINS']['USER_INDEX'])
            try:
                plugin_module = user_plugins[selected_plugin.id]['Module']
            except KeyError as key:
                self.log.error(f"Plugin {key} not found in {ENV['APP']['PLUGINS']['USER_INDEX']}")
                return
            plugins_used[selected_plugin.id] = selected_plugin.title
            plugin = plugin_manager.get_plugin_info(plugin_module)
            if not plugin.is_loaded():
                plugin_manager.load_plugin(plugin)
                self.config.save_used(items=plugins_used)
                self.log.debug(f"{i_title} {selected_plugin.id} activated")
                workflow.switch_start()
        else:
            self.log.warning(f"{i_title} '{selected_plugin.id}' was already activated. Nothing to do")
        self.update_views()

    def _show_plugin_info(self, *args):
        util = self.app.get_service('util')
        ENV = self.app.get_env()
        plugin_system = self.app.get_service('plugin-system')
        selected_plugin = self.viewAv.get_selected()
        if selected_plugin is None:
            return
        user_plugins = util.json_load(ENV['APP']['PLUGINS']['USER_INDEX'])
        plugin_info = user_plugins[selected_plugin.id]

        # Build info dialog
        dialog = Adw.PreferencesDialog()
        dialog.set_title('Plugin info')
        page_title = _('Properties')
        page_icon = "io.github.t00m.MiAZ-dialog-information-symbolic"
        page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        dialog.add(page)
        group = Adw.PreferencesGroup()
        group.set_title('Data Sheet')
        page.add(group)

        # Add plugin info as key/value rows
        for key in plugin_info:
            row = Adw.ActionRow(title=_(f'<b>{key}</b>'))
            label = Gtk.Label.new(plugin_info[key])
            row.add_suffix(label)
            group.add(row)
        dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)
        dialog.present(self.viewAv.get_root())
