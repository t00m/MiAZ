# File: configview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Custom selector views to manage configuration

import os
import glob
from gettext import gettext as _
from gi.repository import Adw
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.util import humanize_value
from MiAZ.backend.models import Plugin, Repository
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewCountry
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewGroup
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPurpose
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPerson
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewRepo
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.services.dialogs import MiAZDialogAddRepo
from MiAZ.frontend.desktop.services.pluginsystem import (
    format_load_failure_banner, plugin_version as pluginsystem_version)


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    config_for = None

    def __init__(self, app, config_name=None, custom_config=None):
        super().__init__(app)
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
        self._sid_used = None
        self._sid_avail = None
        # A sibling config that shares this one's available pool (SentBy and
        # SentTo both use people-available.json). Subclasses set it; the base
        # connects to its 'available-updated' so both views refresh together.
        self.config_paired = None
        self._sid_paired = None
        self._update_views_pending = False
        # Connect signals only while the widget is on screen so stale instances
        # opened from previous settings windows don't keep firing updates.
        self.connect('map', self._on_configview_mapped)
        self.connect('unmap', self._on_configview_unmapped)
        self.set_vexpand(True)
        item_type = self.config.model
        i_title = _(item_type.__title__)
        i_title_plural = _(item_type.__title_plural__)
        tooltip=_('Enable ') + i_title.lower()
        self.btnAddToUsed.set_tooltip_markup(tooltip)
        tooltip=_('Disable ') + i_title.lower()
        self.btnRemoveFromUsed.set_tooltip_markup(tooltip)
        self.dialog_title = _('{item_types} management').format(item_types=i_title_plural)

    def _on_configview_mapped(self, *args):
        if self._sid_used is None:
            self._sid_used = self.config.connect('used-updated', self._schedule_update_views)
        if self._sid_avail is None:
            self._sid_avail = self.config.connect('available-updated', self._schedule_update_views)
        # Refresh this view when the paired config changes the shared available
        # pool, so a person added under Sender shows up under Recipient and back.
        if self.config_paired is not None and self._sid_paired is None:
            self._sid_paired = self.config_paired.connect('available-updated', self._schedule_update_views)
        self.update_views()

    def _on_configview_unmapped(self, *args):
        if self._sid_used is not None:
            self.config.disconnect(self._sid_used)
            self._sid_used = None
        if self._sid_avail is not None:
            self.config.disconnect(self._sid_avail)
            self._sid_avail = None
        if self._sid_paired is not None:
            self.config_paired.disconnect(self._sid_paired)
            self._sid_paired = None

    def _schedule_update_views(self, *args):
        if not self._update_views_pending:
            self._update_views_pending = True
            GLib.idle_add(self._deferred_update_views)

    def _deferred_update_views(self):
        self._update_views_pending = False
        self.update_views()
        return False

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

    def _add_config_menubutton(self, name: str):
        """Add an Export/Import menu button to the available-items toolbar.

        Export writes the available pool of this configuration type to a JSON
        file; import merges a JSON file back into it. Available to every config
        type because each subclass calls this from _setup_view_finish.
        """
        factory = self.app.get_service('factory')
        btn_export = factory.create_button(
            icon_name='document-save-symbolic', title=_('Export…'),
            callback=self._on_config_export)
        btn_import = factory.create_button(
            icon_name='document-open-symbolic', title=_('Import…'),
            callback=self._on_config_import)
        menubutton = factory.create_button_popover(
            icon_name='open-menu-symbolic', widgets=[btn_export, btn_import])
        self.toolbar_buttons_Av.append(menubutton)

    def _on_config_export(self, *args):
        parent = self.get_root()
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Export {name} configuration').format(name=self.config.config_for))
        dialog.set_initial_name(f'{self.config.config_for}.json')
        dialog.save(parent, None, self._on_config_export_selected)

    def _on_config_export_selected(self, dialog, result):
        srvdlg = self.app.get_service('dialogs')
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return  # cancelled
        path = gfile.get_path()
        try:
            self.app.get_service('util').json_save(path, self.config.load_available())
            srvdlg.show_toast(_('Configuration exported: {name}').format(
                name=os.path.basename(path)))
        except Exception as error:
            self.log.error(f"Config export failed: {error}")
            srvdlg.show_toast(_('Export failed: ') + str(error))

    def _on_config_import(self, *args):
        parent = self.get_root()
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_('Import {name} configuration').format(name=self.config.config_for))
        dialog.open(parent, None, self._on_config_import_selected)

    def _on_config_import_selected(self, dialog, result):
        srvdlg = self.app.get_service('dialogs')
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return  # cancelled
        path = gfile.get_path()
        try:
            imported = self.app.get_service('util').json_load(path)
        except Exception as error:
            self.log.error(f"Config import failed to read {path}: {error}")
            srvdlg.show_toast(_('Import failed: could not read the file'))
            return
        if not isinstance(imported, dict):
            srvdlg.show_toast(_('Import failed: unexpected file format'))
            return
        # Merge into the existing pool rather than replacing it, so an import
        # adds entries without dropping the ones already configured.
        available = self.config.load_available()
        available.update(imported)
        self.config.save_available(items=available)
        srvdlg.show_toast(_('Imported {n} {name} items').format(
            n=len(imported), name=self.config.config_for))


class MiAZRepositories(MiAZConfigView):
    """Manage Repositories"""
    __gtype_name__ = 'MiAZRepositories'
    current = None

    def __init__(self, app):
        super().__init__(app, 'Repository')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewRepo(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewRepo(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

    def _update_view_available(self):
        # Repository values are dicts ({'path': ..., 'description': ...}), so the
        # generic base implementation (title=_(items[key])) does not apply here.
        items_available = []
        items = self.config.load_available()
        used = self.config.load_used()
        for key in items:
            if key not in used:
                entry = items[key]
                items_available.append(Repository(
                    id=key,
                    title=entry.get('path', ''),
                    description=entry.get('description', '')))
        self.viewAv.update(items_available)

    def _update_view_used(self, items=None):
        items_used = []
        items = self.config.load_used()
        for key in items:
            entry = items[key]
            items_used.append(Repository(
                id=key,
                title=entry.get('path', ''),
                description=entry.get('description', '')))
        self.viewSl.update(items_used)

    def _on_item_available_add(self, *args):
        window = self.viewSl.get_root()
        title = _('Add repository')
        key1 = _('Repository name')
        key2 = _('Location')
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2, action_label=_('Add'))
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
            repo_desc = this_repo.get_value3()
            if len(repo_name) > 0 and os.path.exists(repo_path):
                self.config.set_repo_available(repo_name, repo_path, repo_desc)
                body = _('Repository added to list of available repositories')
                self.log.debug(body)
                srvdlg.show_toast(body)
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
        title = _('Edit repository')
        key1 = _('Repository name')
        key2 = _('Location')
        this_repo = MiAZDialogAddRepo(self.app)
        dialog = this_repo.create(title=title, key1=key1, key2=key2, action_label=_('Save'))
        this_repo.disable_key1()
        this_repo.set_value1(item.id)
        this_repo.set_value2(item.title)
        this_repo.set_value3(item.description)
        dialog.connect('response', self._on_item_available_edit_description, item, this_repo, parent)
        dialog.present(parent)

    def _on_item_available_edit_description(self, dialog, response, item, this_item, parent):
        item_type = self.config.model
        i_title = item_type.__title__

        if response == 'apply':
            oldkey = item.id
            oldpath = item.title
            olddesc = item.description
            newpath = this_item.get_value2()
            newdesc = this_item.get_value3()
            self.log.debug(f"path {oldpath} -> {newpath}; desc {olddesc} -> {newdesc}")
            title = self.dialog_title
            if newpath != oldpath or newdesc != olddesc:
                if self.config.exists_used(oldkey):
                    self.config.set_repo_used(oldkey, newpath, newdesc)
                self.config.set_repo_available(oldkey, newpath, newdesc)
                body = _('Repository updated')
                self.srvdlg.show_toast(body)
            else:
                body1 = _('<b>Action not possible</b>')
                body2 = _('Repository not updated')
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
        signal = self.app.get_widget('signal-dd_repo') if dd_repo is not None else None
        if dd_repo is not None and signal is not None:
            dd_repo.handler_block(signal)
        try:
            items_used = self.config.load_used()
            selected_item = self.viewAv.get_selected()
            if selected_item is None:
                return

            is_used = selected_item.id in items_used
            item_type = self.config.model
            i_title = item_type.__title__
            if not is_used:
                self.config.set_repo_used(selected_item.id, selected_item.title, selected_item.description)
                body = _('{title} {item} ready to be used').format(title=i_title, item=selected_item.id)
                self.log.debug(body)
            else:
                body = _('{title} {item} is already being used').format(title=i_title, item=selected_item.id)
                self.log.debug(body)

            if len(self.config.load_used()) == 1:
                config = self.app.get_config_dict()
                config['App'].set('current', selected_item.id)
                self.log.debug(f"Repository {selected_item.id} enabled")
                workflow = self.app.get_service('workflow')
                workflow.switch_start()
                body = _('{title} {item} set as default').format(title=i_title, item=selected_item.id)
                self.log.info(body)
            srvdlg.show_toast(body)
        finally:
            if dd_repo is not None and signal is not None:
                dd_repo.handler_unblock(signal)

    def _on_item_used_remove(self, *args):
        # Trick to avoid restart app when repos are enabled/disabled
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        signal = self.app.get_widget('signal-dd_repo')
        if signal is not None:
            dd_repo.handler_block(signal)
        try:
            items_available = self.config.load_available()
            items_used = self.config.load_used()
            selected_item = self.viewSl.get_selected()
            if selected_item is None:
                return

            item_type = self.config.model
            i_title = item_type.__title__
            items_available[selected_item.id] = {
                'path': selected_item.title,
                'description': selected_item.description}
            self.log.debug(f"{i_title} {selected_item.id} added back to the list of available items")
            del items_used[selected_item.id]
            self.log.debug(f"{i_title} {selected_item.id} removed from de list of used items")
            self.config.save_used(items=items_used)
            self.config.save_available(items=items_available)
            self.srvdlg.show_toast(_('{title} {item} removed from de list of used items').format(title=i_title, item=selected_item.id))
        finally:
            if signal is not None:
                dd_repo.handler_unblock(signal)


class MiAZCountries(MiAZConfigView):
    """Manage countries from Repo Settings. Edit disabled"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        super().__init__(app, 'Country')

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewCountry(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewCountry(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

        # Countries are a fixed ISO 3166-1 alpha-2 vocabulary, and each entry
        # renders a bundled flag SVG (icon=f'{code}.svg'). The available pool is
        # the full ISO list; users only choose which countries they use, they do
        # not add, remove or rename them. Adding a custom code would produce an
        # entry with no flag, so the pool-editing buttons stay hidden by design.
        self.btnAvAdd.set_visible(False)
        self.btnAvRemove.set_visible(False)
        self.btnAvEdit.set_visible(False)
        if hasattr(self, 'btnSlEdit'):
            self.btnSlEdit.set_visible(False)

    def _update_view_available(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_available()
        used = self.config.load_used()
        for code in countries:
            if code not in used:
                items.append(item_type(id=code, title=humanize_value('Country', countries[code]), icon=f'{code}.svg'))
        self.viewAv.update(items)

    def _update_view_used(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_used()
        for code in countries:
            items.append(item_type(id=code, title=humanize_value('Country', countries[code]), icon=f'{code}.svg'))
        self.viewSl.update(items)


class MiAZGroups(MiAZConfigView):
    """Manage groups from Repo Settings"""
    __gtype_name__ = 'MiAZGroups'

    def __init__(self, app):
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
        super().__init__(app, 'SentBy')
        # SentBy and SentTo share the people-available.json pool; pairing keeps
        # both views in sync (the base class connects to its available-updated).
        self.config_paired = self.conf['SentTo']

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
        super().__init__(app, 'SentTo')
        # SentBy and SentTo share the people-available.json pool; pairing keeps
        # both views in sync (the base class connects to its available-updated).
        self.config_paired = self.conf['SentBy']

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
        super().__init__(app, 'Purpose')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPurpose(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPurpose(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)

class MiAZPlugins(MiAZConfigView):
    """Manage plugins from Repo Settings."""
    __gtype_name__ = 'MiAZPlugins'
    __gsignals__ = {
        'plugins-downloaded': (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    current = None

    def __init__(self, app):
        super().__init__(app, 'Plugin')
        boxopers = self.app.get_widget('selector-box-operations')
        factory = self.app.get_service('factory')
        util = self.app.get_service('util')

        # Load-failure banner: shown at the top of the Plugins view when one or
        # more enabled plugins failed to load. It lives here (not in the shared
        # columnview) so plugin-specific state stays out of the generic row
        # rendering used by every configuration view.
        self.banner_load_failures = Adw.Banner.new('')
        self.banner_load_failures.set_revealed(False)
        self.prepend(self.banner_load_failures)
        self._sid_plugins_updated = None
        self._refresh_load_failures()

        # Available view buttons
        btnInfo = factory.create_button(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', callback=self._show_plugin_info, css_classes=['linked'])
        btnInfo.set_valign(Gtk.Align.CENTER)
        for child in factory.get_children(self.toolbar_buttons_Av):
            self.toolbar_buttons_Av.remove(child)
        self.toolbar_buttons_Av.append(btnInfo)

        # Used view buttons. Plugins have no editable description, so drop the
        # edit button inherited from MiAZSelector. Configuring a plugin is the
        # Settings tab's job now, not a button here.
        if hasattr(self, 'btnSlEdit'):
            self.toolbar_buttons_Sl.remove(self.btnSlEdit)

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

        # Fill-in dropdowns
        ENV = self.app.get_env()
        try:
            self.user_plugins = util.json_load(ENV['APP']['PLUGINS']['INDEX'])
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

        self._cached_selected_cat = None
        self._cached_selected_subcat = None
        self.dpdCats.connect("notify::selected-item", self._on_plugin_category_selected)
        self.dpdSubcats.connect("notify::selected-item", self._on_plugin_subcategory_selected)

        if len(set_cats) > 0:
            self.dpdCats.set_selected(0)
            self._on_plugin_category_selected()

    def _on_configview_mapped(self, *args):
        super()._on_configview_mapped(*args)
        if self._sid_plugins_updated is None:
            plugin_manager = self.app.get_service('plugin-system')
            self._sid_plugins_updated = plugin_manager.connect(
                'plugins-updated', self._refresh_load_failures)
        self._refresh_load_failures()

    def _on_configview_unmapped(self, *args):
        super()._on_configview_unmapped(*args)
        if self._sid_plugins_updated is not None:
            plugin_manager = self.app.get_service('plugin-system')
            plugin_manager.disconnect(self._sid_plugins_updated)
            self._sid_plugins_updated = None

    def _refresh_load_failures(self, *_args):
        """Reveal the banner and set its text from the plugin manager's current
        load failures. Hide it when there are none."""
        plugin_manager = self.app.get_service('plugin-system')
        failures = plugin_manager.get_load_failures()
        if failures:
            self.banner_load_failures.set_title(format_load_failure_banner(failures))
            self.banner_load_failures.set_revealed(True)
        else:
            self.banner_load_failures.set_revealed(False)

    def _update_view_available(self):
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        try:
            system_plugins = util.json_load(ENV['APP']['PLUGINS']['INDEX'])
        except Exception:
            system_plugins = {}
        used = self.config.load_used()
        items = []
        for plugin_id, info in system_plugins.items():
            if plugin_id not in used:
                title = info.get('Description', plugin_id)
                items.append(Plugin(id=plugin_id, title=_(title)))
        self.viewAv.update(items)

    def _update_view_used(self, items=None):
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        try:
            all_plugins = util.json_load(ENV['APP']['PLUGINS']['INDEX'])
        except Exception:
            all_plugins = {}
        enabled = self.config.load_used()
        enabled_items = []
        for plugin_id, info in all_plugins.items():
            if plugin_id in enabled:
                title = info.get('Description', plugin_id)
                enabled_items.append(Plugin(id=plugin_id, title=_(title)))
        self.viewSl.update(enabled_items)

    def _do_filter_view(self, item, filter_list_model):
        plugin = item.id
        selected_cat = self._cached_selected_cat
        selected_subcat = self._cached_selected_subcat

        try:
            category = self.user_plugins[plugin]['Category']
        except KeyError:
            selected_cat = None

        try:
            subcategory = self.user_plugins[plugin]['Subcategory']
        except KeyError:
            selected_subcat = None

        chunk = self._cached_filter_text
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
        self._cached_selected_cat = self.dpdCats.get_selected_item()
        self._cached_selected_subcat = self.dpdSubcats.get_selected_item()
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
            pluginsystem.create_plugin_index()
            self.searchentry.set_text('')
            self.searchentry.activate()
            plugin_dirname = zip_archive.namelist()[0]
            plugin_path = glob.glob(os.path.join(ENV['LPATH']['PLUGINS'], plugin_dirname, '*.plugin'))[0]
            plugin_info = pluginsystem.get_plugin_attributes(plugin_path)
            plugin_name = plugin_info['Name']
            plugin_version = pluginsystem_version(plugin_info,
                                                  ENV['APP']['VERSION'])
            body2 = _('Plugin {plugin_name} v{plugin_version} imported successfully').format(plugin_name=plugin_name, plugin_version=plugin_version)
            self.srvdlg.show_toast(body2)
        except Exception as error:
            body1 = _('<b>Action not possible</b>')
            body2 = _('Error: {error}').format(error=error)
            body = body1 + '\n' + body2
            self.srvdlg.show_error(title=title, body=body, parent=self)
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
            heading = _('Delete {title}?').format(title=i_title.lower())
            body = _('<i>{desc}</i> will be permanently removed.').format(desc=item_dsc)
            dialog = self.srvdlg.show_confirmation(title=heading, body=body, confirm_label=_('Delete'))
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
            self.srvdlg.show_toast(body)

    def update_user_plugins(self):
        plugin_system = self.app.get_service('plugin-system')
        plugin_system.rescan_plugins()
        self.update_views()

    def plugins_updated(self, *args):
        self._update_view_available()

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewPlugin(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPlugin(self.app)
        self._add_columnview_used(self.viewSl)

    def _load_plugin_index(self):
        """Return the runtime plugin index keyed by plugin Name."""
        ENV = self.app.get_env()
        util = self.app.get_service('util')
        try:
            return util.json_load(ENV['APP']['PLUGINS']['INDEX'])
        except Exception:
            return {}

    def _parse_dependencies(self, plugin_info):
        """Return the list of plugin Names declared as dependencies.

        Dependencies are stored as a comma-separated string in the
        `Dependencies` key of the plugin_info dict. Missing or empty means
        no dependencies.
        """
        if plugin_info is None:
            return []
        raw = plugin_info.get('Dependencies', '')
        return [dep.strip() for dep in raw.split(',') if dep.strip()]

    def _resolve_required_chain(self, plugin_id, all_plugins):
        """Resolve the full dependency chain for `plugin_id`.

        Post-order depth-first walk so a dependency always lands before the
        plugin that needs it. Returns a tuple (to_enable, missing) where:
        - to_enable: topologically ordered list of installed-but-disabled
          dependency Names (dependencies first).
        - missing: list of dependency Names not present in the index.
        """
        to_enable = []
        missing = []
        done = set()
        visiting = set()

        def visit(pid):
            for dep in self._parse_dependencies(all_plugins.get(pid)):
                if dep in done or dep in visiting:
                    continue
                if dep not in all_plugins:
                    if dep not in missing:
                        missing.append(dep)
                    done.add(dep)
                    continue
                visiting.add(dep)
                visit(dep)
                visiting.discard(dep)
                done.add(dep)
                if not self.config.exists_used(dep) and dep not in to_enable:
                    to_enable.append(dep)

        visiting.add(plugin_id)
        visit(plugin_id)
        return to_enable, missing

    def _find_dependents(self, plugin_id, all_plugins):
        """Return enabled plugin Names whose dependency chain needs `plugin_id`."""
        dependents = []
        for enabled_id in self.config.load_used():
            if enabled_id == plugin_id:
                continue
            if self._chain_contains(enabled_id, plugin_id, all_plugins):
                dependents.append(enabled_id)
        return dependents

    def _chain_contains(self, plugin_id, target_id, all_plugins):
        """Return True if `target_id` is anywhere in `plugin_id`'s dependency chain."""
        visited = set()
        pending = list(self._parse_dependencies(all_plugins.get(plugin_id)))
        while pending:
            dep = pending.pop(0)
            if dep in visited:
                continue
            visited.add(dep)
            if dep == target_id:
                return True
            pending.extend(self._parse_dependencies(all_plugins.get(dep)))
        return False

    def _enable_single(self, plugin_id, all_plugins):
        """Load and record a single plugin as enabled. Returns True on success."""
        plugin_manager = self.app.get_service('plugin-system')
        plugin_info = all_plugins.get(plugin_id)
        if plugin_info is None:
            self.log.error(f"Plugin '{plugin_id}' not found in plugin index")
            return False
        if self.config.exists_used(plugin_id):
            return True
        plugin_module = plugin_info['Module']
        plugin = plugin_manager.get_plugin_info(plugin_module)
        if plugin is None:
            self.log.error(f"Plugin '{plugin_id}' could not be resolved by the engine")
            return False
        if not plugin_manager.is_plugin_loaded(plugin):
            if not plugin_manager.load_plugin(plugin):
                # Activation was refused (e.g. a plugin whose required external
                # tools are missing vetoed its do_activate). The plugin is
                # responsible for telling the user why; do not persist it as
                # enabled.
                self.log.warning(f"Plugin '{plugin_id}' was not enabled (activation refused)")
                return False
        enabled = self.config.load_used()
        enabled[plugin_id] = plugin_info.get('Name', plugin_id)
        self.config.save_used(enabled)
        self.log.debug(f"Plugin '{plugin_id}' enabled")
        return True

    def _on_item_used_remove(self, *args):
        selected_plugin = self.viewSl.get_selected()
        if selected_plugin is None:
            return

        plugin_manager = self.app.get_service('plugin-system')
        all_plugins = self._load_plugin_index()
        plugin_info = all_plugins.get(selected_plugin.id)
        if plugin_info is None:
            return

        # Warn and block: refuse to disable a plugin other enabled plugins need
        dependents = self._find_dependents(selected_plugin.id, all_plugins)
        if dependents:
            title = _('Cannot disable plugin')
            body = _("Plugin <b>{plugin}</b> is required by the following enabled "
                     "plugin(s):\n\n{deps}\n\nDisable them first.").format(
                         plugin=selected_plugin.id, deps='\n'.join(dependents))
            self.srvdlg.show_error(title=title, body=body, parent=self)
            return

        plugin_module = plugin_info['Module']
        plugin = plugin_manager.get_plugin_info(plugin_module)
        if plugin is not None and plugin_manager.is_plugin_loaded(plugin):
            plugin_manager.unload_plugin(plugin)
        self.config.remove_used(selected_plugin.id)
        self.log.debug(f"Plugin '{selected_plugin.id}' disabled")
        self.update_views()

    def _on_item_used_add(self, *args):
        selected_plugin = self.viewAv.get_selected()
        if selected_plugin is None:
            return

        if self.config.exists_used(selected_plugin.id):
            self.log.warning(f"Plugin '{selected_plugin.id}' is already enabled. Nothing to do")
            self.update_views()
            return

        all_plugins = self._load_plugin_index()
        plugin_info = all_plugins.get(selected_plugin.id)
        if plugin_info is None:
            self.log.error(f"Plugin '{selected_plugin.id}' not found in plugin index")
            return

        to_enable, missing = self._resolve_required_chain(selected_plugin.id, all_plugins)

        if missing:
            title = _('Missing plugin dependencies')
            body = _("Plugin <b>{plugin}</b> requires the following plugin(s) "
                     "which are not installed:\n\n{deps}").format(
                         plugin=selected_plugin.id, deps='\n'.join(missing))
            self.srvdlg.show_error(title=title, body=body, parent=self)
            return

        if to_enable:
            title = _('Enable required plugins')
            body = _("Plugin <b>{plugin}</b> requires the following plugin(s) "
                     "which are not enabled:\n\n{deps}\n\nEnable them now?").format(
                         plugin=selected_plugin.id, deps='\n'.join(to_enable))
            dialog = self.srvdlg.show_confirmation(title=title, body=body,
                                                   confirm_label=_('Enable'),
                                                   confirm_id='enable')
            data = (selected_plugin.id, to_enable, all_plugins)
            dialog.connect('response', self._on_enable_dependencies_response, data)
            dialog.present(self)
            return

        self._enable_single(selected_plugin.id, all_plugins)
        self.update_views()

    def _on_enable_dependencies_response(self, dialog, response, data):
        if response != 'enable':
            return
        plugin_id, to_enable, all_plugins = data
        for dep_id in to_enable:
            self._enable_single(dep_id, all_plugins)
        self._enable_single(plugin_id, all_plugins)
        self.update_views()

    def _show_plugin_info(self, *args):
        util = self.app.get_service('util')
        ENV = self.app.get_env()
        selected_plugin = self.viewAv.get_selected()
        if selected_plugin is None:
            return
        try:
            system_plugins = util.json_load(ENV['APP']['PLUGINS']['INDEX'])
        except Exception:
            return
        plugin_info = system_plugins.get(selected_plugin.id)
        if plugin_info is None:
            return

        # Build info dialog
        dialog = Adw.PreferencesDialog()
        dialog.set_title(_('Plugin info'))
        page_title = _('Properties')
        page_icon = "io.github.t00m.MiAZ-dialog-information-symbolic"
        page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        dialog.add(page)
        group = Adw.PreferencesGroup()
        group.set_title(_('Data Sheet'))
        page.add(group)

        # Add plugin info as key/value rows
        for key in plugin_info:
            row = Adw.ActionRow(title=f'<b>{_(key)}</b>')
            label = Gtk.Label.new(plugin_info[key])
            row.add_suffix(label)
            group.add(row)
        dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)
        dialog.present(self.viewAv.get_root())
