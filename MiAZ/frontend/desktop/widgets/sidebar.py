#!/usr/bin/python3
# File: sidebar.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Sidebar widget

from gettext import gettext as _

from gi.repository import Adw, Gtk  # type:ignore

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country, Purpose, SentBy, SentTo, Date


class MiAZSidebar(Adw.Bin):
    """Main Sidebar built with Gtk.Box (no Adw.Sidebar, compatible with
    Libadwaita < 1.7 / Debian 13)."""
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
        repo_id = config['App'].get('current') or 'MiAZ'
        self.set_title(repo_id)
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

        self.dropdowns = self.app.add_widget('ws-dropdowns', {})
        self.app.add_widget('plugin-dropdowns', [])

        dd_size_group = self.app.add_widget(
            'sidebar-dropdown-size-group',
            Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL))

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        repo_id = config['App'].get('current') or 'MiAZ'
        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_bar.set_margin_top(6)
        title_bar.set_margin_bottom(6)
        title_bar.set_margin_start(6)
        title_bar.set_margin_end(6)

        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<big><b>{repo_id}</b></big>")
        lbl_title.set_hexpand(True)
        lbl_title.set_halign(Gtk.Align.START)
        lbl_title.set_valign(Gtk.Align.CENTER)
        lbl_title.set_ellipsize(3)
        self.app.add_widget('sidebar-title', lbl_title)

        title_bar.append(lbl_title)
        title_bar.append(button_settings)
        title_bar.append(button_clear)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        filters_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        filters_box.set_margin_start(12)
        filters_box.set_margin_end(12)
        filters_box.set_margin_top(6)
        filters_box.set_margin_bottom(6)

        # Search entry
        searchentry = self.app.add_widget('searchentry', Gtk.Entry())
        searchentry.set_hexpand(True)
        dd_size_group.add_widget(searchentry)
        filters_box.append(factory.create_box_filter(_('Free text'), searchentry))

        # Date dropdown
        i_type = Date.__gtype_name__
        dd_date = factory.create_dropdown_generic(
            item_type=Date, ellipsize=False, enable_search=True)
        dd_date.set_size_request(190, -1)
        dd_size_group.add_widget(dd_date)
        self.dropdowns[i_type] = dd_date
        filters_box.append(factory.create_box_filter(_('Date'), dd_date))

        # Field dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = factory.create_dropdown_generic(item_type=item_type)
            dropdown.set_size_request(190, -1)
            dd_size_group.add_widget(dropdown)
            self.dropdowns[i_type] = dropdown
            filters_box.append(factory.create_box_filter(i_title, dropdown))

        # Concept entry (free text, filters only by Concept field)
        searchentry_concept = self.app.add_widget('searchentry-concept', Gtk.Entry())
        searchentry_concept.set_hexpand(True)
        dd_size_group.add_widget(searchentry_concept)
        filters_box.append(factory.create_box_filter(_('Concept'), searchentry_concept))

        # Plugin section — plugins append their own filter rows here
        plugin_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.app.add_widget('sidebar-plugin-section', plugin_box)
        filters_box.append(plugin_box)
        scroll.set_child(filters_box)
        main_box.append(title_bar)
        main_box.append(separator)
        main_box.append(scroll)
        self.set_child(main_box)

    def setup_custom_filters(self, *args):
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
        lbl_title = self.app.get_widget('sidebar-title')
        if lbl_title is not None:
            lbl_title.set_markup(f"<big><b>{title.replace('_', ' ')}</b></big>")
