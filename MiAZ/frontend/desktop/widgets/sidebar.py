# Copyright 2023-2024 Vlad Krupinskii <mrvladus@yandex.ru>
# SPDX-License-Identifier: MIT


from gi.repository import Adw, GObject, Gio, Gtk  # type:ignore

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
        self.__build_ui()
        self.app.add_widget('sidebar', self)

    def __build_ui(self) -> None:
        # Setup system menu
        self._setup_menu_system()

        # Dropdown filters
        self.toolbar_filters = self._setup_toolbar_filters()
        self.app.add_widget('workspace-toolbar-filters', self.toolbar_filters)

        # Status page
        self.status_page = Adw.StatusPage(
            title=_(""),
            description=_('Personal Document Organizer'),
            icon_name="io.github.t00m.MiAZ",
            css_classes=["compact"],
            vexpand=True,
        )

        menubutton_system = self.app.get_widget('headerbar-button-menu-system')

        self.set_child(
            MiAZToolbarView(
                top_bars=[
                    MiAZHeaderBar(
                        title_widget=Gtk.Label(
                            label=_("MiAZ"),
                            css_classes=["heading"],
                        ),
                        start_children=[menubutton_system],
                        end_children=[],
                    )
                ],
                content=MiAZBox(
                    orientation=Gtk.Orientation.VERTICAL,
                    children=[
                        # ~ Gtk.ScrolledWindow(
                            # ~ propagate_natural_height=True, child=Gtk.Box()
                        # ~ ),
                        self.toolbar_filters,
                        self.status_page,
                    ],
                ),
            )
        )


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

    def _setup_toolbar_filters(self):
        factory = self.app.get_service('factory')
        dropdowns = self.app.get_widget('ws-dropdowns')
        widget = factory.create_box_vertical(spacing=0, margin=0, hexpand=True, vexpand=False)
        body = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.set_margin_top(margin=6)
        body.set_margin_start(margin=12)
        body.set_margin_end(margin=12)
        widget.append(body)
        row_up = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
        row_down = factory.create_box_vertical(margin=3, spacing=6, hexpand=True, vexpand=True)
        body.append(row_up)
        body.append(row_down)
        widget.append(Gtk.Separator.new(orientation=Gtk.Orientation.HORIZONTAL))

        dropdowns = {}
        ### Projects dropdown
        i_type = Project.__gtype_name__
        i_title = _(Project.__title__)
        dd_prj = factory.create_dropdown_generic(item_type=Project)
        boxDropdown = factory.create_box_filter(i_title, dd_prj)
        dropdowns[i_type] = dd_prj
        row_up.append(boxDropdown)

        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            dropdown = factory.create_dropdown_generic(item_type=item_type)
            boxDropdown = factory.create_box_filter(i_title, dropdown)
            row_down.append(boxDropdown)
            dropdowns[i_type] = dropdown

        self.app.add_widget('ws-dropdowns', dropdowns)
        # ~ btnClearFilters = factory.create_button(icon_name='io.github.t00m.MiAZ-entry_clear', tooltip='Clear all filters', css_classes=['flat'], callback=self.clear_filters)
        # ~ boxDropdown = factory.create_box_filter('', btnClearFilters)
        # ~ row_up.append(boxDropdown)

        return widget

    def clear_filters(self, *args):
        # ~ search_entry = self.app.get_widget('searchentry')
        # ~ search_entry.set_text('')
        dropdowns = self.app.get_widget('ws-dropdowns')
        for ddId in dropdowns:
            dropdowns[ddId].set_selected(0)
        # ~ self.log.debug("All filters cleared")
