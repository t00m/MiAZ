#!/usr/bin/python3
# File: mainwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup widget for the main window

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
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
        content = self._setup_stack()
        content.set_hexpand(True)
        content.set_vexpand(True)
        sidebar = MiAZSidebar(self.app)

        paned = self.app.add_widget('main-paned', Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True))
        paned.set_start_child(sidebar)
        paned.set_end_child(content)
        paned.set_position(320)
        paned.set_resize_start_child(False)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        vmainbox.append(headerbar)
        vmainbox.append(paned)

        # Welcome page
        page_welcome = self.app.get_widget('welcome')
        if page_welcome is None:
            self._setup_page_welcome()

        # Page Not found
        page = self.app.get_widget('page-notfound')
        if page is None:
            self._setup_page_404()

        # Page WebBrowser
        page = self.app.get_widget('page-webbrowser')
        if page is None:
            self._setup_webbrowser()

        toast_overlay = self.app.add_widget('toast-overlay', Adw.ToastOverlay())
        toast_overlay.set_child(vmainbox)
        self.append(toast_overlay)

    def _setup_event_listener(self):
        """Setup an event listener for mainwindow"""
        evk = Gtk.EventControllerKey.new()
        evk.connect('key-pressed', self._on_key_pressed)
        self.app.add_widget('window-event-controller', evk)
        self.win.add_controller(evk)
        plugin_system = self.app.get_service('plugin-system')
        if plugin_system is not None:
            plugin_system.connect('plugins-updated', self._on_plugins_updated)
        self._footer_menu_appended_to = None
        self.app.connect('application-started', self._on_application_started)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        actions = self.app.get_service('actions')
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if keyval == Gdk.KEY_Return:
            actions.document_display_selected()
            return True
        if ctrl and keyval == Gdk.KEY_BackSpace:
            actions.document_rename()
            return True
        if ctrl and keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
            actions.document_delete()
            return True
        return False

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
        actions = self.app.get_service('actions')
        headerbar = self.app.get_widget('headerbar')
        hbox = factory.create_box_horizontal(margin=0, spacing=0)
        hbox.add_css_class('linked')
        self.app.add_widget('headerbar-right-box', hbox)
        headerbar.pack_end(hbox)

        # View document button (visible when exactly 1 item selected)
        btn_view = factory.create_button(
            icon_name='io.github.t00m.MiAZ-view-document',
            tooltip=_('View document'),
            callback=actions.document_display_selected)
        btn_view.set_visible(False)
        self.app.add_widget('headerbar-button-view', btn_view)
        hbox.append(btn_view)

        # Rename document button (visible when exactly 1 item selected)
        btn_rename = factory.create_button(
            icon_name='io.github.t00m.MiAZ-rename',
            tooltip=_('Rename document'),
            callback=actions.document_rename)
        btn_rename.set_visible(False)
        self.app.add_widget('headerbar-button-rename', btn_rename)
        hbox.append(btn_rename)

        # Delete document button (visible when at least 1 item selected)
        btn_delete = factory.create_button(
            icon_name='io.github.t00m.MiAZ-edit-delete-symbolic',
            tooltip=_('Delete documents'),
            callback=actions.document_delete)
        btn_delete.add_css_class('destructive-action')
        btn_delete.set_visible(False)
        self.app.add_widget('headerbar-button-delete', btn_delete)
        hbox.append(btn_delete)

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
            widget_workspace.connect('workspace-view-updated', self._on_workspace_menu_update)
            # Double-click on a row → view document
            view = self.app.get_widget('workspace-view')
            if view is not None and hasattr(view, 'cv'):
                view.cv.connect('activate', lambda cv, pos: actions.document_display_selected())
        return widget_workspace

    def _on_application_started(self, *args):
        GLib.idle_add(self._append_footer_menu_deferred)

    def _append_footer_menu_deferred(self):
        menu = self.app.get_widget('workspace-menu-selection')
        if menu is not None and menu is not self._footer_menu_appended_to:
            self._prepend_repo_title_section(menu)
            self._append_repo_management_section(menu)
            self._footer_menu_appended_to = menu
        return GLib.SOURCE_REMOVE

    def _on_plugins_updated(self, *args):
        """Rebuild workspace-menu-selection whenever plugins are loaded or unloaded."""
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return

        # During initial batch loading each plugin handles its own startup(); skip the full
        # rebuild loop to avoid calling startup() on already-started plugins on every load.
        if not self.app.get_plugins_loaded():
            return

        # Replace the menu model with a fresh Gio.Menu
        new_main_menu = Gio.Menu.new()
        self.app.add_widget('workspace-menu-selection', new_main_menu)
        new_plugins_section = Gio.Menu.new()
        self.app.add_widget('workspace-plugins-section', new_plugins_section)
        new_main_menu.append_section(None, new_plugins_section)
        btn_workspace_menu = self.app.get_widget('workspace-menu')
        if btn_workspace_menu is not None:
            popover = btn_workspace_menu.get_popover()
            if popover is not None:
                popover.set_menu_model(new_main_menu)

        self.app.remove_widgets_with_prefix('workspace-menu-plugins-')

        # For every currently loaded plugin, reset its started flag then call startup()
        # directly so it reinstalls its menu entry without waiting for workspace-loaded
        plugin_manager = self.app.get_service('plugin-system')
        for plugin_info in plugin_manager.plugins:
            if not plugin_manager.is_plugin_loaded(plugin_info):
                continue
            plugin_name = plugin_info.get_name()
            plugin_obj = self.app.get_widget(f'plugin-{plugin_name}')
            if plugin_obj is None:
                continue
            if hasattr(plugin_obj, 'plugin'):
                plugin_obj.plugin.set_started(False)
            if hasattr(plugin_obj, 'startup') and callable(plugin_obj.startup):
                try:
                    plugin_obj.startup()
                except Exception as error:
                    self.log.error(f"Error rebuilding menu for plugin {plugin_name}: {error}")

        self._prepend_repo_title_section(new_main_menu)
        self._append_repo_management_section(new_main_menu)
        self._footer_menu_appended_to = new_main_menu

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
        tooltip += _('{ns} documents selected\n').format(ns=s)
        tooltip += _('{nv} documents in this view\n').format(nv=v)
        tooltip += _('{nr} documents in this repository').format(nr=t)
        workspace_menu.set_tooltip_markup(tooltip)

        # Toggle headerbar button visibility based on selection
        btn_view = self.app.get_widget('headerbar-button-view')
        if btn_view is not None:
            btn_view.set_visible(s == 1)
        btn_rename = self.app.get_widget('headerbar-button-rename')
        if btn_rename is not None:
            btn_rename.set_visible(s == 1)
        btn_delete = self.app.get_widget('headerbar-button-delete')
        if btn_delete is not None:
            btn_delete.set_visible(s >= 1)

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
        hbox.set_homogeneous(True)
        popovermenu = self._setup_menu_selection()
        label = Gtk.Label()
        btnDocsSel  = Gtk.MenuButton()
        btnDocsSel.add_css_class('accent')
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
        """Create workspace menu with a dedicated section for plugin entries."""
        menu = self.app.add_widget('workspace-menu-selection', Gio.Menu.new())
        plugins_section = self.app.add_widget('workspace-plugins-section', Gio.Menu.new())
        menu.append_section(None, plugins_section)
        return menu

    def _prepend_repo_title_section(self, menu):
        """Prepend the current repository name as the first section of menu."""
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        repo_id = self.app.get_config('App').get('current') or 'MiAZ'
        repo_name = repo_id.replace('_', ' ')
        section = Gio.Menu.new()
        section.append_item(factory.create_menuitem(
            'show-repo-title',
            _('Repository {name}').format(name=repo_name),
            actions.show_repository_settings,
            None, []))
        menu.prepend_section(None, section)

    def _append_repo_management_section(self, menu):
        """Append a separator + Repository Management entry at the bottom of menu."""
        pass # Disabled
        # ~ factory = self.app.get_service('factory')
        # ~ actions = self.app.get_service('actions')
        # ~ section = Gio.Menu.new()
        # ~ section.append_item(factory.create_menuitem(
            # ~ 'show-repo-management',
            # ~ _('Repository Management'),
            # ~ actions.show_repository_settings,
            # ~ None, []))
        # ~ menu.append_section(None, section)

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
        menuitem = factory.create_menuitem('app-about', _('About'), actions.show_app_about, None, ['<Control>b'])
        section_common.append_item(menuitem)
        menuitem = factory.create_menuitem('app-quit', _('Exit'), actions.exit_app, None, ['<Control>q'])
        section_bottom.append_item(menuitem)

        menubutton = Gtk.MenuButton(child=factory.create_button_content(icon_name='io.github.t00m.MiAZ'))
        menubutton.set_has_frame(False)
        menubutton.add_css_class('flat')
        menubutton.set_valign(Gtk.Align.CENTER)
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        menubutton.set_popover(popover=popover)
        self.app.add_widget('headerbar-button-menu-system', menubutton)

        return menubutton
