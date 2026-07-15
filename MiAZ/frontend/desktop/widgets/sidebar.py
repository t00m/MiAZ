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

    def _repo_label(self, repo_id):
        # Show the repository description; fall back to the prettified key when
        # no description is set.
        config = self.app.get_config_dict()
        description = config['Repository'].get_description(repo_id, used=True)
        return description or repo_id.replace('_', ' ')

    def _on_repo_switch(self, *args):
        config = self.app.get_config_dict()
        repo_id = config['App'].get('current') or 'MiAZ'
        self.title_label.set_text(self._repo_label(repo_id))
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
                none_value=False)

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

        # Sidebar header: repository-settings button (left) and clear-filters
        # button (right). The Review toggle now lives on the main header bar
        # (see mainwindow._setup_headerbar_start).
        header = Gtk.CenterBox()
        header.add_css_class('toolbar')
        header.set_margin_start(6)
        header.set_margin_end(6)
        header.set_margin_top(6)
        header.set_margin_bottom(6)
        header.set_start_widget(button_settings)
        header.set_end_widget(button_clear)
        main_box.append(header)

        # Repository title label, kept for use at the bottom of the sidebar
        # (above the document-count label).
        self.title_label = Gtk.Label()
        self.title_label.add_css_class('heading')
        self.title_label.set_ellipsize(True)
        self.title_label.set_halign(Gtk.Align.CENTER)
        repo_id = config['App'].get('current') or 'MiAZ'
        self.title_label.set_text(self._repo_label(repo_id))
        self.app.add_widget('sidebar-title-label', self.title_label)

        box_frame = factory.create_box_vertical(margin=6, spacing=6, hexpand=True, vexpand=True)
        # ~ frame = Gtk.Frame()
        # ~ box_frame.append(frame)
        box_filters = factory.create_box_vertical(margin=0, spacing=6, hexpand=True, vexpand=True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        box_filters.append(scroll)
        box_frame.append(box_filters)

        filters_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        filters_box.set_margin_start(6)
        filters_box.set_margin_end(6)
        filters_box.set_margin_top(6)
        filters_box.set_margin_bottom(6)

        # Search entry
        searchentry = self.app.add_widget('searchentry', Gtk.SearchEntry())
        searchentry.set_hexpand(True)
        searchentry.set_placeholder_text(_('Search in all fields'))
        dd_size_group.add_widget(searchentry)
        filters_box.append(searchentry)

        # Date dropdown
        i_type = Date.__gtype_name__
        dd_date = factory.create_dropdown_generic(
            item_type=Date, ellipsize=False, enable_search=True)
        dd_date.set_size_request(190, -1)
        dd_size_group.add_widget(dd_date)
        self.dropdowns[i_type] = dd_date
        filters_box.append(dd_date)

        # Field dropdowns
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = factory.create_dropdown_generic(item_type=item_type)
            dropdown.set_size_request(190, -1)
            dd_size_group.add_widget(dropdown)
            self.dropdowns[i_type] = dropdown
            filters_box.append(dropdown)

        # Concept entry (free text, filters only by Concept field)
        searchentry_concept = self.app.add_widget('searchentry-concept', Gtk.SearchEntry())
        searchentry_concept.set_hexpand(True)
        searchentry_concept.set_placeholder_text(_('Search in Concept field'))
        dd_size_group.add_widget(searchentry_concept)
        filters_box.append(searchentry_concept)

        # Visual divider between the built-in filters and the
        # plugin-provided custom filters.
        filters_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Plugin section: plugins append their own filter rows here
        plugin_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.app.add_widget('sidebar-plugin-section', plugin_box)
        filters_box.append(plugin_box)

        scroll.set_child(filters_box)
        main_box.append(box_frame)

        # Document-count label at the bottom centre of the sidebar. box_frame
        # already carries vexpand=True, so it claims the slack and the label
        # stays pinned to the bottom edge regardless of window height. It shows
        # "selected / in view / total" and is updated from
        # _on_workspace_menu_update (formerly the headerbar menu button label).
        self.title_label.set_margin_top(6)
        main_box.append(self.title_label)

        doc_count_label = Gtk.Label()
        doc_count_label.add_css_class('title-1')
        doc_count_label.set_halign(Gtk.Align.CENTER)
        doc_count_label.set_margin_top(6)
        doc_count_label.set_margin_bottom(12)
        self.app.add_widget('sidebar-doc-count-label', doc_count_label)
        main_box.append(doc_count_label)

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
            workspace.update()
            self.log.debug("All filters cleared and workspace refreshed")
