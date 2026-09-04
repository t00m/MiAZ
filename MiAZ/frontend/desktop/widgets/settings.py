# File: settings.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage App and Repository settings

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.config import MiAZConfigRepositories
from MiAZ.backend.models import Repository, Plugin
from MiAZ.backend.models import Country, Group, Purpose, SentBy, SentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.widgets.configview import MiAZPlugins
from MiAZ.frontend.desktop.widgets.window import MiAZCustomWindow
from MiAZ.frontend.desktop.widgets.dr import MiAZDRPage
from MiAZ.frontend.desktop.widgets.reposettingspage import MiAZRepoSettingsPage
from MiAZ.frontend.desktop.widgets.metadatapage import MiAZMetadataPage
# ~ from MiAZ.frontend.desktop.widgets.pluginuimanager import MiAZPluginUIManager

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Plugin'] = MiAZPlugins
# ~ Configview['Date'] = Gtk.Calendar


class MiAZAppSettings(Adw.PreferencesDialog):
    __gtype_name__ = 'MiAZAppSettings'
    """Workspace"""
    __gsignals__ = {
        "settings-loaded":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app, **kwargs):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.AppSettings')
        config_dict = self.app.get_config_dict()
        self.config_repos = config_dict['Repository']
        self.config_repos.connect('used-updated', self._on_update_repos_available)
        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')
        self.actions = self.app.get_service('actions')
        self._build_ui()
        self.emit('settings-loaded')

    def _on_update_repos_available(self, *args):
        repo_id = self.app.get_service('repo').get_active_id()
        n = 0
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        for repo in dd_repo.get_model():
            if repo_id ==  repo.id:
                dd_repo.set_selected(n)
            n += 1
        self._update_active_repo_subtitle()

    def _update_active_repo_subtitle(self, *args):
        # dropdown_populate() rewrites Repository.title to a prettified name
        # (id with underscores turned into spaces), so the model item no
        # longer carries the path. Look up the absolute path in the repo
        # config by id.
        row = self.app.get_widget('window-setting-row-active-repository')
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        if row is None or dd_repo is None:
            return
        repo = dd_repo.get_selected_item()
        path = ''
        if repo is not None:
            path = self.config_repos.get_path(repo.id, used=True)
        row.set_subtitle(path)

    def _build_ui(self):
        self.set_title(_('Application settings'))
        self.set_search_enabled(False)
        self._build_ui_page_preferences()
        self._build_ui_page_dr()
        # ~ self._build_ui_page_aspect()

    def _build_ui_page_dr(self):
        page = MiAZDRPage(self.app)
        self.add(page)

    def _build_ui_page_aspect(self):
        # Create preferences page
        page_title = _("Aspect")
        page_icon = "io.github.t00m.MiAZ-preferences-ui"
        page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        self.add(page)
        self.app.add_widget('window-preferences-page-aspect', page)

        ## Group UI
        group = Adw.PreferencesGroup()
        group.set_title(_('User interface'))
        page.add(group)
        self.app.add_widget('window-preferences-page-aspect-group-ui', group)

    def _build_ui_page_preferences(self):
        """Repositories dialog page"""

        # Create preferences page
        page_title = _("Preferences")
        page_icon = "io.github.t00m.MiAZ-emblem-system-symbolic"
        page = Adw.PreferencesPage(title=page_title, icon_name=page_icon)
        self.add(page)

        ## Group Repositories
        group = Adw.PreferencesGroup()
        group.set_title(_('Repositories'))
        page.add(group)

        ### Row Repositories
        #### View active repository / Select repository
        row = Adw.ActionRow(title=_('Active repository'))
        self.app.add_widget('window-setting-row-active-repository', row)
        group.add(row)

        #### Configure repository dropdown
        dd_repo = self.factory.create_dropdown_generic(item_type=Repository, ellipsize=False, enable_search=True)
        self.app.add_widget('window-settings-dropdown-repository-active', dd_repo)
        dd_repo.set_valign(Gtk.Align.CENTER)
        dd_repo.set_hexpand(False)
        self.actions.dropdown_populate(MiAZConfigRepositories, dd_repo, Repository, any_value=False, none_value=False)

        #### Select active repository
        self._on_update_repos_available()

        # Selecting a repository here asks to switch to it. The switch happens
        # in place: MiAZWorkflow.switch_start unloads the plugins of the
        # repository being left before loading the new configuration, so the
        # restart this used to need is gone.
        self.config_repos.connect('used-updated', self.actions.dropdown_repopulate, dd_repo, Repository, False, False)
        signal = dd_repo.connect("notify::selected-item", self._on_use_repo)
        self.app.add_widget('signal-dd_repo', signal)
        dd_repo.connect("notify::selected-item", self._update_active_repo_subtitle)
        row.add_suffix(dd_repo)
        self._update_active_repo_subtitle()

        #### Manage repositories
        btnManageRepos = self.factory.create_button(icon_name='io.github.t00m.MiAZ-study-symbolic', callback=self._on_manage_repositories, tooltip="Manage repositories")
        btnManageRepos.set_valign(Gtk.Align.CENTER)
        row.add_prefix(btnManageRepos)

        ## Group User Interface
        # Interface plugins register their rows here via the
        # 'settings-loaded' signal on MiAZActions.
        ui_group = Adw.PreferencesGroup()
        ui_group.set_title(_('User Interface'))
        page.add(ui_group)
        self.app.add_widget('window-preferences-page-ui-group', ui_group)

        # Sidebar toggle button visibility (core behaviour, formerly the
        # MiAZSidebarTB plugin).
        self._build_sidebar_toggle_row(ui_group)

        # Optional external libraries (per-user venv for plugin dependencies).
        self._build_external_libraries_group(page)

    def _build_external_libraries_group(self, page):
        group = Adw.PreferencesGroup()
        group.set_title(_('External libraries'))
        group.set_description(_('Optional Python libraries some plugins need '
                                '(for example AI providers). MiAZ installs them '
                                'in a private virtualenv in your home directory, '
                                'never into the system Python.'))
        page.add(group)

        # Collapsible: collapsed it shows only a status summary; expanded it
        # lists one row per installed library, so a long list never floods the
        # settings page.
        row = Adw.ExpanderRow(title=_('External libraries'))
        self.app.add_widget('window-setting-row-extlibs', row)
        self._extlibs_lib_rows = []
        group.add(row)

        btn_install = self.factory.create_button(
            title=_('Install / Update'), callback=self._on_extlibs_install)
        btn_install.set_valign(Gtk.Align.CENTER)
        row.add_suffix(btn_install)

        btn_remove = self.factory.create_button(
            title=_('Remove'), callback=self._on_extlibs_remove)
        btn_remove.set_valign(Gtk.Align.CENTER)
        row.add_suffix(btn_remove)

        self._update_extlibs_row()

    # Packages the venv tooling itself brings along; not user libraries.
    _EXTLIBS_BOOTSTRAP = frozenset({'pip', 'setuptools', 'wheel'})

    def _update_extlibs_row(self):
        row = self.app.get_widget('window-setting-row-extlibs')
        if row is None:
            return
        for lib_row in self._extlibs_lib_rows:
            row.remove(lib_row)
        self._extlibs_lib_rows = []

        venv = self.app.get_service('venv')
        if not venv.exists():
            row.set_subtitle(_('Not installed. Install to download them.'))
            row.set_expanded(False)
            row.set_enable_expansion(False)
            return
        if venv.stale():
            row.set_subtitle(_('Installed for a different Python version. '
                               'Reinstall to rebuild.'))
            row.set_expanded(False)
            row.set_enable_expansion(False)
            return

        libs = {name: version
                for name, version in venv.installed_details().items()
                if name not in self._EXTLIBS_BOOTSTRAP}
        count = len(libs)
        row.set_subtitle(_('{count} libraries installed').format(count=count))
        row.set_enable_expansion(count > 0)
        by_lib = self.app.get_service('extlibs').plugins_by_library()
        for name in sorted(libs):
            plugins = by_lib.get(name)
            if plugins:
                subtitle = _('{version}, required by {plugins}').format(
                    version=libs[name], plugins=', '.join(plugins))
            else:
                subtitle = libs[name]
            lib_row = Adw.ActionRow(title=name, subtitle=subtitle)
            # Activating the row opens the library's project page in the browser.
            lib_row.set_activatable(True)
            lib_row.add_suffix(Gtk.Image.new_from_icon_name(
                'adw-external-link-symbolic'))
            lib_row.connect('activated', self._on_extlib_open,
                            venv.distribution_url(name))
            row.add_row(lib_row)
            self._extlibs_lib_rows.append(lib_row)

    def _on_extlib_open(self, _row, url):
        Gio.AppInfo.launch_default_for_uri(url, None)

    def _on_extlibs_install(self, *args):
        self.app.get_service('extlibs').install(
            self, on_done=lambda ok: self._update_extlibs_row())

    def _on_extlibs_remove(self, *args):
        self.app.get_service('venv').remove()
        self._update_extlibs_row()
        self.app.get_service('dialogs').show_toast(_('External libraries removed'))

    def _build_sidebar_toggle_row(self, group):
        appconf = self.app.get_config('App')
        visible = appconf.get('sidebar-button-visible') if appconf is not None else None
        if visible is None:
            visible = True
        row = Adw.SwitchRow(title=_('Display sidebar toggle button'))
        row.set_subtitle(_('Show the headerbar icon that reveals or hides the '
                           'sidebar. The sidebar can also be toggled with the '
                           'Escape key.'))
        row.set_active(bool(visible))
        row.connect('notify::active', self._on_sidebar_toggle_visibility)
        group.add(row)

    def _on_sidebar_toggle_visibility(self, row, gparam):
        visible = row.get_active()
        appconf = self.app.get_config('App')
        if appconf is not None:
            appconf.set('sidebar-button-visible', visible)
        button = self.app.get_widget('headerbar-button-sidebar-toggle')
        if button is not None:
            button.set_visible(visible)

    def _create_widget_for_repositories(self):
        box = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        configview = MiAZRepositories(self.app)
        configview.set_hexpand(True)
        configview.set_vexpand(True)
        configview.update_views()
        box.append(configview)
        return box

    def _on_use_repo(self, dropdown, gparam):
        """Ask before switching to the repository just selected.

        The switch happens in place, with no restart: the documents, the
        vocabularies and the plugins of the repository being opened replace
        the ones on screen. The checkbox decides the other half, whether this
        repository also becomes the one MiAZ opens next time.
        """
        repo = dropdown.get_selected_item()
        if repo is None:
            return

        repository = self.app.get_service('repo')
        if repo.id == repository.get_active_id():
            # Already the repository on screen, so there is nothing to confirm.
            return

        title = _('Repository management')
        body1 = _('Would you like to switch to the repository {repository}?').format(repository=repo.id)
        body2 = _('Its documents, vocabularies and plugins replace the ones in use.')
        body = body1 + '\n\n' + body2
        check = Gtk.CheckButton(label=_('Set as the default repository'))
        check.set_active(True)
        check.set_tooltip_text(_('The repository MiAZ opens the next time it starts'))
        parent = self.app.get_widget('window')
        srvdlg = self.app.get_service('dialogs')
        dialog = srvdlg.show_question(title=title, body=body, widget=check,
                                      callback=self._on_use_repo_response,
                                      data=(repo, check))
        dialog.present(parent)

    def _on_use_repo_response(self, dialog, response, data):
        repo, check = data
        srvdlg = self.app.get_service('dialogs')
        config = self.app.get_config_dict()

        if response == 'apply':
            set_default = check.get_active()
            if set_default:
                config['App'].set('current', repo.id)
            workflow = self.app.get_service('workflow')
            if workflow.switch_start(repo_id=repo.id):
                self.log.info(f"Switched to repository {repo.id} (default: {set_default})")
                self._update_active_repo_subtitle()
                if set_default:
                    srvdlg.show_toast(_('Switched to {repository}, now the default one').format(repository=repo.id))
                else:
                    srvdlg.show_toast(_('Switched to {repository}').format(repository=repo.id))
            else:
                self.log.error(f"Repository {repo.id} could not be loaded")
                self._select_active_repo()
                srvdlg.show_toast(_('{repository} could not be loaded').format(repository=repo.id))
        else:
            self._select_active_repo()
            srvdlg.show_toast(_('Action canceled. Repository not switched'))

    def _select_active_repo(self):
        """Put the dropdown back on the repository actually in use.

        Selecting in the dropdown is what asks for a switch, so writing the
        selection back has to happen with that signal blocked, or the dialog
        opens again for the repository the user just declined.
        """
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        signal = self.app.get_widget('signal-dd_repo')
        if dd_repo is None or signal is None:
            return
        active_id = self.app.get_service('repo').get_active_id()
        dd_repo.handler_block(signal)
        for position, item in enumerate(dd_repo.get_model()):
            if item.id == active_id:
                dd_repo.set_selected(position)
        dd_repo.handler_unblock(signal)

    def _on_manage_repositories(self, *args):
        widget = self._create_widget_for_repositories()
        window = self
        title = _('Repository management')
        body = "" # "Add, edit, delete and (de)activate repositories"
        dialog = self.srvdlg.show_noop(title=title, body=body, widget=widget, width=800, height=600)
        dialog.present(window)

    def _update_action_row_repo_source(self, name, dirpath):
        self.row_repo_source.set_title(name)
        self.row_repo_source.set_subtitle(dirpath)
        self.repo_is_set = True

    def is_repo_set(self):
        return self.repo_is_set


class MiAZRepoSettings(MiAZCustomWindow):
    __gtype_name__ = 'MiAZRepoSettings'

    def __init__(self, app, **kwargs):
        self.app = app
        self.log = MiAZLog('MiAZ.RepoSettings')
        self.name = 'repo-settings'
        self.title = _('Settings for repository') + ' ' + self._repo_label(app.get_service('repo').get_active_id())
        super().__init__(app, self.name, self.title, **kwargs)

    def _repo_label(self, repo_id):
        # Prefer the repository description; fall back to the prettified key.
        if repo_id is None:
            return ''
        description = self.app.get_config('Repository').get_description(repo_id, used=True)
        return description or repo_id.replace('_', ' ')

    def _build_ui(self):
        self.set_default_size(1024, 728)
        notebook = self.app.add_widget('repository-settings-notebook', Gtk.Notebook())
        notebook.set_show_border(False)
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.mainbox.append(notebook)

        def create_selector(item_type):
            i_type = item_type.__gtype_name__
            widget_title = f"configview-{item_type.__title__}"
            selector = self.app.add_widget(widget_title, Configview[i_type](self.app))
            selector.set_vexpand(True)
            selector.update_views()
            return selector

        metadata = MiAZMetadataPage(self.app)
        for item_type in [Country, Group, Purpose, SentBy, SentTo]:
            icon_name = f"io.github.t00m.MiAZ-res-{item_type.__config_name__.lower()}"
            metadata.add_view(item_type.__gtype_name__,
                              _(item_type.__title_plural__),
                              icon_name,
                              create_selector(item_type))
        notebook.append_page(metadata, self._tab_label(
            _('Metadata'), 'io.github.t00m.MiAZ-res-groups'))

        notebook.append_page(create_selector(Plugin), self._tab_label(
            _('Plugins'), 'io.github.t00m.MiAZ-res-plugins'))

        settings_page = MiAZRepoSettingsPage(self.app)
        notebook.append_page(settings_page, self._tab_label(
            _('Settings'), 'io.github.t00m.MiAZ-emblem-system-symbolic'))
        # Built when it is shown, not when the dialog opens: see the page's
        # docstring for what that saves.
        notebook.connect('switch-page', self._on_switch_page)

    def _tab_label(self, title, icon_name):
        box = self.factory.create_box_horizontal()
        box.add_css_class('caption')
        icon = self.icman.get_image_by_name(icon_name)
        icon.set_hexpand(False)
        icon.set_pixel_size(16)
        label = self.factory.create_label(f"<b>{title}</b>")
        label.set_xalign(0.0)
        label.set_hexpand(True)
        box.append(icon)
        box.append(label)
        return box

    def _on_switch_page(self, notebook, page, number):
        if isinstance(page, MiAZRepoSettingsPage):
            page.build_plugin_groups()

    def update(self, *args):
        title = _('Settings for repository') + ' ' + self._repo_label(self.app.get_service('repo').get_active_id())
        self.set_title(title)

        for item_type in [Country, Group, Purpose, SentBy, SentTo, Plugin]:
            i_title = item_type.__title__
            widget_title = f"configview-{i_title}"
            configview = self.app.get_widget(widget_title)
            if configview is None:
                self.log.warning(f"Widget '{widget_title}' not registered, skipping update")
                continue
            configview.update_config()
            configview.update_views()
