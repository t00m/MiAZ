#!/usr/bin/python3
# File: mainwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup widget for the main window

from gettext import gettext as _

from gi.repository import Gdk, Gio, Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.searchbar import SearchBar
from MiAZ.frontend.desktop.widgets.welcome import MiAZWelcome
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace


class MiAZMainWindow(Gtk.Box):
    def __init__(self, app, edit=True):
        self.app = app
        self.log = MiAZLog('MiAZ.Selector')
        super(MiAZMainWindow, self).__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, spacing=0)
        self.win = self.app.get_widget('window')
        self._setup_ui()
        self._setup_event_listener()

    def _setup_ui(self):
        # Widgets
        ## HeaderBar
        headerbar = self.app.add_widget('headerbar', Gtk.HeaderBar())
        self.win.set_titlebar(headerbar)

        ## Stack & Stack.Switcher
        stack = self._setup_stack()
        self.append(stack)

        # Setup system menu
        self._setup_menu_app()

        # Setup headerbar widgets
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()

        # On-Demand SearchBar
        search = self.app.add_widget('searchbar', SearchBar(self.app))
        self.append(search)


    def _setup_event_listener(self):
        evk = Gtk.EventControllerKey.new()
        self.app.add_widget('window-event-controller', evk)
        evk.connect("key-pressed", self._on_key_press)
        self.win.add_controller(evk)

    def _setup_headerbar_left(self):
        factory = self.app.get_service('factory')
        headerbar = self.app.get_widget('headerbar')

        # System menu
        menubutton = self.app.get_widget('headerbar-button-menu-system')
        menubutton.set_has_frame(False)
        menubutton.get_style_context().add_class(class_name='flat')
        menubutton.set_valign(Gtk.Align.CENTER)
        headerbar.pack_start(menubutton)

        # Filters and Search box
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
        self.stack = self.app.add_widget('stack', Gtk.Stack())
        self.switcher = self.app.add_widget('switcher', Gtk.StackSwitcher())
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)
        return self.stack

    def _setup_menu_app(self):
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
        menuitem = factory.create_menuitem('app-help', _('Help'), actions.show_app_help, None, ['<Control>h'])
        section_common_out.append_item(menuitem)
        menuitem = factory.create_menuitem('app-about', _('About MiAZ'), actions.show_app_about, None, ['<Control>h'])
        section_common_out.append_item(menuitem)
        menuitem = factory.create_menuitem('app-quit', _('Exit application'), actions.exit_app, None, ['<Control>q'])
        section_danger.append_item(menuitem)

        menubutton = Gtk.MenuButton(child=factory.create_button_content(icon_name='miaz-system-menu'))
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        menubutton.set_popover(popover=popover)
        self.app.add_widget('headerbar-button-menu-system', menubutton)

    def show_workspace(self, *args):
        actions = self.app.get_service('actions')
        actions.show_stack_page_by_name('workspace')

    def _on_key_press(self, event, keyval, keycode, state):
        actions = self.app.get_service('actions')
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            actions.show_stack_page_by_name('workspace')
        elif keyname == 'F3':
            actions.toggle_workspace_filters()

    def _setup_page_welcome(self):
        stack = self.app.get_widget('stack')
        widget_welcome = self.app.get_widget('welcome')
        if widget_welcome is None:
            widget_welcome = self.app.add_widget('welcome', MiAZWelcome(self.app))
            page_welcome = stack.add_titled(widget_welcome, 'welcome', 'MiAZ')
            page_welcome.set_icon_name('MiAZ')
            page_welcome.set_visible(True)

    def _setup_page_rename(self):
        stack = self.app.get_widget('stack')
        widget_rename = self.app.get_widget('rename')
        if widget_rename is None:
            widget_rename = self.app.add_widget('rename', MiAZRenameDialog(self.app))
            page_rename = stack.add_titled(widget_rename, 'rename', 'MiAZ')
            page_rename.set_icon_name('document-properties')
            page_rename.set_visible(False)

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
