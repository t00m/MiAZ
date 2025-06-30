#!/usr/bin/python3
# File: settings.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage App and Repository settings

from gettext import gettext as _

from gi.repository import Adw
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
from MiAZ.frontend.desktop.widgets.configview import MiAZUserPlugins
from MiAZ.frontend.desktop.widgets.window import MiAZCustomWindow
from MiAZ.frontend.desktop.widgets.pluginuimanager import MiAZPluginUIManager

Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Plugin'] = MiAZUserPlugins
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
        config = self.app.get_config_dict()
        repo_id = config['App'].get('current')
        n = 0
        dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        for repo in dd_repo.get_model():
            if repo_id ==  repo.id:
                dd_repo.set_selected(n)
            n += 1

    def _build_ui(self):
        self.set_title(_('Application settings'))
        self.set_search_enabled(False)
        self._build_ui_page_preferences()
        # ~ self._build_ui_page_aspect()

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

        # DOC: By enabling this signal, repos are loaded automatically without pressing the button:
        # However, if a repository is loaded automatically, plugins too
        # Right now, the load/unload plugin procedure is not working well
        # Therefore, the app is restarted.
        self.config_repos.connect('used-updated', self.actions.dropdown_populate, dd_repo, Repository, False, False)
        signal = dd_repo.connect("notify::selected-item", self._on_use_repo)
        self.app.add_widget('signal-dd_repo', signal)
        row.add_suffix(dd_repo)

        #### Manage repositories
        btnManageRepos = self.factory.create_button(icon_name='io.github.t00m.MiAZ-study-symbolic', callback=self._on_manage_repositories, tooltip="Manage repositories")
        btnManageRepos.set_valign(Gtk.Align.CENTER)
        row.add_prefix(btnManageRepos)

        ## Group plugins
        group = Adw.PreferencesGroup()
        group.set_title(_('Plugins'))
        # ~ FIXME: Add plugins back revamped.
        page.add(group)

        ### Row Plugins
        #### Manage plugins
        row = Adw.ActionRow(title=_('Manage plugins'))
        group.add(row)
        button = self.factory.create_button(icon_name='io.github.t00m.MiAZ-res-plugins', callback=self._on_manage_plugins, tooltip="Manage plugins")
        button.set_valign(Gtk.Align.CENTER)
        row.add_prefix(button)

    def _on_manage_plugins(self, *args):
        srvdlg = self.app.get_service('dialogs')
        window = self.app.get_widget('window')
        widget = MiAZPluginUIManager(self.app)
        dialog = srvdlg.show_noop(title=_('Plugin Manager'), body='', widget=widget, width=800, height=600)

        dialog.present(self)

    def _build_ui_page_plugins(self):
        # Plugins page
        group = self.app.add_widget('dialog-settings-plugins', Adw.PreferencesGroup())
        page_title = _("Plugins")
        page_icon = "io.github.t00m.MiAZ-res-plugins"
        page = self.app.add_widget('dialog-settings-page-plugins', Adw.PreferencesPage(title=page_title, icon_name=page_icon))
        self.add(page)
        page.add(group)

    def _create_widget_for_repositories(self):
        box = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        configview = MiAZRepositories(self.app)
        configview.set_hexpand(True)
        configview.set_vexpand(True)
        configview.update_views()
        box.append(configview)
        return box

    def _on_use_repo(self, dropdown, gparam):
        """
        Load repository automatically whenever is selected.
        Once loaded, it is set as the default in the app config.
        Then, the  user is asked if enabled repo should be the default one.
        If yes, the app is restarted.
        """
        # ~ dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
        repo = dropdown.get_selected_item()
        if repo is None:
            return

        title = _('Repository management')
        body1 = _('Would you like to set the repository {repository} as default?').format(repository=repo.id)
        body2 = _('Please, note that the app will be restarted upon confirmation')
        body = body1 + '\n\n' + body2
        parent = self.app.get_widget('window')
        srvdlg = self.app.get_service('dialogs')
        dialog = srvdlg.show_question(title=title, body=body, callback=self._on_use_repo_response, data=repo)
        dialog.present(parent)

    def _on_use_repo_response(self, dialog, response, repo):
        srvdlg = self.app.get_service('dialogs')
        config = self.app.get_config_dict()
        default_repo = config['App'].get('current')

        if response == 'apply':
            config['App'].set('current', repo.id)
            self.log.debug(_('Repository %s enabled' % repo.id))
            # ~ srvdlg.show_info("Repostory management", body="Repository {repo.id} switched.\nApplication will be restarted now.", parent=dialog)
            actions = self.app.get_service('actions')
            actions.application_restart()
        else:
            # Trick to avoid restart app when repos are enabled/disabled
            ## Block signal "dd_repo > notify::selected-item"
            dd_repo = self.app.get_widget('window-settings-dropdown-repository-active')
            signal = self.app.get_widget('signal-dd_repo')
            dd_repo.handler_block(signal)

            # Set default report back again
            model = dd_repo.get_model()
            n = 0
            for item in model:
                if item.id == default_repo:
                    dd_repo.set_selected(n)
                n += 1

            ## Unblock signal "dd_repo > notify::selected-item"
            dd_repo.handler_unblock(signal)

            srvdlg.show_error(_('Repository management'), body=_('Action canceled. Repository not switched'), parent=dialog)

    def _on_manage_repositories(self, *args):
        widget = self._create_widget_for_repositories()
        window = self
        title = _('Repository management')
        body = "" # "Add, edit, delete and (de)activate repositories"
        dialog = self.srvdlg.show_noop(title=title, body=body, widget=widget, width=800, height=600)
        dialog.present(window)

    def _on_selected_repo(self, dropdown, gparamobj):
        try:
            repo_id = dropdown.get_selected_item().id
            repo_dir = dropdown.get_selected_item().title
            self.log.debug(f"ON_SELECTED_REPO: Repository selected: {repo_id}[{repo_dir}]")
            self.config['App'].set('current', repo_id)
            # ~ self.app.switch()
            actions = self.app.get_service('actions')
            # ~ actions.application_restart()
        except AttributeError:
            # Probably the repository was removed from used view
            pass

    def _update_action_row_repo_source(self, name, dirpath):
        self.row_repo_source.set_title(name)
        self.row_repo_source.set_subtitle(dirpath)
        self.repo_is_set = True

    def is_repo_set(self):
        return self.repo_is_set

    def on_filechooser_response_source(self, dialog, response, data):
                return


class MiAZRepoSettings(MiAZCustomWindow):
    __gtype_name__ = 'MiAZRepoSettings'

    def __init__(self, app, **kwargs):
        self.app = app
        self.log = MiAZLog('MiAZ.RepoSettings')
        self.name = 'repo-settings'
        appconf = self.app.get_config('App')
        repo_id = appconf.get('current').replace('_', ' ')
        self.title = _('Settings for repository') + ' ' + repo_id
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
            i_id = item_type.__config_name__
            i_title = item_type.__title__
            i_title_plural = _(item_type.__title_plural__)
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
            icon_name = f"io.github.t00m.MiAZ-res-{i_id.lower()}"
            icon = self.icman.get_image_by_name(icon_name)
            icon.set_hexpand(False)
            icon.set_pixel_size(16)
            title = _(i_title_plural)
            label = self.factory.create_label(f"<b>{title}</b>")
            label.set_xalign(0.0)
            label.set_hexpand(True)
            wdgLabel.append(icon)
            wdgLabel.append(label)
            wdgLabel.set_hexpand(True)
            return page, wdgLabel

        # FIXME: User plugins disabled temporary
        for item_type in [Country, Group, Purpose, SentBy, SentTo, Plugin]:
            page, label = create_tab(item_type)
            notebook.append_page(page, label)

    def update(self, *args):
        appconf = self.app.get_config('App')
        repo_id = appconf.get('current')
        title = f"Settings for repository {repo_id}"
        self.set_title(title)

        # FIXME: User plugins disabled temporary
        for item_type in [Country, Group, Purpose, SentBy, SentTo, Plugin]:
            try:
                i_title = item_type.__title_plural__
                widget_title = f"configview-{i_title}"
                configview = self.app.get_widget(widget_title)
                configview.update_config()
                configview.update_views()
            except Exception as error:
                # FIXME: investigate this error
                pass
        # ~ self.log.debug("Repository UI updated according to current settings")


