#!/usr/bin/python
# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager

# Code initially borrowed from:
# Copyright 2023-2024 Vlad Krupinskii <mrvladus@yandex.ru>
# SPDX-License-Identifier: MIT


from gi.repository import Adw, GObject, Gio, Gtk  # type:ignore

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, SentBy, SentTo, Date
from MiAZ.frontend.desktop.services.factory import MiAZBox


def MiAZToolbarView(
    top_bars: list[Gtk.Widget] = None,
    bottom_bars: list[Gtk.Widget] = None,
    **kwargs,
) -> Adw.ToolbarView:
    """Create AdwToolbarView with top and bottom bars added"""

    toolbar_view: Adw.ToolbarView = Adw.ToolbarView(**kwargs)

    if top_bars:
        for child in top_bars:
            toolbar_view.add_top_bar(child)

    if bottom_bars:
        for child in bottom_bars:
            toolbar_view.add_bottom_bar(child)

    return toolbar_view


def MiAZHeaderBar(
    start_children: list[Gtk.Widget] = None,
    end_children: list[Gtk.Widget] = None,
    **kwargs,
) -> Adw.HeaderBar:
    """Create AdwHeaderBar with children packed"""

    hb: Adw.HeaderBar = Adw.HeaderBar(**kwargs)
    hb.set_show_back_button(True)
    hb.set_show_end_title_buttons(False)

    if start_children:
        for child in start_children:
            hb.pack_start(child)

    if end_children:
        for child in end_children:
            hb.pack_end(child)

    return hb

class SidebarTitle(Adw.Bin):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.title = ''


class MiAZSidebar(Adw.Bin):
    """Main Sidebar"""
    __gtype_name__ = 'MiAZSidebar'

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Sidebar')
        self.set_size_request(350, -1)
        self.config = self.app.get_config_dict()
        self.__build_ui()
        self.app.add_widget('sidebar', self)
        workflow = self.app.get_service('workflow')
        workflow.connect("repository-switch-finished", self._on_repo_switch)

    def _on_repo_switch(self, *args):
        config = self.app.get_config_dict()
        repo_id = config['App'].get('current')
        title = _(f"<big><b>{repo_id}</b></big>")
        self.set_title(title)
        # ~ searchentry = self.app.get_widget('searchentry')
        self.clear_filters()
        self.setup_custom_filters()
        row = self.app.get_widget('sidebar-box-custom-filters')
        workspace = self.app.get_widget('workspace')
        workspace.update()
        self.log.debug(f"Switched to repository {repo_id} > Sidebar updated")

        # Connect signals to repository config
        self.config = self.app.get_config_dict()
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            config = self.config[i_type]
            actions.dropdown_populate(config, self.dropdowns[i_type], item_type, True, True)

    def __build_ui(self) -> None:
        factory = self.app.get_service('factory')
        config = self.app.get_config_dict()

        # Clear filters button
        button_clear_filters = self._setup_clear_filters_button()
        self.app.add_widget('sidebar-button-clear-filters', button_clear_filters)
        button_repository_settings = self._setup_repo_settings_button()
        self.app.add_widget('sidebar-button-repo-settings', button_repository_settings)

        # Sidebar title
        repo_id = config['App'].get('current')
        boxTitle = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        self.app.add_widget('sidebar-box-title', boxTitle)
        lblTitle = Gtk.Label()
        lblTitle.set_markup(_(f"<big><b>{repo_id}</b></big>"))
        boxTitle.append(lblTitle)
        boxTitle.set_valign(Gtk.Align.CENTER)
        self.app.add_widget('sidebar-title', lblTitle)

        # Dropdown filters
        toolbar_filters = self._setup_toolbar_filters()
        toolbar_filters.set_margin_top(12)
        self.app.add_widget('workspace-toolbar-filters', toolbar_filters)

        # Status page
        self.status_page = Gtk.Label()

        # Create sidebar
        self.set_child(
            MiAZToolbarView(
                top_bars=[
                    MiAZHeaderBar(
                        title_widget=boxTitle,
                        start_children=[button_repository_settings],
                        end_children=[button_clear_filters],
                    )
                ],
                content=MiAZBox(
                    orientation=Gtk.Orientation.VERTICAL,
                    children=[  toolbar_filters,
                                self.status_page,
                    ],
                ),
            )
        )

    def update_repo_status(self, *args):
        repo_status = self.app.get_widget('sidebar-status-repo')
        repository = self.app.get_service('repository')
        workspace = self.app.get_widget('workspace')
        num_docs = len(workspace.get_selected_items())
        config = self.app.get_config_dict()
        repo_id = config['App'].get('current')
        description = f"<big>Repository {repo_id}\n<b>{num_docs} documents</b></big>"
        repo_status.set_description(description)
        self.log.debug(description)

    def _setup_toolbar_filters(self):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')

        box_filters = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
        viewstack = self.app.add_widget('sidebar-stack-filters', Adw.ViewStack())
        switcher = self.app.add_widget('sidebar-switcher-filters', Adw.ViewSwitcher())
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        switcher.set_halign(Gtk.Align.CENTER)
        switcher.set_stack(viewstack)
        viewstack.set_vexpand(True)
        box_filters.append(switcher)
        box_filters.append(viewstack)

        # First tab - Main filters
        widget = factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=False)
        body = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.set_margin_top(margin=6)
        body.set_margin_start(margin=12)
        body.set_margin_end(margin=12)
        row = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.append(row)
        widget.append(body)

        ## Search box
        searchentry = self.app.add_widget('searchentry', Gtk.SearchEntry())
        searchentry.set_hexpand(True)
        boxDropdown = factory.create_box_filter('Filter by free text', searchentry)
        row.append(boxDropdown)

        ## Dropdowns
        self.dropdowns = self.app.add_widget('ws-dropdowns', {})

        ### Date dropdown
        i_type = Date.__gtype_name__
        dd_date = factory.create_dropdown_generic(item_type=Date, ellipsize=False, enable_search=True)
        dd_date.set_hexpand(True)
        self.dropdowns[i_type] = dd_date
        boxDropdown = factory.create_box_filter('Date', dd_date)
        row.append(boxDropdown)

        ### Rest of filters dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = factory.create_dropdown_generic(item_type=item_type)
            boxDropdown = factory.create_box_filter(i_title, dropdown)
            row.append(boxDropdown)
            self.dropdowns[i_type] = dropdown


        page_main_filters = viewstack.add_titled(widget, 'main-filters', 'Main filters')
        page_main_filters.set_icon_name('io.github.t00m.MiAZ-filter-symbolic')
        page_main_filters.set_visible(True)

        return box_filters

    def setup_custom_filters(self, *args):
        # Second tab - Custom filters
        if self.app.get_widget('sidebar-box-custom-filters') is None:
            factory = self.app.get_service('factory')
            workspace = self.app.get_widget('workspace')
            workspace_filters = workspace.get_workspace_filters()
            viewstack = self.app.get_widget('sidebar-stack-filters')
            widget = factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=False)
            body = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
            body.set_margin_top(margin=6)
            body.set_margin_start(margin=12)
            body.set_margin_end(margin=12)
            row = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
            self.app.add_widget('sidebar-box-custom-filters', row)
            body.append(row)
            widget.append(body)
            page_custom_fiters = viewstack.add_titled(widget, 'custom-filters', 'Custom filters')
            page_custom_fiters.set_icon_name('io.github.t00m.MiAZ-filter-custom-symbolic')
            page_custom_fiters.set_visible(True)

    def _setup_clear_filters_button(self):
        factory = self.app.get_service('factory')
        button = factory.create_button(icon_name='io.github.t00m.MiAZ-entry_clear', tooltip='Clear all filters', css_classes=['flat'], callback=self.clear_filters)
        self.app.add_widget('headerbar-button-clear-filters', button)

        return button

    def _setup_repo_settings_button(self):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        button = factory.create_button(icon_name='io.github.t00m.MiAZ-emblem-system-symbolic', tooltip='Repository management', css_classes=['flat'], callback=actions.show_repository_settings)
        self.app.add_widget('headerbar-button-clear-filters', button)

        return button

    def clear_filters(self, *args):
        search_entry = self.app.get_widget('searchentry')
        search_entry.set_text('')
        search_entry.emit("activate")
        dropdowns = self.app.get_widget('ws-dropdowns')
        for ddId in dropdowns:
            dropdowns[ddId].set_selected(0)
        workspace_view = self.app.get_widget('workspace-view')
        workspace_view.refilter()
        self.log.debug("All filters cleared")

    def set_title(self, title: str=''):
        sidebar_title = self.app.get_widget('sidebar-title')
        sidebar_title.set_markup(title.replace('_', ' '))

    # ~ def toggle(self, *args):
        # ~ """ Sidebar collapsed when active = False"""
        # ~ if self is not None:
            # ~ toggleButtonFilters = self.app.get_widget('workspace-togglebutton-filters')
            # ~ active = toggleButtonFilters.get_active()
            # ~ self.set_visible(active)
