# File: mainwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup widget for the main window

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.pages import MiAZWelcome
from MiAZ.frontend.desktop.widgets.pages import MiAZPageNotFound
from MiAZ.frontend.desktop.widgets.webbrowser import MiAZWebBrowser
from MiAZ.frontend.desktop.widgets.sidebar import MiAZSidebar
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace


class MiAZMainWindow(Gtk.Box):
    __gtype_name__ = 'MiAZMainWindow'

    # True while the window is too narrow for the desktop layout. One
    # breakpoint sets it and everything that has to change reads it, so the
    # width at which MiAZ rearranges itself is written down in one place.
    narrow = GObject.Property(
        type=bool, default=False, nick='Narrow layout',
        blurb='The window is too narrow for the desktop layout')

    def __init__(self, app, edit=True):
        self.app = app
        self.log = MiAZLog('MiAZ.MainWindow')
        super(MiAZMainWindow, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.win = self.app.get_widget('window')
        self._setup_ui()
        self._setup_event_listener()
        self.app.add_widget('mainwindow', self)

    def _setup_ui(self):
        ENV = self.app.get_env()

        # Content (ViewStack) + sidebar inside an adaptive split view
        content = self._setup_stack()
        content.set_hexpand(True)
        content.set_vexpand(True)
        sidebar = MiAZSidebar(self.app)

        split_view = self.app.add_widget('main-split-view', Adw.OverlaySplitView())
        split_view.set_sidebar(sidebar)
        split_view.set_content(content)
        split_view.set_min_sidebar_width(300)
        split_view.set_max_sidebar_width(360)
        split_view.set_sidebar_width_fraction(0.25)

        # Sidebar visibility is core behaviour (formerly the MiAZSidebarTB
        # plugin). On first run the sidebar starts hidden; afterwards the last
        # state is remembered. The headerbar reveal button and the Escape key
        # both toggle it (see _setup_headerbar_start and _on_key_pressed).
        appconf = self.app.get_config('App')
        if appconf is not None and appconf.exists('sidebar-visible'):
            show_sidebar = bool(appconf.get('sidebar-visible'))
        else:
            show_sidebar = False
            if appconf is not None:
                appconf.set('sidebar-visible', False)
        split_view.set_show_sidebar(show_sidebar)
        split_view.connect('notify::show-sidebar', self._on_sidebar_visibility_changed)

        # HeaderBar
        headerbar = self.app.add_widget('headerbar', Adw.HeaderBar())
        self._setup_headerbar_start(split_view)
        self._setup_headerbar_center()
        self._setup_headerbar_end()

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

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(headerbar)
        toolbar_view.set_content(split_view)

        toast_overlay = self.app.add_widget('toast-overlay', Adw.ToastOverlay())
        toast_overlay.set_child(toolbar_view)
        self.append(toast_overlay)

        # Adaptive: collapse the sidebar into an overlay, show only icons in
        # the workspace view switcher, and put the window into narrow mode.
        breakpoint_ = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 720sp"))
        breakpoint_.add_setter(split_view, "collapsed", True)
        breakpoint_.add_setter(self, "narrow", True)
        switcher = self.app.get_widget('workspace-view-switcher')
        if switcher is not None:
            breakpoint_.add_setter(
                switcher, "display-mode", Adw.InlineViewSwitcherDisplayMode.ICONS)
        self.win.add_breakpoint(breakpoint_)
        self.connect('notify::narrow', self._on_narrow_changed)
        self._on_narrow_changed()

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
        workflow = self.app.get_service('workflow')
        if workflow is not None:
            workflow.connect('repository-switch-finished', self._update_window_title)

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
        if keyval == Gdk.KEY_Escape:
            # Toggle the sidebar without consuming the event, so Escape keeps
            # working for other widgets (search entry, popovers).
            split_view = self.app.get_widget('main-split-view')
            if split_view is not None:
                split_view.set_show_sidebar(not split_view.get_show_sidebar())
            return False
        return False

    def _on_sidebar_visibility_changed(self, split_view, gparam):
        """Persist sidebar visibility so it is remembered across runs."""
        appconf = self.app.get_config('App')
        if appconf is not None:
            appconf.set('sidebar-visible', split_view.get_show_sidebar())

    def _setup_headerbar_start(self, split_view):
        factory = self.app.get_service('factory')
        headerbar = self.app.get_widget('headerbar')

        # Review (pending documents) toggle.
        btn_review = factory.create_button_toggle(
            icon_name='io.github.t00m.MiAZ-rename',
            title=_('Review'),
            tooltip=_('There are documents pending of review'))
        btn_review.set_has_frame(True)
        btn_review.set_visible(False)
        btn_review.set_active(False)
        self.app.add_widget('workspace-togglebutton-pending-docs', btn_review)
        headerbar.pack_start(btn_review)

        # Sidebar reveal toggle
        sidebar_toggle = Gtk.ToggleButton(
            icon_name='io.github.t00m.MiAZ-sidebar-show-left-symbolic')
        sidebar_toggle.add_css_class('flat')
        sidebar_toggle.set_tooltip_text(_(
            'Show or hide the sidebar.\n'
            'Press Escape to toggle it.\n'
            'You can hide this button in Settings ▸ User Interface.'))
        split_view.bind_property(
            'show-sidebar', sidebar_toggle, 'active',
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL)
        appconf = self.app.get_config('App')
        button_visible = appconf.get('sidebar-button-visible') if appconf is not None else None
        if button_visible is None:
            button_visible = True
            if appconf is not None:
                appconf.set('sidebar-button-visible', True)
        sidebar_toggle.set_visible(bool(button_visible))
        self.app.add_widget('headerbar-button-sidebar-toggle', sidebar_toggle)
        headerbar.pack_start(sidebar_toggle)

        # Plugin/workspace controls box (plugins append their buttons here)
        hbox = factory.create_box_horizontal(margin=0, spacing=6)
        self.app.add_widget('headerbar-left-box', hbox)
        headerbar.pack_start(hbox)

    def _setup_headerbar_center(self):
        """Build the workspace document-count menu and the pending-docs
        toggle and install them as the header bar's centered title widget.
        """
        factory = self.app.get_service('factory')
        headerbar = self.app.get_widget('headerbar')
        self._setup_menu_selection()
        switcher = Adw.InlineViewSwitcher()
        switcher.set_display_mode(Adw.InlineViewSwitcherDisplayMode.BOTH)
        switcher.set_homogeneous(True)
        switcher.set_valign(Gtk.Align.CENTER)
        switcher.set_visible(False)
        self.app.add_widget('workspace-view-switcher', switcher)
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        center_box.append(switcher)
        # Kept, because a narrow window takes it off the header bar and a wide
        # one puts it back.
        self._headerbar_center = center_box
        headerbar.set_title_widget(center_box)

    def _setup_headerbar_end(self):
        # Filled by pack() below, moved onto the workspace toolbar as soon as
        # there is one: the header bar is built before the workspace exists.
        self._document_actions = []
        factory = self.app.get_service('factory')
        actions = self.app.get_service('actions')
        headerbar = self.app.get_widget('headerbar')

        # Primary menu (rightmost)
        menubutton = self._setup_menu_system()
        headerbar.pack_end(menubutton)

        # What acts on documents belongs with the documents, not up in the
        # header bar: the toolbar above the list is where the user is looking.
        # It falls back to the header bar if there is no workspace yet.
        def pack(widget):
            headerbar.pack_end(widget)
            self._document_actions.append(widget)

        # "Add" menu. Aggregates every Import-category plugin actions
        add_menu = self.app.add_widget('headerbar-add-menu', Gio.Menu.new())
        btn_add = Gtk.MenuButton()
        btn_add.set_tooltip_text(_('Add or import documents'))
        btn_add.set_child(Adw.ButtonContent(icon_name='list-add-symbolic', label=_('Add')))
        btn_add.set_menu_model(add_menu)
        btn_add.set_visible(False)
        self.app.add_widget('headerbar-button-add', btn_add)
        pack(btn_add)

        # Document preview, off by default. It comes up from the bottom.
        btn_preview = factory.create_button_toggle(
            icon_name='image-x-generic-symbolic',
            tooltip=_('Show the document page'),
            callback=self._on_toggle_preview)
        self.app.add_widget('headerbar-button-preview', btn_preview)
        pack(btn_preview)

        # The same four actions as one menu, for a window too narrow to carry
        # them as buttons. Only one of the two is ever visible.
        btn_actions = Gtk.MenuButton()
        btn_actions.set_icon_name('view-more-symbolic')
        btn_actions.set_tooltip_text(_('Actions for the selected documents'))
        btn_actions.add_css_class('flat')
        btn_actions.set_visible(False)
        self.app.add_widget('headerbar-button-actions', btn_actions)
        pack(btn_actions)

        # Per-selection action buttons. Plugins add theirs to this same box,
        # so the Notes button and the rest travel with it.
        hbox = factory.create_box_horizontal(margin=0, spacing=6)
        self.app.add_widget('headerbar-right-box', hbox)
        pack(hbox)

        # View document button (visible when exactly 1 item selected)
        btn_view = factory.create_button(
            icon_name='io.github.t00m.MiAZ-view-document',
            tooltip=_('View document'),
            callback=actions.document_display_selected,
            css_classes=['flat'])
        btn_view.set_visible(False)
        self.app.add_widget('headerbar-button-view', btn_view)
        hbox.append(btn_view)

        # Rename document button (visible when exactly 1 item selected)
        btn_rename = factory.create_button(
            icon_name='io.github.t00m.MiAZ-rename',
            tooltip=_('Rename document'),
            callback=actions.document_rename,
            css_classes=['flat'])
        btn_rename.set_visible(False)
        self.app.add_widget('headerbar-button-rename', btn_rename)
        hbox.append(btn_rename)

        # Mass rename menu button (visible when 2+ items selected). It uses the
        # same icon as single rename and its menu lists every mass-rename
        # function (date, country, group, purpose, concept, sent by, sent to).
        btn_massrename = Gtk.MenuButton()
        btn_massrename.set_icon_name('io.github.t00m.MiAZ-rename')
        btn_massrename.set_tooltip_text(_('Mass rename documents'))
        btn_massrename.add_css_class('flat')
        massrename_menu = self.app.get_widget('massrename-menu')
        if massrename_menu is not None:
            btn_massrename.set_menu_model(massrename_menu)
        btn_massrename.set_visible(False)
        self.app.add_widget('headerbar-button-massrename', btn_massrename)
        hbox.append(btn_massrename)

        # Delete document button (visible when at least 1 item selected)
        btn_delete = factory.create_button(
            icon_name='io.github.t00m.MiAZ-edit-delete-symbolic',
            tooltip=_('Delete documents'),
            callback=actions.document_delete)
        btn_delete.add_css_class('destructive-action')
        btn_delete.add_css_class('flat')
        btn_delete.set_visible(False)
        self.app.add_widget('headerbar-button-delete', btn_delete)
        hbox.append(btn_delete)

    def _on_narrow_changed(self, *args):
        """Strip the header bar down to what fits when the window is narrow.

        The buttons that carry a label lose it, and the four per-selection
        buttons become one menu. Together that is what lets the window reach
        a phone width; the breakpoint that sets 'narrow' cannot fire at a
        width the header bar refuses to allow.
        """
        narrow = self.get_property('narrow')

        # The Add button keeps its icon and drops the word next to it.
        btn_add = self.app.get_widget('headerbar-button-add')
        if btn_add is not None:
            content = btn_add.get_child()
            if isinstance(content, Adw.ButtonContent):
                content.set_label('' if narrow else _('Add'))

        # The Review toggle carries a word and a count; narrow it keeps the
        # count. The workspace owns that string, so it does the relabelling.
        workspace = self.app.get_widget('workspace')
        if workspace is not None:
            workspace.update_review_button()

        # The page switcher is the widest thing in the header bar. It is taken
        # out by dropping the title widget rather than by hiding the switcher,
        # whose own visibility belongs to the repository switch. An empty
        # Adw.WindowTitle, not None: with no title widget GTK falls back to the
        # window title, a label that will not ellipsize and costs 69px.
        headerbar = self.app.get_widget('headerbar')
        center = getattr(self, '_headerbar_center', None)
        if headerbar is not None and center is not None:
            headerbar.set_title_widget(Adw.WindowTitle() if narrow else center)

        # A phone shell draws the window controls itself, and 108px of them is
        # a third of the screen. Quit stays on Ctrl+Q and in the primary menu.
        if headerbar is not None:
            headerbar.set_show_end_title_buttons(not narrow)
            headerbar.set_show_start_title_buttons(not narrow)

        self._update_selection_widgets()

    @classmethod
    def _button_label(cls, widget):
        """The Gtk.Label inside a button, however deep the factory nested it."""
        child = widget.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Label):
                return child
            found = cls._button_label(child)
            if found is not None:
                return found
            child = child.get_next_sibling()
        return None

    def _build_actions_menu(self, selected):
        """The per-selection actions as a menu, matching the buttons shown."""
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        menu = Gio.Menu.new()
        if selected == 1:
            menu.append_item(factory.create_menuitem(
                'narrow-document-view', _('View document'),
                lambda *_a: actions.document_display_selected()))
            menu.append_item(factory.create_menuitem(
                'narrow-document-rename', _('Rename document'),
                lambda *_a: actions.document_rename()))
        if selected > 1:
            massrename_menu = self.app.get_widget('massrename-menu')
            if massrename_menu is not None:
                menu.append_submenu(_('Mass renaming'), massrename_menu)
        if selected >= 1:
            menu.append_item(factory.create_menuitem(
                'narrow-document-delete', _('Delete documents'),
                lambda *_a: actions.document_delete()))
        return menu

    def _on_toggle_preview(self, button, *args):
        sheet = self.app.get_widget('workspace-preview-sheet')
        if sheet is not None:
            sheet.set_open(button.get_active())

    def _update_window_title(self, *args):
        repo_id = self.app.get_service('repo').get_active_id()
        subtitle = repo_id.replace('_', ' ') if repo_id else ''
        if getattr(self, '_window_title', None) is not None:
            self._window_title.set_subtitle(subtitle)

    def _setup_stack(self):
        viewstack = self.app.add_widget('stack', Adw.ViewStack())
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
            if btnWorkspace is not None:
                btnWorkspace.set_visible(False)
            switcher = self.app.get_widget('workspace-view-switcher')
            if switcher is not None:
                switcher.set_visible(False)

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
            self._move_document_actions_to_toolbar()
        return widget_workspace

    def _move_document_actions_to_toolbar(self):
        """Put what acts on documents onto the toolbar above them.

        They are created with the header bar, which is built before there is a
        workspace to hold them, so they start there and move across.
        """
        center = self.app.get_widget('workspace-toolbar-center')
        headerbar = self.app.get_widget('headerbar')
        if center is None or headerbar is None:
            return
        for widget in getattr(self, '_document_actions', []):
            if widget.get_parent() is center:
                continue
            headerbar.remove(widget)
            center.append(widget)
        # Review goes next to the view buttons: it chooses which documents
        # are on screen, and that is what the left of the toolbar is for.
        start = self.app.get_widget('workspace-toolbar-start')
        btn_review = self.app.get_widget('workspace-togglebutton-pending-docs')
        # The parent is a box inside the header bar, not the bar itself, so
        # it is checked against where it is going rather than where it is.
        if start is not None and btn_review is not None and btn_review.get_parent() is not start:
            headerbar.remove(btn_review)
            start.append(btn_review)

    def _on_application_started(self, *args):
        GLib.idle_add(self._append_footer_menu_deferred)

    def _append_footer_menu_deferred(self):
        menu = self.app.get_widget('workspace-menu-selection')
        if menu is not None and menu is not self._footer_menu_appended_to:
            self._prepend_repo_title_section(menu)
            self._append_repo_management_section(menu)
            self._footer_menu_appended_to = menu
        # Import plugins have registered their entries by now; build the
        # headerbar Add menu from them.
        self._populate_add_menu()
        return GLib.SOURCE_REMOVE

    def _populate_add_menu(self):
        """Build the headerbar Add menu from the core import actions plus
        every loaded Import plugin."""
        add_menu = self.app.get_widget('headerbar-add-menu')
        if add_menu is None:
            return
        add_menu.remove_all()
        importdoc = self.app.get_service('importdoc')
        if importdoc is not None:
            add_menu.append_item(importdoc.menuitem)
            add_menu.append_item(importdoc.menuitem_dir)
        plugin_manager = self.app.get_service('plugin-system')
        if plugin_manager is not None:
            for plugin_info in plugin_manager.plugins:
                if not plugin_manager.is_plugin_loaded(plugin_info):
                    continue
                plugin_name = plugin_info.get_name()
                plugin_obj = self.app.get_widget(f'plugin-{plugin_name}')
                if plugin_obj is None or not hasattr(plugin_obj, 'plugin'):
                    continue
                try:
                    subcategory = plugin_obj.plugin.get_plugin_info_key('Subcategory')
                except Exception:
                    continue
                if subcategory != 'Import':
                    continue
                menuitem = self.app.get_widget(f'plugin-menuitem-{plugin_name}')
                if menuitem is not None:
                    add_menu.append_item(menuitem)
        self._update_add_button_visibility()

    def _update_add_button_visibility(self):
        """Show the headerbar Add button only when an Import plugin registered."""
        btn_add = self.app.get_widget('headerbar-button-add')
        add_menu = self.app.get_widget('headerbar-add-menu')
        if btn_add is not None and add_menu is not None:
            btn_add.set_visible(add_menu.get_n_items() > 0)

    def _on_plugins_updated(self, *args):
        """Rebuild workspace-menu-selection whenever plugins are loaded or unloaded."""
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return

        if not self.app.get_plugins_loaded():
            return

        # Replace the menu model with a fresh Gio.Menu
        new_main_menu = Gio.Menu.new()
        self.app.add_widget('workspace-menu-selection', new_main_menu)
        new_plugins_section = Gio.Menu.new()
        self.app.add_widget('workspace-plugins-section', new_plugins_section)
        new_main_menu.append_section(None, new_plugins_section)
        self._append_massrename_submenu(new_main_menu)
        self._append_clipboard_item(new_main_menu)
        btn_workspace_menu = self.app.get_widget('workspace-menu')
        if btn_workspace_menu is not None:
            popover = btn_workspace_menu.get_popover()
            if popover is not None:
                popover.set_menu_model(new_main_menu)

        self.app.remove_widgets_with_prefix('workspace-menu-plugins-')

        # Put back what each loaded plugin contributed. This used to clear the
        # plugin's started flag and call startup() again, so every plugin ran
        # its whole setup once per load or unload of any other plugin: a fresh
        # gesture on the column view here, another background scan there. The
        # contributions are recorded when they are made, so the rebuild is a
        # replay and startup() runs once per activation.
        plugin_manager = self.app.get_service('plugin-system')
        for plugin_info in plugin_manager.plugins:
            if not plugin_manager.is_plugin_loaded(plugin_info):
                continue
            plugin_name = plugin_info.get_name()
            try:
                plugin_manager.menus.replay(plugin_name, self.app)
            except Exception as error:
                self.log.error(f"Error rebuilding menu for plugin {plugin_name}: {error}")

        self._prepend_repo_title_section(new_main_menu)
        self._append_repo_management_section(new_main_menu)
        self._footer_menu_appended_to = new_main_menu
        self._populate_add_menu()

    def _on_workspace_menu_update(self, *args):
        stack = self.app.get_widget('stack')
        workspace = self. app.get_widget('workspace')

        s = workspace.get_num_selected_items() # Items selected
        v = workspace.get_num_displayed_items() # Items in view
        t = workspace.get_num_total_items() # Items in repository

        # Document count is shown at the bottom centre of the sidebar
        label = self.app.get_widget('sidebar-doc-count-label')
        label_text = f"<small>{s}</small> / {v} / <big>{t}</big>"
        tooltip = ""
        tooltip += _('{ns} documents selected\n').format(ns=s)
        tooltip += _('{nv} documents in this view\n').format(nv=v)
        tooltip += _('{nr} documents in this repository').format(nr=t)
        if label is not None:
            label.set_markup(label_text)
            label.set_tooltip_markup(tooltip)

        self._selected_count = s
        self._update_selection_widgets()

        searchentry = self.app.get_widget('searchentry')
        if v > 0:
            stack.set_visible_child_name('workspace')
        else:
            stack.set_visible_child_name('page-404')

    def _update_selection_widgets(self):
        """Show the per-selection actions as buttons, or as one menu if narrow.

        Both paths follow the same rule: view and rename need exactly one
        document, mass rename needs more than one, delete needs at least one.
        """
        selected = getattr(self, '_selected_count', 0)
        narrow = self.get_property('narrow')
        wide = not narrow
        for key, visible in (
            ('headerbar-button-view', selected == 1),
            ('headerbar-button-rename', selected == 1),
            ('headerbar-button-massrename', selected > 1),
            ('headerbar-button-delete', selected >= 1),
        ):
            button = self.app.get_widget(key)
            if button is not None:
                button.set_visible(wide and visible)
        btn_actions = self.app.get_widget('headerbar-button-actions')
        if btn_actions is not None:
            btn_actions.set_visible(narrow and selected >= 1)
            if narrow and selected >= 1:
                btn_actions.set_menu_model(self._build_actions_menu(selected))

    def _setup_menu_selection(self):
        """Create workspace menu with a dedicated section for plugin entries."""
        menu = self.app.add_widget('workspace-menu-selection', Gio.Menu.new())
        plugins_section = self.app.add_widget('workspace-plugins-section', Gio.Menu.new())
        menu.append_section(None, plugins_section)
        self._append_massrename_submenu(menu)
        self._append_clipboard_item(menu)
        return menu

    def _append_massrename_submenu(self, menu):
        """Add the core 'Mass renaming' submenu (built by the massrename
        service) to a workspace selection menu. The menu is rebuilt on plugin
        changes, so this is called from both setup paths."""
        massrename_menu = self.app.get_widget('massrename-menu')
        if massrename_menu is not None:
            menu.append_submenu(_('Mass renaming'), massrename_menu)

    def _append_clipboard_item(self, menu):
        """Add the core 'Copy document names' entry to a selection menu.

        Built once by the actions service and appended here, the same way the
        mass-rename submenu is, so a menu rebuild puts it back.
        """
        actions = self.app.get_service('actions')
        menuitem = getattr(actions, 'menuitem_copy_names', None)
        if menuitem is not None:
            menu.append_item(menuitem)

    def _prepend_repo_title_section(self, menu):
        """Prepend the current repository name as the first section of menu."""
        actions = self.app.get_service('actions')
        factory = self.app.get_service('factory')
        repo_id = self.app.get_service('repo').get_active_id() or 'MiAZ'
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
        pass

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
        menuitem = factory.create_menuitem('app-shortcuts', _('Keyboard Shortcuts'), actions.show_app_shortcuts, None, ['<Control>question'])
        section_common.append_item(menuitem)
        # F1 is listed in the shortcuts window, so it has to do something. It
        # opens that same window: MiAZ has no separate manual, and a shortcut
        # advertised and bound to nothing is worse than one that is honest.
        menuitem = factory.create_menuitem('app-help', _('Help'), actions.show_app_help, None, ['F1'])
        section_common.append_item(menuitem)
        menuitem = factory.create_menuitem('app-about', _('About MiAZ'), actions.show_app_about, None, ['<Control>b'])
        section_common.append_item(menuitem)
        menuitem = factory.create_menuitem('app-quit', _('Quit'), actions.exit_app, None, ['<Control>q'])
        section_bottom.append_item(menuitem)

        menubutton = Gtk.MenuButton()
        menubutton.set_icon_name('open-menu-symbolic')
        menubutton.set_tooltip_text(_('Main Menu'))
        menubutton.add_css_class('flat')
        menubutton.set_valign(Gtk.Align.CENTER)
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        menubutton.set_popover(popover=popover)
        self.app.add_widget('headerbar-button-menu-system', menubutton)

        return menubutton
