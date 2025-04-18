#!/usr/bin/python3
# File: configview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom selector views to manage configuration

import os
import glob
from gettext import gettext as _

from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
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
from MiAZ.backend.pluginsystem import MiAZPluginType
from MiAZ.backend.models import File


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    config_for = None

    def __init__(self, app, config_name=None):
        super(MiAZSelector, self).__init__(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZConfigView')
        self.repository = self.app.get_service('repo')
        self.config_name = config_name
        self.conf = self.app.get_config_dict()
        self.config = self.conf[config_name]
        self._setup_view_finish()
        self.config.connect('used-updated', self.update_views)
        self.config.connect('available-updated', self.update_views)
        self.set_vexpand(True)
        self.log.debug(f"Configview for {config_name} initialited")

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
        self.viewSl = MiAZColumnViewRepo(self.app)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

    def _on_item_available_add(self, *args):
        window = self.viewSl.get_root()
        title = 'Add a new repository'
        key1 = '<big><b>Repository name</b></big>'
        key2 = '<big><b>Folder</b></big>'
        search_term = self.entry.get_text()
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2)
        this_repo.set_value1(search_term)
        dialog.connect('response', self._on_response_item_available_add, this_repo)
        dialog.present(window)

    def _on_response_item_available_add(self, dialog, response, this_repo):
        if response == 'apply':
            repo_name = this_repo.get_value1()
            repo_path = this_repo.get_value2()
            if len(repo_name) > 0 and os.path.exists(repo_path):
                self.config.add_available(repo_name, repo_path)
                self.log.debug(f"Repo '{repo_name}' added to list of available repositories")
                self.update_views()
            else:
                self.log.debug("No repository added. Invalid data")

    def _on_item_available_rename(self, item):
        if item is None:
            return

        repo_name = item.id
        repo_path = item.title
        self.log.debug(f"Renaming Repository '{repo_name}' located in {repo_path}")
        window = self.viewSl.get_root()
        this_repo = MiAZDialogAddRepo(self.app)
        title = _('Edit repository')
        key1 = '<big><b>Repository name</b></big>'
        key2 = '<big><b>Folder</b></big>'
        dialog = this_repo.create(title=title, key1=key1, key2=key2)
        this_repo.set_value1(repo_name.replace('_', ' '))
        this_repo.set_value2(repo_path)
        entry1 = this_repo.get_entry_key1()
        entry1.set_sensitive(False)
        dialog.connect('response', self._on_response_item_available_rename, item, this_repo)
        dialog.present(window)

    def _on_item_available_remove(self, *args):
        srvdlg = self.app.get_service('dialogs')
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_available = self.config.load_available()
        item_type = self.config.model
        i_title = item_type.__title__

        is_used = self.config.exists_used(selected_item.id)
        if not is_used:
            del items_available[selected_item.id]
            self.config.save_available(items=items_available)
            self.log.debug(f"{i_title} {selected_item.id} removed from de list of available items")
        else:
            dtype = "error"
            text = _(f'<big>{i_title} {selected_item.id} is still being used</big>')
            window = self.viewSl.get_root()
            dtype = 'error'
            title = "Action not possible"
            dialog = srvdlg.create(enable_response=False, dtype=dtype, title=title, body=text, widget=None)
            dialog.present(window)

    def _on_item_used_add(self, *args):
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

    def _on_item_used_remove(self, *args):
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
        self.viewSl = MiAZColumnViewCountry(self.app)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

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
        self.viewSl = MiAZColumnViewGroup(self.app)
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
        self.viewSl = MiAZColumnViewPerson(self.app)
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
        self.viewSl = MiAZColumnViewPerson(self.app)
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
        self.viewSl = MiAZColumnViewPerson(self.app)
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
        self.viewSl = MiAZColumnViewPurpose(self.app)
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
        self.viewSl = MiAZColumnViewProject(self.app)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

    def _on_item_available_remove(self, *args):
        srvdlg = self.app.get_service('dialogs')
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_available = self.config.load_available()
        item_type = self.config.model
        i_title = item_type.__title__

        is_used = self.config.exists_used(selected_item.id)
        if not is_used:
            del items_available[selected_item.id]
            self.config.save_available(items=items_available)
            self.log.debug(f"{i_title} {selected_item.id} removed from de list of available items")
        else:
            dtype = "error"
            text = _(f'{i_title} {selected_item.id} is still being used')
            window = self.viewSl.get_root()
            dtype = 'error'
            title = f"{i_title} {selected_item.id} can't be removed"
            title = "Action not possible"
            dialog = srvdlg.create(enable_response=False, dtype=dtype, title=title, body=text, width=600, height=480)
            dialog.present(window)

    def _on_item_used_add(self, *args):
        items_used = self.config.load_used()
        selected_item = self.viewAv.get_selected()
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

    def _on_item_used_remove(self, *args):
        self.log.debug("_on_item_used_remove:: start")
        items_available = self.config.load_available()
        items_used = self.config.load_used()
        selected_item = self.viewSl.get_selected()
        item_type = self.config.model
        i_title = item_type.__title__
        srvprj = self.app.get_service('Projects')
        srvdlg = self.app.get_service('dialogs')
        docs = srvprj.docs_in_project(selected_item.id)
        if len(docs) == 0:
            self.log.debug("_on_item_used_remove:: no dependencies")
            items_available[selected_item.id] = selected_item.title
            self.log.debug(f"{i_title} {selected_item.id} added back to the list of available items")
            del items_used[selected_item.id]
            self.log.debug(f"{i_title} {selected_item.id} removed from de list of used items")
            self.config.save_used(items=items_used)
            self.config.save_available(items=items_available)
            self.update_views()
        else:
            text = _(f'{i_title} {selected_item.title} is still being used by {len(docs)} docs')
            self.log.error(text)
            window = self.viewSl.get_root()
            dtype = 'error'
            title = f"{i_title} {selected_item.title} can't be removed"
            title = "Action not possible"
            items = []
            for doc in docs:
                items.append(File(id=doc, title=os.path.basename(doc)))
            view = MiAZColumnViewDocuments(self.app)
            view.update(items)
            dialog = srvdlg.create(enable_response=False, dtype=dtype, title=title, body=text, widget=view, width=600, height=480)
            dialog.present(window)


class MiAZUserPlugins(MiAZConfigView):
    """Manage user plugins from Repo Settings. Edit disabled"""
    __gtype_name__ = 'MiAZUserPlugins'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app, 'Plugin')
        self._update_view_available()
        self._update_view_used()

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
            user_plugins = util.json_load(ENV['APP']['PLUGINS']['LOCAL_INDEX'])
            plugin_module = user_plugins[selected_plugin.id]['Module']
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


