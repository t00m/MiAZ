#!/usr/bin/python3
# File: mainwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Setup widget for the main window

from gettext import gettext as _

from gi.repository import Adw, Gdk, Gio, Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.searchbar import SearchBar
from MiAZ.frontend.desktop.widgets.welcome import MiAZWelcome
from MiAZ.frontend.desktop.widgets.sidebar import MiAZSidebar
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
        factory = self.app.get_service('factory')

        # Widgets
        ## HeaderBar
        headerbar = self.app.add_widget('headerbar', Adw.HeaderBar())
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()
        # ~ self.append(headerbar)

        # View Stack
        self.view_stack: Adw.ViewStack = Adw.ViewStack()

        # Split View
        self.split_view: Adw.NavigationSplitView = Adw.NavigationSplitView(
            show_content=True,
            max_sidebar_width=300,
            min_sidebar_width=200,
            sidebar=Adw.NavigationPage(child=MiAZSidebar(self.app), title=_("Sidebar")),
            content=Adw.NavigationPage(child=self.view_stack, title=_("Documents"), width_request=360),
        )
        self.split_view.set_vexpand(True)
        # ~ self.split_view.set_collapsed(True)

        ## Stack & Stack.Switcher
        box = factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        box.append(headerbar)
        stack = self._setup_stack()
        box.append(stack)

        # Welcome page
        page_welcome = self.app.get_widget('welcome')
        if page_welcome is None:
            self._setup_page_welcome()

        # ~ workspace = self.app.add_widget('workspace', MiAZWorkspace(self.app))
        self.view_stack.add_titled(child=box, name="Workspace", title=_("Workspace"),
        )

        self.append(self.split_view)

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
        self.stack = self.app.add_widget('stack', Gtk.Stack())
        self.switcher = self.app.add_widget('switcher', Gtk.StackSwitcher())
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)
        return self.stack

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
            page_welcome.set_icon_name('io.github.t00m.MiAZ')
            page_welcome.set_visible(True)

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
