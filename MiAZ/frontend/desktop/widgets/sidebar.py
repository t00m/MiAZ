# Copyright 2023-2024 Vlad Krupinskii <mrvladus@yandex.ru>
# SPDX-License-Identifier: MIT


from gi.repository import Adw, GObject, Gio, Gtk  # type:ignore

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, SentBy, SentTo, Date, Project
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

    if start_children:
        for child in start_children:
            hb.pack_start(child)

    if end_children:
        for child in end_children:
            hb.pack_end(child)

    return hb

class MiAZSidebar(Adw.Bin):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Sidebar')
        self.__build_ui()
        self.app.add_widget('sidebar', self)

    def __build_ui(self) -> None:
        # Setup system menu
        self._setup_menu_system()
        self._setup_clear_filters_button()

        # Status page
        self.status_page = Gtk.Label()

        # ~ TEMPORARY DISABLED
        # ~ repository = self.app.get_service('repository')
        # ~ config = self.app.get_config_dict()
        # ~ repo_id = config['App'].get('current')
        # ~ self.status_page = Adw.StatusPage(
            # ~ title=_(""),
            # ~ description=_(f"<big>Repository {repo_id}</big>"),
            # ~ icon_name="io.github.t00m.MiAZ",
            # ~ css_classes=["compact"],
            # ~ vexpand=True,
        # ~ )
        # ~ self.app.add_widget('sidebar-status-repo', self.status_page)


        menubutton_system = self.app.get_widget('headerbar-button-menu-system')
        button_clear_filters = self.app.get_widget('headerbar-button-clear-filters')
        toolbar_filters = self.app.get_widget('workspace-toolbar-filters')

        self.set_child(
            MiAZToolbarView(
                top_bars=[
                    MiAZHeaderBar(
                        title_widget=Gtk.Label(
                            label=_("MiAZ"),
                            css_classes=["heading"],
                        ),
                        start_children=[menubutton_system],
                        end_children=[button_clear_filters],
                    )
                ],
                content=MiAZBox(
                    orientation=Gtk.Orientation.VERTICAL,
                    children=[
                        # ~ Gtk.ScrolledWindow(
                            # ~ propagate_natural_height=True, child=Gtk.Box()
                        # ~ ),
                        toolbar_filters,
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
        self.log.trace(description)

    def _setup_menu_system(self):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        menu = self.app.add_widget('window-menu-app', Gio.Menu.new())
        section_common_in = self.app.add_widget('app-menu-section-common-in', Gio.Menu.new())
        section_common_out = self.app.add_widget('app-menu-section-common-out', Gio.Menu.new())
        section_danger = self.app.add_widget('app-menu-section-common-danger', Gio.Menu.new())
        menu.append_section(None, section_common_in)
        menu.append_section(None, section_common_out)
        menu.append_section(None, section_danger)
        menuitem = factory.create_menuitem('app-settings', _('Application settings'), actions.show_app_settings, None, ['<Control>s'])
        section_common_in.append_item(menuitem)
        # ~ menuitem = factory.create_menuitem('app-help', _('Help'), actions.show_app_help, None, ['<Control>h'])
        # ~ section_common_out.append_item(menuitem)
        menuitem = factory.create_menuitem('app-about', _('About MiAZ'), actions.show_app_about, None, ['<Control>h'])
        section_common_out.append_item(menuitem)
        menuitem = factory.create_menuitem('app-quit', _('Exit application'), actions.exit_app, None, ['<Control>q'])
        section_danger.append_item(menuitem)

        menubutton = Gtk.MenuButton(child=factory.create_button_content(icon_name='io.github.t00m.MiAZ-system-menu'))
        menubutton.set_has_frame(False)
        menubutton.get_style_context().add_class(class_name='flat')
        menubutton.set_valign(Gtk.Align.CENTER)
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        menubutton.set_popover(popover=popover)
        self.app.add_widget('headerbar-button-menu-system', menubutton)

    def _setup_clear_filters_button(self):
        factory = self.app.get_service('factory')
        button = factory.create_button(icon_name='io.github.t00m.MiAZ-entry_clear', tooltip='Clear all filters', css_classes=['flat'], callback=self.clear_filters)
        self.app.add_widget('headerbar-button-clear-filters', button)


    def clear_filters(self, *args):
        # ~ search_entry = self.app.get_widget('searchentry')
        # ~ search_entry.set_text('')
        dropdowns = self.app.get_widget('ws-dropdowns')
        for ddId in dropdowns:
            dropdowns[ddId].set_selected(0)
        # ~ self.log.debug("All filters cleared")
