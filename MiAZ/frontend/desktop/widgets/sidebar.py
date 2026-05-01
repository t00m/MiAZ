#!/usr/bin/python
# File: sidebar.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Sidebar widget

from gettext import gettext as _

from gi.repository import Adw, Gtk  # type:ignore

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country, Purpose, SentBy, SentTo, Date


class MiAZSidebar(Adw.Bin):
    """Main Sidebar built around Adw.Sidebar for filter controls."""
    __gtype_name__ = 'MiAZSidebar'

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Sidebar')
        self.set_size_request(320, -1)
        self.__build_ui()
        self.app.add_widget('sidebar', self)
        workflow = self.app.get_service('workflow')
        workflow.connect("repository-switch-finished", self._on_repo_switch)

    def _on_repo_switch(self, *args):
        config = self.app.get_config_dict()
        repo_id = config['App'].get('current')
        self.set_title(f"<big><b>{repo_id}</b></big>")
        self.setup_custom_filters()
        self.log.debug(f"Switched to repository {repo_id} > Sidebar updated")

        actions = self.app.get_service('actions')
        configdict = self.app.get_config_dict()
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            actions.dropdown_populate(
                config=configdict[i_type],
                dropdown=self.dropdowns[i_type],
                item_type=item_type,
                any_value=True,
                none_value=True)

    def __build_ui(self) -> None:
        factory = self.app.get_service('factory')
        config = self.app.get_config_dict()

        button_clear = self._setup_clear_filters_button()
        self.app.add_widget('sidebar-button-clear-filters', button_clear)
        button_settings = self._setup_repo_settings_button()
        self.app.add_widget('sidebar-button-repo-settings', button_settings)

        repo_id = config['App'].get('current')
        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<big><b>{repo_id}</b></big>")
        self.app.add_widget('sidebar-title', lbl_title)

        searchentry = self.app.add_widget('searchentry', Gtk.SearchEntry())
        searchentry.set_hexpand(True)
        searchentry.set_margin_start(6)
        searchentry.set_margin_end(6)
        searchentry.set_margin_top(4)
        searchentry.set_margin_bottom(4)

        headerbar = Adw.HeaderBar()
        headerbar.set_show_back_button(False)
        headerbar.set_show_end_title_buttons(False)
        headerbar.set_title_widget(lbl_title)
        headerbar.pack_start(button_settings)
        headerbar.pack_end(button_clear)

        adw_sidebar = self._setup_adw_sidebar()

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(headerbar)
        toolbar_view.add_top_bar(searchentry)
        toolbar_view.set_content(adw_sidebar)

        self.set_child(toolbar_view)

    def _setup_adw_sidebar(self) -> Adw.Sidebar:
        factory = self.app.get_service('factory')

        self.dropdowns = self.app.add_widget('ws-dropdowns', {})
        self.app.add_widget('plugin-dropdowns', [])

        adw_sidebar = Adw.Sidebar()

        # Plugin section — plugins append Adw.SidebarItem objects here
        plugin_section = self.app.add_widget(
            'sidebar-plugin-section', Adw.SidebarSection())
        adw_sidebar.append(plugin_section)

        # Main filters section
        main_section = Adw.SidebarSection()

        # Date dropdown
        i_type = Date.__gtype_name__
        dd_date = factory.create_dropdown_generic(
            item_type=Date, ellipsize=False, enable_search=True)
        dd_date.set_hexpand(True)
        self.dropdowns[i_type] = dd_date
        main_section.append(Adw.SidebarItem(title=_('Date'), suffix=dd_date))

        # Field dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            dropdown = factory.create_dropdown_generic(item_type=item_type)
            dropdown.set_hexpand(True)
            self.dropdowns[i_type] = dropdown
            main_section.append(
                Adw.SidebarItem(title=_(item_type.__title__), suffix=dropdown))

        adw_sidebar.append(main_section)
        return adw_sidebar

    def setup_custom_filters(self, *args):
        # Register a detached widget so legacy plugins that append to
        # 'sidebar-box-custom-filters' don't crash.
        if self.app.get_widget('sidebar-box-custom-filters') is None:
            factory = self.app.get_service('factory')
            row = factory.create_box_vertical(margin=3, spacing=6, hexpand=True)
            self.app.add_widget('sidebar-box-custom-filters', row)

    def _setup_clear_filters_button(self):
        factory = self.app.get_service('factory')
        button = factory.create_button(
            icon_name='io.github.t00m.MiAZ-entry_clear',
            tooltip=_('Clear all filters'),
            css_classes=['flat'],
            callback=self.clear_filters)
        self.app.add_widget('headerbar-button-clear-filters', button)
        return button

    def _setup_repo_settings_button(self):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        button = factory.create_button(
            icon_name='io.github.t00m.MiAZ-emblem-system-symbolic',
            tooltip=_('Repository management'),
            css_classes=['flat'],
            callback=actions.show_repository_settings)
        self.app.add_widget('headerbar-button-repo-settings', button)
        return button

    def clear_filters(self, *args):
        workspace = self.app.get_widget('workspace')
        self.log.debug(f"Workspace loaded? {workspace.is_loaded()}")
        if workspace.is_loaded():
            workspace.clear_filters()
            self.log.debug("All filters cleared")

    def set_title(self, title: str = ''):
        sidebar_title = self.app.get_widget('sidebar-title')
        sidebar_title.set_markup(title.replace('_', ' '))
