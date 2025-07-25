#!/usr/bin/python3
# File: configview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom selector views to manage configuration

import os
import glob
from gettext import gettext as _
import threading

import requests

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Plugin
from MiAZ.frontend.desktop.services.pluginsystem import MiAZPluginType
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewCountry
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewGroup
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPurpose
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPerson
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
        i_title = _(item_type.__title__)
        i_title_plural = _(item_type.__title_plural__)
        tooltip=_('Enable ') + i_title.lower()
        self.btnAddToUsed.set_tooltip_markup(tooltip)
        tooltip=_('Disable ') + i_title.lower()
        self.btnRemoveFromUsed.set_tooltip_markup(tooltip)
        self.dialog_title = _('{item_types} management').format(item_types=i_title_plural)

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
        title = self.dialog_title + _(' : Add')
        key1 = _('<b>Repository name</b>')
        key2 = _('Select target folder')
        # ~ search_term = self.entry.get_text()
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2)
        this_repo.set_value1('')
        this_repo.set_value2(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS))
        dialog.connect('response', self._on_response_item_available_add, this_repo, window)
        dialog.present(window)

    def _on_response_item_available_add(self, dialog, response, this_repo, parent):
        srvdlg = self.app.get_service('dialogs')
        title = self.dialog_title
        if response == 'apply':
            repo_name = this_repo.get_value1()
            repo_path = this_repo.get_value2()
            if len(repo_name) > 0 and os.path.exists(repo_path):
                self.config.add_available(repo_name, repo_path)
                body = _('Repository added to list of available repositories')
                self.log.debug(body)
                self.update_views()
                srvdlg.show_info(title=title, body=body, parent=parent)
            else:
                body1 = _('<b>Action not possible</b>')
                body2 = _('No repository added. Invalid input.\n\nTry again by setting a repository name and a valid target directory')
                body = body1 + '\n' + body2
                srvdlg.show_error(title=title, body=body, parent=parent)

    def _on_item_available_edit(self, *args):
        item = self.viewAv.get_selected()
        if item is None:
            return

        item_type = self.config.model
        i_title = item_type.__title__
        parent = self.viewSl.get_root()
        title = self.dialog_title + _(' : Edit')
        key1 = _('<b>Repository name</b>')
        key2 = _('Select target folder')
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2)
        this_repo.disable_key1()
        this_repo.set_value1(item.id)
        this_repo.set_value2(item.title)
        dialog.connect('response', self._on_item_available_edit_description, item, this_repo, parent)
        dialog.present(parent)

    def _on_item_available_edit_description(self, dialog, response, item, this_item, parent):
        item_type = self.config.model
        i_title = item_type.__title__

        if response == 'apply':
            oldkey = item.id
            oldval = item.title
            newkey = this_item.get_value1()
            newval = this_item.get_value2()
            self.log.debug(f"{oldval} == {newval}? {newval != oldval}")
            title = self.dialog_title
            if newval != oldval:
                items_used = self.config.load_used()
                if oldkey in items_used:
                    items_used[oldkey] = newval
                    self.config.save_used(items_used)
                items_available = self.config.load_available()
                items_available[oldkey] = newval
                self.config.save_available(items_available)
                self.update_views()
                body = _('Repository target folder updated')
                self.srvdlg.show_info(title=title, body=body, parent=parent)
            else:
                body1 = _('<b>Action not possible</b>')
                body2 = _('Repository target folder not updated')
                body = body1 + '\n' + body2
                self.srvdlg.show_error(title=title, body=body, parent=parent)

    def _on_item_available_remove(self, button, data=None):
        parent=button
        srvdlg = self.app.get_service('dialogs')
        parent = self.viewAv.get_root()
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_available = self.config.load_available()
        item_type = self.config.model
        i_title = _(item_type.__title__)
        item_id = selected_item.id.replace('_', ' ')
        is_used = self.config.exists_used(selected_item.id)
        title = self.dialog_title
        if not is_used:
            del items_available[selected_item.id]
            self.config.save_available(items=items_available)
            body = _('{title} {id} removed from de list of available items').format(title=i_title, id=item_id)
            self.log.debug(body)
            srvdlg.show_warning(title=title, body=body, widget=None, parent=parent)
        else:
            title = self.dialog_title
            body1 = _('<b>Action not possible</b>')
            body2 = _('{title} {id} is still being used').format(title=i_title, id=item_id)
            body = body1 + '\n' + body2
            srvdlg.show_error(title=title, body=body, widget=None, parent=parent)

    def _on_item_used_add(self, *args):
        srvdlg = self.app.get_service('dialogs')
        title = self.dialog_title

        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        if dd_repo is not None:
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
            body = _('{title} {item} ready to be used').format(title=i_title, item=selected_item.id)
            self.log.debug(body)
        else:
            body = f"{i_title} {selected_item.id} is already being used"
            self.log.debug(body)
        if dd_repo is not None:
            dd_repo.handler_unblock(signal)

        if len(self.config.load_used()) == 1:
            config = self.app.get_config_dict()
            config['App'].set('current', selected_item.id)
            self.log.debug(f"Repository {selected_item.id} enabled")
            workflow = self.app.get_service('workflow')
            workflow.switch_start()
            body=_('{title} {item} set as default').format(title=i_title, item=selected_item.id)
            self.log.info(body)
        srvdlg.show_info(title=title, body=body, parent=self)

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

class MiAZUserPlugins(MiAZConfigView):
    """
    Manage user plugins from Repo Settings. Edit disabled
    Only display User plugins found in ENV['APP']['PLUGINS']['USER_INDEX']
    """
    __gtype_name__ = 'MiAZUserPlugins'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app, 'Plugin')
        sid_u = GObject.signal_lookup('plugins-downloaded', MiAZUserPlugins)
        if sid_u == 0:
            GObject.signal_new('plugins-downloaded',
                                MiAZUserPlugins,
                                GObject.SignalFlags.RUN_LAST, None, ())
        boxopers = self.app.get_widget('selector-box-operations')
        factory = self.app.get_service('factory')
        util = self.app.get_service('util')

        # Available view buttons
        btnInfo = factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', callback=self._show_plugin_info, css_classes=['linked'])
        btnInfo.set_valign(Gtk.Align.CENTER)
        self.toolbar_buttons_Av.append(btnInfo)

        btnRefresh = factory.create_button(icon_name='io.github.t00m.MiAZ-view-refresh-symbolic', callback=self._refresh_index_plugin_file, css_classes=['linked'])
        btnRefresh.set_valign(Gtk.Align.CENTER)
        self.app.add_widget('repository-settings-plugins-av-btnRefresh', btnRefresh)
        self.toolbar_buttons_Av.append(btnRefresh)

        # Used view buttons
        self.btnConfig = factory.create_button(icon_name='io.github.t00m.MiAZ-config-symbolic', callback=self._configure_plugin_options)
        self.btnConfig.set_valign(Gtk.Align.CENTER)
        # ~ self.btnConfig.set_visible(False)
        self.toolbar_buttons_Sl.append(self.btnConfig)

        # Setup plugin (sub)categories dropdowns
        boxFilters = factory.create_box_vertical(margin=0, spacing=6)
        self.dpdCats = factory.create_dropdown(item_type=Plugin)
        self.dpdSubcats = factory.create_dropdown(item_type=Plugin)
        boxFilters.append(self.dpdCats)
        boxFilters.append(self.dpdSubcats)
        self.boxLeft.prepend(boxFilters)

        # ~ self.dpdCats.connect("notify::selected-item", self._on_plugin_category_selected)

        # Action to be done when selecting an used plugin
        # ~ selection_model = self.viewSl.cv.get_model()
        # ~ selection_model.connect('selection-changed', self._on_plugin_used_selected)

        # Fill-in dropdowns
        ENV = self.app.get_env()
        try:
            self.user_plugins = util.json_load(ENV['APP']['PLUGINS']['USER_INDEX'])
        except Exception:
            self.user_plugins = {}

        cat_items = []
        model_filter = self.dpdCats.get_model()
        model_sort = model_filter.get_model()
        model_cats = model_sort.get_model()
        model_cats.remove_all()
        set_cats = set()
        model_cats.append(Plugin(id='all', title=_('All categories')))
        for plugin in self.user_plugins:
            category = self.user_plugins[plugin]['Category']
            if category not in set_cats:
                model_cats.append(Plugin(id=category, title=_(category)))
                set_cats.add(category)

        self.dpdCats.connect("notify::selected-item", self._on_plugin_category_selected)
        self.dpdSubcats.connect("notify::selected-item", self._on_plugin_subcategory_selected)

        if len(set_cats) > 0:
            self.dpdCats.set_selected(0)
            self.log.debug(f"Select first category")
            self._on_plugin_category_selected()

    def _do_filter_view(self, item, filter_list_model):
        plugin = item.id
        selected_cat = self.dpdCats.get_selected_item()
        selected_subcat = self.dpdSubcats.get_selected_item()


        try:
            category = self.user_plugins[plugin]['Category']
        except KeyError:
            selected_cat = None

        try:
            subcategory = self.user_plugins[plugin]['Subcategory']
        except KeyError:
            selected_subcat = None

        chunk = self.searchentry.get_text().upper()
        string = f"{item.id}-{item.title}"

        # Check filters
        text_filter = chunk in string.upper()

        if selected_cat is None:
            cat_matches = True
        elif selected_cat.id == 'all':
            cat_matches = True
        else:
            cat_matches = category == selected_cat.id

        if  selected_subcat is None:
            subcat_matches = True
        elif selected_subcat.id == 'all':
            subcat_matches = True
        else:
            subcat_matches = subcategory == selected_subcat.id

        match = text_filter and cat_matches and subcat_matches
        return match

    def _on_plugin_category_selected(self, *args):
        selected_category = self.dpdCats.get_selected_item()
        if selected_category is None:
            self.log.warning("No category selected")
            return
        subcat_items = []
        model_filter = self.dpdSubcats.get_model()
        model_sort = model_filter.get_model()
        model_subcats = model_sort.get_model()
        model_subcats.remove_all()

        set_subcats = set()
        model_subcats.append(Plugin(id='all', title=_('All subcategories')))
        for plugin in self.user_plugins:
            category = self.user_plugins[plugin]['Category']
            if category == selected_category.id:
                subcategory = self.user_plugins[plugin]['Subcategory']
                if subcategory not in set_subcats:
                    item = Plugin(id=subcategory, title=_(subcategory))
                    model_subcats.append(item)
                    set_subcats.add(subcategory)
        self.dpdSubcats.set_selected(0)
        self._on_plugin_subcategory_selected()

    def _on_plugin_subcategory_selected(self, *args):
        self.viewAv.refilter()
        self.viewSl.refilter()

    def _on_item_available_add(self, *args):
        factory = self.app.get_service('factory')
        factory.create_filechooser_for_plugins(self._on_item_available_add_response, parent=self)

    def _on_item_available_add_response(self, dialog, result):
        title = self.dialog_title
        try:
            ENV = self.app.get_env()
            util = self.app.get_service('util')
            pluginsystem = self.app.get_service('plugin-system')
            filepath = dialog.open_finish(result)
            plugin_file = filepath.get_path()
            zip_archive = util.unzip(plugin_file, ENV['LPATH']['PLUGINS'])
            pluginsystem.create_user_plugin_index()
            self.searchentry.set_text('')
            self.searchentry.activate()
            plugin_dirname = zip_archive.namelist()[0]
            plugin_path = glob.glob(os.path.join(ENV['LPATH']['PLUGINS'], plugin_dirname, '*.plugin'))[0]
            plugin_info = pluginsystem.get_plugin_attributes(plugin_path)
            plugin_name = plugin_info['Name']
            plugin_version = plugin_info['Version']
            body1 = _('<b>Import plugin</b>')
            body2 = _('Plugin {plugin_name} v{plugin_version} imported successfully').format(plugin_name=plugin_name, plugin_version=plugin_version)
            body = body1 + '\n' + body2
            self.srvdlg.show_info(title='Import plugin', body=body, parent=self)
        except Exception as error:
            body1 = _('<b>Action not possible</b>')
            body2 = _('Error: {error}').format(error=error)
            body = body1 + '\n' + body2
            self.srvdlg.show_error(title=title, body=error, parent=self)
            self.log.error(f"Error import plugin: {error}")

    def _on_item_available_remove(self, *args):
        util = self.app.get_service('util')
        selected_item = self.viewAv.get_selected()
        if selected_item is None:
            return

        items_available = self.config.load_available()
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')
        item_dsc = selected_item.title

        items_used = self.config.load_used()
        is_used = selected_item.id in items_used
        self.log.debug(f"Is '{selected_item.id}' used? {is_used}")
        title = self.dialog_title
        if not is_used:
            body = _('You are about to delete <i>{title} {desc}</i>.\n\nAre you sure?').format(title=i_title.lower(), desc=item_dsc)
            dialog = self.srvdlg.show_question(title=title, body=body)
            dialog.connect('response', self._on_item_available_remove_response, selected_item)
            dialog.present(self)
        else:
            item_type = self.config.model
            i_title = _(item_type.__title__)
            window = self.viewAv.get_root()
            title = self.dialog_title
            body1 = _('<b>Action not possible</b>')
            body2 = _('{title} <i>{desc}</i> is still enabled.\nPlease, disable it first before deleting it.').format(title=i_title, desc=item_dsc)
            body = body1 + '\n' + body2
            item_desc = selected_item.title.replace('_', ' ')
            widget = None
            srvdlg = self.app.get_service('dialogs')
            srvdlg.show_error(title=title, body=body, widget=widget, parent=window)

    def _on_item_available_remove_response(self, dialog, response, selected_item):
        ENV = self.app.get_env()
        item_type = self.config.model
        i_title = item_type.__title__
        item_id = selected_item.id.replace('_', ' ')
        item_dsc = selected_item.title
        title = self.dialog_title
        if response == 'apply':
            self.config.remove_available(selected_item.id)
            plugin_path = os.path.join(ENV['LPATH']['PLUGINS'], selected_item.id)
            if os.path.exists(plugin_path):
                util = self.app.get_service('util')
                util.directory_remove(plugin_path)
            self.searchentry.set_text('')
            self.searchentry.activate()
            body = _('{title} {desc}  removed from de list of available {item_types}').format(title=i_title, desc=item_dsc, item_types=item_type.__title_plural__.lower())
            self.srvdlg.show_warning(title=title, body=body, parent=self)
        else:
            body = _('{title} {desc}  not removed from de list of available {item_types}').format(title=i_title, desc=item_dsc, item_types=item_type.__title_plural__.lower())
            self.srvdlg.show_info(title=title, body=body, parent=self)

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
        # FIXME: set toolbar sensitivity to False
        banner = self.app.get_widget('repository-settings-banner')
        banner.set_revealed(True)
        banner.set_button_label('')
        banner.set_title("")

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
        srvdlg = self.app.get_service('dialogs')
        title = "Plugin management"
        percentage = int(fraction*100)
        banner = self.app.get_widget('repository-settings-banner')
        banner.set_title(f"{text} ({percentage}%) done")
        if fraction == 1.0:
            banner = self.app.get_widget('repository-settings-banner')
            banner.set_revealed(True)
            banner.set_title("One or more plugins were updated. Application restart needed")
            banner.set_button_label('Restart')
            pluginsystem = self.app.get_service('plugin-system')
            pluginsystem.create_user_plugin_index()
            # ~ self.update_user_plugins()
            body = "Plugins updated"
            self.log.info(body)
            srvdlg.show_info(title=title, body=body, parent=self)

    def _configure_plugin_options(self, *args):
        srvdlg = self.app.get_service('dialogs')
        title = 'Plugin management'
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
                    body = error
                    self.log.error(error)
                    srvdlg.show_error(title=title, body=body, parent=self)
            else:
                body = f"Plugin {selected_plugin.id} doesn't have a settings dialog"
                self.log.warning(body)
                srvdlg.show_warning(title=title, body=body, parent=self)
        else:
            body = f"Can't find plugin object for {plugin_id}!!"
            self.log.error(body)
            srvdlg.show_error(title=title, body=body, parent=self)

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
                    items.append(item_type(id=module_name, title=_(title)))
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
