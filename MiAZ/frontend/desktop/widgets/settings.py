#!/usr/bin/python3
# File: settings.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage App and Repository settings

import os
from gettext import gettext as _

from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Repository, Plugin, Project
from MiAZ.backend.models import Country, Group, Purpose, SentBy, SentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.widgets.configview import MiAZUserPlugins
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.widgets.window import MiAZCustomWindow
from MiAZ.backend.config import MiAZConfigRepositories
from MiAZ.backend.pluginsystem import MiAZPluginType
from MiAZ.frontend.desktop.services.dialogs import MiAZFileChooserDialog

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Project'] = MiAZProjects
Configview['Plugin'] = MiAZUserPlugins
# ~ Configview['Date'] = Gtk.Calendar


class MiAZAppSettings(MiAZCustomWindow):
    __gtype_name__ = 'MiAZAppSettings'

    def __init__(self, app, **kwargs):
        self.app = app
        self.log = MiAZLog('MiAZ.AppSettings')
        self.name = 'app-settings'
        self.title = 'Application settings'
        self.app.add_widget('window-settings', self)
        super().__init__(app, self.name, self.title, **kwargs)

    def _build_ui(self):
        self.set_default_size(1024, 728)
        headerbar = self.app.get_widget(f"window-{self.name}-headerbar")
        self.stack = self.app.add_widget('stack_settings', Gtk.Stack())
        self.stack.set_vexpand(True)
        self.switcher = self.app.add_widget('switcher_settings', Gtk.StackSwitcher())
        self.switcher.set_stack(self.stack)
        self.switcher.set_hexpand(False)
        headerbar.pack_start(self.switcher)
        self.mainbox.append(self.stack)
        widget = self._create_widget_for_repositories()
        page = self.stack.add_titled(widget, 'repos', 'Repositories')
        page.set_visible(True)
        widget = self._create_widget_for_plugins()
        page = self.stack.add_titled(widget, 'plugins', 'Plugins')
        page.set_visible(True)
        self.repo_is_set = False

    def _create_widget_for_repositories(self):
        row = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        hbox = self.factory.create_box_horizontal()
        lblActive = Gtk.Label()
        lblActive.set_markup(_("<b>Select repository</b>"))
        self.dd_repo = self.factory.create_dropdown_generic(item_type=Repository, ellipsize=False, enable_search=False)
        btnUseRepo = self.factory.create_button(icon_name='io.github.t00m.MiAZ-document-open-symbolic', title=_('Load'), callback=self._on_use_repo)
        hbox.append(lblActive)
        hbox.append(self.dd_repo)
        hbox.append(btnUseRepo)
        self.actions.dropdown_populate(MiAZConfigRepositories, self.dd_repo, Repository, any_value=False, none_value=False)
        # DOC: By enabling this signal, repos are loaded automatically without pressing the button:
        # ~ self.dd_repo.connect("notify::selected-item", self._on_selected_repo)
        self.config['Repository'].connect('used-updated', self.actions.dropdown_populate, self.dd_repo, Repository, False, False)

        # Load last active repo
        repos_used = self.config['Repository'].load_used()
        repo_active = self.config['App'].get('current')
        if repo_active in repos_used:
            model = self.dd_repo.get_model()
            for n, item in enumerate(model):
                if item.id == repo_active:
                    self.dd_repo.set_selected(n)
        row.append(hbox)
        configview = MiAZRepositories(self.app)
        configview.set_hexpand(True)
        configview.set_vexpand(True)
        configview.update_views()
        row.append(configview)
        return row

    def _on_use_repo(self, *args):
        repo_id = self.dd_repo.get_selected_item().id
        self.config['App'].set('current', repo_id)
        valid = self.app.switch_start()
        if valid:
            window = self.app.get_widget(f"window-{self.name}")
            window.hide()
            sidebar = self.app.get_widget('sidebar')
            sidebar.clear_filters()
            self.log.debug(f"Repository {repo_id} loaded successfully")
        else:
            self.log.error(f"Repository {repo_id} couldn't be loaded")

    def _on_selected_repo(self, dropdown, gparamobj):
        try:
            repo_id = dropdown.get_selected_item().id
            repo_dir = dropdown.get_selected_item().title
            self.log.debug(f"Repository selected: {repo_id}[{repo_dir}]")
            self.config['App'].set('current', repo_id)
            self.app.switch()
        except AttributeError:
            # Probably the repository was removed from used view
            pass

    def _update_action_row_repo_source(self, name, dirpath):
        self.row_repo_source.set_title(name)
        self.row_repo_source.set_subtitle(dirpath)
        self.repo_is_set = True

    def is_repo_set(self):
        return self.repo_is_set

    def show_filechooser_source(self, *args):
        window = self.app.get_widget('window')
        filechooser = self.factory.create_filechooser(
                    enable_response=True,
                    title=_('Choose target directory'),
                    target = 'FOLDER',
                    callback = self.on_filechooser_response_source,
                    data = None
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response, data):
                return

    def _create_widget_for_plugins(self):
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        notebook = Gtk.Notebook()
        notebook.set_show_border(False)
        notebook.set_tab_pos(Gtk.PositionType.LEFT)
        widget = self._create_view_plugins_system()
        label = self.factory.create_notebook_label(icon_name='io.github.t00m.MiAZ-res-plugins-system', title='System')
        notebook.append_page(widget, label)
        widget = self._create_view_plugins_user()
        label = self.factory.create_notebook_label(icon_name='io.github.t00m.MiAZ-res-plugins', title='User')
        notebook.append_page(widget, label)
        vbox.append(notebook)
        return vbox

    def _create_view_plugins_system(self):
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        scrwin = self.factory.create_scrolledwindow()
        self.app.add_widget('app-settings-plugins-system-scrwin', scrwin)
        vbox.append(scrwin)
        pm = self.app.get_service('plugin-manager')
        view = MiAZColumnViewPlugin(self.app)
        view.set_hexpand(True)
        view.set_vexpand(True)
        self.app.add_widget('app-settings-plugins-system-view', view)
        scrwin.set_child(view)

        # System Plugins
        items = []
        item_type = Plugin
        for plugin in pm.plugins:
            if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                pid = plugin.get_module_name()
                title = plugin.get_description()
                items.append(item_type(id=pid, title=title))
        view.update(items)
        return vbox

    def _create_view_plugins_user(self):
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)

        # Add/Remove
        hbox = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=False)
        hbox.get_style_context().add_class(class_name='toolbar')
        hbox.append(self.factory.create_button(icon_name='io.github.t00m.MiAZ-list-add-symbolic', title='Add plugin', callback=self._on_plugin_add))
        hbox.append(self.factory.create_button(icon_name='io.github.t00m.MiAZ-list-remove-symbolic', title='Remove plugin', callback=self._on_plugin_remove))
        vbox.append(hbox)

        # User Plugins
        scrwin = self.factory.create_scrolledwindow()
        self.app.add_widget('app-settings-plugins-user-scrwin', scrwin)
        vbox.append(scrwin)
        view = MiAZColumnViewPlugin(self.app)
        view.set_hexpand(True)
        view.set_vexpand(True)
        self.app.add_widget('app-settings-plugins-user-view', view)
        scrwin.set_child(view)
        self.update_user_plugins()
        return vbox

    def update_user_plugins(self):
        ENV = self.app.get_env()
        plugin_manager = self.app.get_service('plugin-manager')
        plugin_manager.rescan_plugins()
        view = self.app.get_widget('app-settings-plugins-user-view')
        items = []
        item_type = Plugin
        for plugin in plugin_manager.plugins:
            ptype = plugin_manager.get_plugin_type(plugin)
            if ptype == MiAZPluginType.USER:
                pid = plugin.get_module_name()
                plugin_path = os.path.join(ENV['LPATH']['PLUGINS'], f"{pid}.plugin")
                if os.path.exists(plugin_path):
                    title = plugin.get_description()
                    items.append(item_type(id=pid, title=title))
        view.update(items)

    def on_filechooser_response(self, dialog, response, clsdlg):
        if response == 'apply':
            plugin_manager = self.app.get_service('plugin-manager')
            filechooser = clsdlg.get_filechooser_widget()
            gfile = filechooser.get_file()
            if gfile is None:
                    self.log.debug('No directory set. Do nothing.')
                    # FIXME: Show warning message. Priority: low
                    return
            plugin_path = gfile.get_path()
            imported = plugin_manager.import_plugin(plugin_path)
            self.log.debug(f"Plugin imported? {imported}")
            if imported:
                self.update_user_plugins()

    def _on_plugin_add(self, *args):
        plugin_filter = Gtk.FileFilter()
        plugin_filter.add_pattern('*.zip')
        window = self.app.get_widget('window-settings')
        clsdlg = MiAZFileChooserDialog(self.app)
        filechooser_dialog = clsdlg.create(
                        parent=window,
                        title=_('Import a single file'),
                        target = 'FILE',
                        callback = self.on_filechooser_response,
                        data=clsdlg)
        filechooser_widget = clsdlg.get_filechooser_widget()
        filechooser_widget.set_filter(plugin_filter)
        filechooser_dialog.present()

    def _on_plugin_remove(self, *args):
        plugin_manager = self.app.get_service('plugin-manager')
        view = self.app.get_widget('app-settings-plugins-user-view')
        try:
            module = view.get_selected()
            plugin = plugin_manager.get_plugin_info(module.id)
            deleted = plugin_manager.remove_plugin(plugin)
            if deleted:
                self.log.debug(f"Plugin '{module.id}' deleted")
                self.update_user_plugins()
        except IndexError as error:
            self.log.debug("No user plugins installed and/or selected")
            raise

    def get_plugin_status(self, name: str) -> bool:
        plugins = self.config['App'].get('plugins')
        if plugins is None:
            return False

        if name in plugins:
            return True
        return False

    def set_plugin_status(self, checkbox, plugin_name):
        active = checkbox.get_active()
        plugins = self.config['App'].get('plugins')
        if plugins is None:
            plugins = []
        if active:
            if plugin_name not in plugins:
                plugins.append(plugin_name)
        else:
            plugins.remove(plugin_name)
        self.config['App'].set('plugins', plugins)


class MiAZRepoSettings(MiAZCustomWindow):
    __gtype_name__ = 'MiAZRepoSettings'

    def __init__(self, app, **kwargs):
        self.app = app
        self.log = MiAZLog('MiAZ.RepoSettings')
        self.name = 'repo-settings'
        appconf = self.app.get_config('App')
        repo_id = appconf.get('current')
        self.title = f"Settings for repository {repo_id}"
        super().__init__(app, self.name, self.title, **kwargs)
        # ~ self.connect('notify::visible', self.update)

    def _build_ui(self):
        self.set_default_size(1024, 728)
        notebook = self.app.add_widget('repository-settings-notebook', Gtk.Notebook())
        notebook.set_show_border(False)
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.mainbox.append(notebook)

        def create_tab(item_type):
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title_plural__)
            page = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            page.set_vexpand(True)
            page.set_hexpand(True)
            widget_title = f"configview-{i_title}"
            selector = self.app.add_widget(widget_title, Configview[i_type](self.app))
            selector.set_vexpand(True)
            selector.update_views()
            box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
            box.append(selector)
            page.set_start_widget(box)
            wdgLabel = self.factory.create_box_horizontal()
            wdgLabel.get_style_context().add_class(class_name='caption')
            icon = self.icman.get_image_by_name(f"io.github.t00m.MiAZ-res-{i_title.lower()}")
            icon.set_hexpand(False)
            icon.set_pixel_size(24)
            label = self.factory.create_label(f"<b>{i_title}</b>")
            label.set_xalign(0.0)
            label.set_hexpand(True)
            wdgLabel.append(icon)
            wdgLabel.append(label)
            wdgLabel.set_hexpand(True)
            return page, wdgLabel

        # FIXME: User plugins disabled temporary
        for item_type in [Country, Group, Purpose, SentBy, SentTo, Project, Plugin]:
            page, label = create_tab(item_type)
            notebook.append_page(page, label)

    def update(self, *args):
        appconf = self.app.get_config('App')
        repo_id = appconf.get('current')
        title = f"Settings for repository {repo_id}"
        self.set_title(title)

        # FIXME: User plugins disabled temporary
        for item_type in [Country, Group, Purpose, Project, SentBy, SentTo, Plugin]:
            i_title = item_type.__title_plural__
            widget_title = f"configview-{i_title}"
            configview = self.app.get_widget(widget_title)
            configview.update_config()
            configview.update_views()
        # ~ self.log.debug("Repository UI updated according to current settings")

