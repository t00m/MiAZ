#!/usr/bin/python3
# File: mainwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup widget for the main window

from gettext import gettext as _

from gi.repository import Adw, Gdk, Gio, Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, SentBy, SentTo, Date, Project
from MiAZ.frontend.desktop.widgets.searchbar import SearchBar
from MiAZ.frontend.desktop.widgets.pages import MiAZWelcome
from MiAZ.frontend.desktop.widgets.pages import MiAZPageNotFound
from MiAZ.frontend.desktop.widgets.sidebar import MiAZSidebar
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace


class MiAZMainWindow(Gtk.Box):
    def __init__(self, app, edit=True):
        self.app = app
        self.log = MiAZLog('MiAZ.MainWindow')
        super(MiAZMainWindow, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.win = self.app.get_widget('window')
        self._setup_ui()
        self._setup_event_listener()



    def _setup_ui(self):
        factory = self.app.get_service('factory')

        # Widgets
        ## HeaderBar
        headerbar = self.app.add_widget('headerbar', Adw.HeaderBar())

        # Hide back button
        # https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/method.HeaderBar.set_show_back_button.html
        # Button doesn't behave as expected. When sidebar is uncollpased, it takes the whole page. Content is gone.
        headerbar.set_show_back_button(False) # This is ugly. FIXME
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()

        # header toolbar
        toolbar = self._setup_toolbar_top()
        headerbar.set_title_widget(toolbar)

        ## Stack & Stack.Switcher
        vmainbox = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        hmainbox = factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=True)
        content = self._setup_stack()
        content.set_hexpand(True)
        sidebar = MiAZSidebar(self.app)
        sidebar.set_hexpand(False)
        vmainbox.append(headerbar)
        vmainbox.append(hmainbox)
        hmainbox.append(sidebar)
        hmainbox.append(content)

        # Welcome page
        page_welcome = self.app.get_widget('welcome')
        if page_welcome is None:
            self._setup_page_welcome()

        # Page Not found
        page = self.app.get_widget('page-notfound')
        if page is None:
            self._setup_page_404()


        # Workspace page
        # ~ self.view_stack.add_titled(child=box, name="Workspace", title=_("Workspace"),
        # ~ )

        # ~ self.append(self.split_view)
        self.append(vmainbox)

    def _setup_event_listener(self):
        evk = Gtk.EventControllerKey.new()
        self.app.add_widget('window-event-controller', evk)
        evk.connect("key-pressed", self._on_key_press)
        self.win.add_controller(evk)

    def _setup_headerbar_left(self):
        factory = self.app.get_service('factory')
        headerbar = self.app.get_widget('headerbar')

        # Box for filters button and search entry
        hbox = factory.create_box_horizontal(margin=0, spacing=0)
        hbox.get_style_context().add_class(class_name='linked')
        self.app.add_widget('headerbar-left-box', hbox)
        headerbar.pack_start(hbox)


    def _setup_headerbar_right(self):
        factory = self.app.get_service('factory')
        headerbar = self.app.get_widget('headerbar')
        hbox = factory.create_box_horizontal(margin=0, spacing=0)
        hbox.get_style_context().add_class(class_name='linked')
        self.app.add_widget('headerbar-right-box', hbox)
        headerbar.pack_end(hbox)

    def _setup_headerbar_center(self):
        pass

    def _setup_stack(self):
        viewstack = self.app.add_widget('stack', Adw.ViewStack())
        switcher = self.app.add_widget('switcher', Adw.ViewSwitcher())
        switcher.set_stack(viewstack)
        viewstack.set_vexpand(True)
        return viewstack

    def show_workspace(self, *args):
        actions = self.app.get_service('actions')
        actions.show_stack_page_by_name('workspace')

    def _on_key_press(self, event, keyval, keycode, state):
        actions = self.app.get_service('actions')
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            # ~ actions.show_stack_page_by_name('workspace')
            self.log.debug("Escape key pressed by user")
            tgbSidebar = self.app.get_widget('workspace-togglebutton-filters')
            active = tgbSidebar.get_active()
            tgbSidebar.set_active(not active)
        elif keyname == 'F3':
            actions.toggle_workspace_filters()

    def _setup_page_welcome(self):
        stack = self.app.get_widget('stack')
        widget_welcome = self.app.get_widget('welcome')
        if widget_welcome is None:
            widget_welcome = self.app.add_widget('welcome', MiAZWelcome(self.app))
            page_welcome = stack.add_titled(widget_welcome, 'welcome', 'MiAZ')
            page_welcome.set_icon_name('io.github.t00m.MiAZ')
            page_welcome.set_visible(True)
            headerbar = self.app.get_widget('headerbar')
            headerbar.set_visible(True)
            tgbSidebar = self.app.get_widget('workspace-togglebutton-filters')
            tgbSidebar.set_active(False)
            tgbSidebar.set_visible(False)
            btnWorkspace = self.app.get_widget('workspace-menu')
            btnWorkspace.set_visible(False)

    def _setup_page_404(self):
        stack = self.app.get_widget('stack')
        widget_notfound = self.app.get_widget('page-404')
        if widget_notfound is None:
            widget_notfound = self.app.add_widget('page-404', MiAZPageNotFound(self.app))
            page_not_found = stack.add_titled(widget_notfound, 'page-404', 'MiAZ')
            self.app.add_widget('page-404', page_not_found)
            page_not_found.set_icon_name('io.github.t00m.MiAZ-dialog-warning-symbolic')
            page_not_found.set_visible(True)

    def _setup_widget_rename(self):
        pass
        # ~ stack = self.app.get_widget('stack')
        # ~ widget_rename = self.app.get_widget('rename')
        # ~ if widget_rename is None:
            # ~ widget_rename = self.app.add_widget('rename', MiAZRenameDialog(self.app))
            # ~ page_rename = stack.add_titled(widget_rename, 'rename', 'MiAZ')
            # ~ page_rename.set_icon_name('document-properties')
            # ~ page_rename.set_visible(False)

    def _setup_page_workspace(self):
        stack = self.app.get_widget('stack')
        widget_workspace = self.app.get_widget('workspace')
        if widget_workspace is None:
            widget_workspace = self.app.add_widget('workspace', MiAZWorkspace(self.app))
            page_workspace = stack.add_titled(widget_workspace, 'workspace', 'MiAZ')
            page_workspace.set_icon_name('document-properties')
            page_workspace.set_visible(True)
            actions = self.app.get_service('actions')
            actions.show_stack_page_by_name('workspace')
        return widget_workspace

    def _setup_toolbar_top(self):
        factory = self.app.get_service('factory')
        hdb_left = self.app.get_widget('headerbar-left-box')
        hdb_right = self.app.get_widget('headerbar-right-box')
        hdb_right.get_style_context().add_class(class_name='linked')


        ## Show/Hide Filters
        tgbSidebar = factory.create_button_toggle('io.github.t00m.MiAZ-sidebar-show-left-symbolic', callback=self._on_sidebar_toggled)
        self.app.add_widget('workspace-togglebutton-filters', tgbSidebar)
        tgbSidebar.set_tooltip_text("Show sidebar and filters")
        tgbSidebar.set_active(True)
        tgbSidebar.set_hexpand(False)
        tgbSidebar.get_style_context().add_class(class_name='dimmed')
        # ~ tgbSidebar.get_style_context().remove_class(class_name='flat')
        # ~ tgbSidebar.set_valign(Gtk.Align.CENTER)
        hdb_left.append(tgbSidebar)

        # Workspace Menu
        hbox = factory.create_box_horizontal(margin=0, spacing=6, hexpand=False)
        popovermenu = self._setup_menu_selection()
        label = Gtk.Label()
        self.btnDocsSel = Gtk.MenuButton()
        self.app.add_widget('workspace-menu', self.btnDocsSel)
        self.btnDocsSel.set_always_show_arrow(True)
        self.btnDocsSel.set_child(label)
        self.popDocsSel = Gtk.PopoverMenu()
        self.popDocsSel.set_menu_model(popovermenu)
        self.btnDocsSel.set_popover(popover=self.popDocsSel)
        self.btnDocsSel.set_sensitive(True)
        hbox.append(self.btnDocsSel)

        # Pending documents toggle button
        button = factory.create_button_toggle( icon_name='io.github.t00m.MiAZ-rename',
                                        title='Review',
                                        tooltip='There are documents pending of review'
                                    )
        self.app.add_widget('workspace-togglebutton-pending-docs', button)
        button.set_has_frame(True)
        button.set_visible(False)
        button.set_active(False)
        hbox.append(button)

        return hbox

    def _on_sidebar_toggled(self, *args):
        """ Sidebar collapsed when active = False"""
        sidebar = self.app.get_widget('sidebar')
        toggleButtonFilters = self.app.get_widget('workspace-togglebutton-filters')
        active = toggleButtonFilters.get_active()
        if sidebar is not None:
            sidebar.set_visible(active)

    def _setup_menu_selection(self):
        menu_selection = self.app.add_widget('workspace-menu-selection', Gio.Menu.new())
        section_common_in = self.app.add_widget('workspace-menu-selection-section-common-in', Gio.Menu.new())
        section_common_out = self.app.add_widget('workspace-menu-selection-section-common-out', Gio.Menu.new())
        section_common_app = self.app.add_widget('workspace-menu-selection-section-app', Gio.Menu.new())
        section_danger = self.app.add_widget('workspace-menu-selection-section-danger', Gio.Menu.new())
        menu_selection.append_section(None, section_common_in)
        menu_selection.append_section(None, section_common_out)
        menu_selection.append_section(None, section_common_app)
        menu_selection.append_section(None, section_danger)

        ## Add
        submenu_add = Gio.Menu.new()
        menu_add = Gio.MenuItem.new_submenu(
            label = _('Add new...'),
            submenu = submenu_add,
        )
        section_common_in.append_item(menu_add)
        self.app.add_widget('workspace-menu-in-add', submenu_add)

        ## Export
        submenu_export = Gio.Menu.new()
        menu_export = Gio.MenuItem.new_submenu(
            label = _('Export...'),
            submenu = submenu_export,
        )
        section_common_out.append_item(menu_export)
        self.app.add_widget('workspace-menu-selection-menu-export', menu_export)
        self.app.add_widget('workspace-menu-selection-submenu-export', submenu_export)

        return menu_selection
