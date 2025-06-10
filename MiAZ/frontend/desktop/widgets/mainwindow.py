#!/usr/bin/python3
# File: mainwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup widget for the main window

from gettext import gettext as _

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZItem, Group, Country, Purpose, SentBy, SentTo, Date
from MiAZ.frontend.desktop.services.pluginsystem import plugin_categories
from MiAZ.frontend.desktop.widgets.pages import MiAZWelcome
from MiAZ.frontend.desktop.widgets.pages import MiAZPageNotFound
from MiAZ.frontend.desktop.widgets.webbrowser import MiAZWebBrowser
from MiAZ.frontend.desktop.widgets.sidebar import MiAZSidebar
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace


class MiAZMainWindow(Gtk.Box):
    __gtype_name__ = 'MiAZMainWindow'

    def __init__(self, app, edit=True):
        self.app = app
        self.log = MiAZLog('MiAZ.MainWindow')
        super(MiAZMainWindow, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.win = self.app.get_widget('window')
        self._setup_ui()
        self._setup_event_listener()
        self.app.add_widget('mainwindow', self)

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

        # Page WebBrowser
        page = self.app.get_widget('page-webbroser')
        if page is None:
            self._setup_webbrowser()

        self.append(vmainbox)

    def _setup_event_listener(self):
        """Setup an event listener for mainwindow"""
        evk = Gtk.EventControllerKey.new()
        self.app.add_widget('window-event-controller', evk)
        self.win.add_controller(evk)

    def _setup_headerbar_left(self):
        factory = self.app.get_service('factory')
        headerbar = self.app.get_widget('headerbar')

        # Box for filters button and search entry
        hbox = factory.create_box_horizontal(margin=0, spacing=6)
        self.app.add_widget('headerbar-left-box', hbox)
        headerbar.pack_start(hbox)

        # Setup system menu
        menubutton = self._setup_menu_system()
        hbox.append(menubutton)


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

    def _setup_webbrowser(self):
        stack = self.app.get_widget('stack')
        widget_webbrowser = self.app.get_widget('page-webbrowser')
        if widget_webbrowser is None:
            widget_webbrowser = self.app.add_widget('webbrowser', MiAZWebBrowser(self.app))
            page_webbrowser = stack.add_titled(widget_webbrowser, 'page-webbrowser', 'MiAZ')
            self.app.add_widget('page-webbrowser', page_webbrowser)
            page_webbrowser.set_icon_name('io.github.t00m.MiAZ-webbrowser')
            page_webbrowser.set_visible(True)

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
            widget_workspace.connect('workspace-view-selection-changed', self._on_workspace_menu_update)
            widget_workspace.connect('workspace-view-filtered', self._on_workspace_menu_update)
        return widget_workspace

    def _on_workspace_menu_update(self, *args):
        stack = self.app.get_widget('stack')
        workspace = self. app.get_widget('workspace')
        workspace_menu = self.app.get_widget('workspace-menu')

        s = workspace.get_num_selected_items() # Items selected
        v = workspace.get_num_displayed_items() # Items in view
        t = workspace.get_num_total_items() # Items in repository

        label = workspace_menu.get_child()
        label_text = f"<small>{s}</small> / {v} / <big>{t}</big>"
        label.set_markup(label_text)
        tooltip = ""
        tooltip += f"{s} documents selected\n"
        tooltip += f"{v} documents in this view\n"
        tooltip += f"{t} documents in this repository"
        workspace_menu.set_tooltip_markup(tooltip)
        # ~ self.log.debug(f"filter selected: {s}/{v}/{t}")
        searchentry = self.app.get_widget('searchentry')
        if v > 0:
            stack.set_visible_child_name('workspace')
        else:
            stack.set_visible_child_name('page-404')

    def _setup_toolbar_top(self):
        factory = self.app.get_service('factory')
        hdb_left = self.app.get_widget('headerbar-left-box')
        hdb_right = self.app.get_widget('headerbar-right-box')
        hdb_right.get_style_context().add_class(class_name='linked')

        # Workspace Menu
        hbox = factory.create_box_horizontal(margin=0, spacing=6, hexpand=False)
        popovermenu = self._setup_menu_selection()
        label = Gtk.Label()
        btnDocsSel  = Gtk.MenuButton()
        self.app.add_widget('workspace-menu', btnDocsSel)
        btnDocsSel .set_always_show_arrow(True)
        btnDocsSel .set_child(label)
        popDocsSel = Gtk.PopoverMenu()
        popDocsSel.set_menu_model(popovermenu)
        btnDocsSel .set_popover(popover=popDocsSel)
        btnDocsSel .set_sensitive(True)
        hbox.append(btnDocsSel)

        # Pending documents toggle button
        button = factory.create_button_toggle( icon_name='io.github.t00m.MiAZ-rename',
                                        title=_('Review'),
                                        tooltip=_('There are documents pending of review')
                                    )
        self.app.add_widget('workspace-togglebutton-pending-docs', button)
        button.set_has_frame(True)
        button.set_visible(False)
        button.set_active(False)
        hbox.append(button)

        return hbox

    def _setup_menu_selection(self):
        """Create workspace menu"""

        return self.app.add_widget('workspace-menu-selection', Gio.Menu.new())

    def _setup_menu_system(self):
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        menu = self.app.add_widget('window-menu-app', Gio.Menu.new())
        section_common = self.app.add_widget('app-menu-section-common', Gio.Menu.new())
        section_bottom = self.app.add_widget('app-menu-section-common-bottom', Gio.Menu.new())
        menu.append_section(None, section_common)
        menu.append_section(None, section_bottom)
        menuitem = factory.create_menuitem('app-settings', _('Settings'), actions.show_app_settings, None, ['<Control>s'])
        section_common.append_item(menuitem)
        # ~ menuitem = factory.create_menuitem('app-help', _('Help'), actions.show_app_help, None, ['<Control>h'])
        # ~ section_common.append_item(menuitem)
        menuitem = factory.create_menuitem('app-about', _('About'), actions.show_app_about, None, ['<Control>a'])
        section_common.append_item(menuitem)
        menuitem = factory.create_menuitem('app-quit', _('Exit'), actions.exit_app, None, ['<Control>q'])
        section_bottom.append_item(menuitem)

        menubutton = Gtk.MenuButton(child=factory.create_button_content(icon_name='io.github.t00m.MiAZ'))
        menubutton.set_has_frame(False)
        menubutton.get_style_context().add_class(class_name='flat')
        menubutton.set_valign(Gtk.Align.CENTER)
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        menubutton.set_popover(popover=popover)
        self.app.add_widget('headerbar-button-menu-system', menubutton)

        return menubutton
