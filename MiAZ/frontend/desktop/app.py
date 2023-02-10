#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend import MiAZBackend
from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepo
from MiAZ.frontend.desktop.widgets.menu import MiAZ_MENU_APP
from MiAZ.frontend.desktop.widgets.menubutton import MiAZMenuButton
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.settings import MiAZSettings
from MiAZ.frontend.desktop.widgets.about import MiAZAbout
from MiAZ.frontend.desktop.icons import MiAZIconManager
from MiAZ.frontend.desktop.factory import MiAZFactory
from MiAZ.frontend.desktop.actions import MiAZActions
from MiAZ.frontend.desktop.help import show_shortcuts


class MiAZApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backend = MiAZBackend()
        self.conf = self.backend.conf
        self.log = get_logger("MiAZ.GUI")
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_default_size(1024, 728)
        self.win.set_icon_name('MiAZ')
        self.win.set_default_icon_name('MiAZ')
        # ~ self.win.get_style_context().add_class(class_name='devel')
        self.icman = MiAZIconManager(self)
        self.theme = Gtk.IconTheme.get_for_display(self.win.get_display())
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.actions = MiAZActions(self)
        self.factory = MiAZFactory(self)
        self.build_gui()
        self.listen_to_key_events()
        self.log.debug("Executing MiAZ Desktop mode")
        # ~ self.win.present()

    def listen_to_key_events(self):
        evk = Gtk.EventControllerKey.new()
        evk.connect("key-pressed", self.key_press)
        self.win.add_controller(evk)

    def key_press(self, event, keyval, keycode, state):
        # ~ self.log.debug("Event[%s] > Keyval[%s] > Keycode[%s] > State[%s]", event, keyval, keycode, state)
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            self.show_stack_page_by_name('workspace')
            self.workspace.display_dashboard()
        # ~ self.log.debug(keyname)


    # ~ def create_menu_actions(self):
        # ~ self.factory.create_action('quit', self.exit_app, ['Control_L', 'q'])

    def get_actions(self):
        return self.actions

    def get_backend(self):
        return self.backend

    def get_config(self, name: str):
        return self.backend.conf[name]

    def get_factory(self):
        return self.factory

    def get_icman(self):
        return self.icman

    def get_workspace(self):
        return self.workspace

    def get_header(self):
        return self.header

    def get_settings(self):
        return self.settings

    def _setup_stack(self):
        self.stack = Adw.ViewStack()
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)
        return self.stack

    def setup_status_page(self):
        # ~ self.btnImport.hide()
        status_page = Adw.StatusPage.new()
        status_page.set_description(description="<big>It seems it is the first time using this application.\n\nPlease, create a new repository in order to start working in your AZ</big>")
        status_page.set_icon_name(icon_name='MiAZ-big')
        status_page.set_title(title="%s" % (ENV['APP']['shortname']))
        boxChild = Gtk.CenterBox()
        btnAddRepo = self.factory.create_button('list-add', 'Add repository', callback=self._on_add_new_repo)
        btnAddRepo.set_valign(Gtk.Align.CENTER)
        boxChild.set_center_widget(btnAddRepo)
        status_page.set_child(boxChild)

        self.page_status = self.stack.add_titled(status_page, 'status', 'MiAZ')
        self.page_status.set_icon_name('list-add')
        self.page_status.set_visible(True)
        self.show_stack_page_by_name('status')

    def _on_add_new_repo(self, *args):
        pw = self.get_settings()
        filechooser = self.factory.create_filechooser(
                    parent=self.win,
                    title='Choose target directory',
                    target = 'FOLDER',
                    callback = pw.on_filechooser_response_source
                    )
        ca = filechooser.get_content_area()
        lblDialogInfo = Gtk.Label()
        lblDialogInfo.set_markup('Please, choose an empty directory')
        ca.append(lblDialogInfo)
        filechooser.show()

    def setup_about_page(self):
        about = MiAZAbout(self)
        # ~ widget = about.get_first_child()
        self.page_about = self.stack.add_titled(about, 'about', 'MiAZ')
        self.page_about.set_icon_name('document-properties')
        # ~ self.page_about.set_needs_attention(True)
        # ~ self.page_about.set_badge_number(1)
        # ~ self.page_about.set_visible(True)
        # ~ self.show_stack_page_by_name('about')

    def setup_settings_page(self):
        self.settings = MiAZSettings(self)
        self.page_settings = self.stack.add_titled(self.settings, 'settings', 'MiAZ')
        self.page_settings.set_icon_name('document-properties')
        self.page_settings.set_needs_attention(True)
        self.page_settings.set_badge_number(1)
        self.page_settings.set_visible(True)
        self.show_stack_page_by_name('settings')

    def setup_workspace_page(self):
        # ~ self.btnImport.show()
        self.workspace = MiAZWorkspace(self)
        self.page_workspace = self.stack.add_titled(self.workspace, 'workspace', 'MiAZ')
        self.page_workspace.set_icon_name('document-properties')
        self.page_workspace.set_needs_attention(True)
        self.page_workspace.set_badge_number(1)
        self.page_workspace.set_visible(True)
        self.show_stack_page_by_name('workspace')

    def setup_rename_page(self):
        # ~ self.btnImport.show()
        self.rename = MiAZRenameDialog(self)
        self.page_rename = self.stack.add_titled(self.rename, 'rename', 'MiAZ')
        self.page_rename.set_icon_name('document-properties')
        self.page_rename.set_visible(False)
        # ~ self.show_stack_page_by_name('rename')

    def get_rename_widget(self):
        return self.rename

    def _setup_headerbar_left(self):
        def show_workspace(*args):
            self.show_stack_page_by_name(name='workspace')
            self.btnGoBack.hide()

        self.btnGoBack = self.factory.create_button('miaz-go-back', 'Back', show_workspace)
        self.header.pack_start(self.btnGoBack)
        self.btnGoBack.hide()
        self.log.debug("❌ ✅")

    def _setup_headerbar_right(self):
        # Add Menu Button to the titlebar (Right Side)
        menu = MiAZMenuButton(MiAZ_MENU_APP, 'app-menu', css_classes=['flat'], child=Adw.ButtonContent(icon_name='miaz-system-menu'))
        # ~ menu = MiAZMenuButton(MiAZ_MENU_APP, 'app-menu')

        # and create actions to handle menu actions
        for action, shortcut in [('settings', ['<Ctrl>s']),
                                 ('help', ['<Ctrl>h']),
                                 ('about', ['<Ctrl>b']),
                                 ('close', ['<Ctrl>q']),
                                 ('view', ['<Ctrl>d']),
                                 ('rename', ['<Ctrl>r'])
                                ]:
            self.factory.create_menu_action(action, self.menu_handler, shortcut)
        self.header.pack_end(menu)

    def _setup_headerbar_center(self):
        title_widget = Gtk.Label()
        title_widget.set_markup(ENV['APP']['name'])
        self.header.set_title_widget(title_widget=title_widget)

    def build_gui(self):
        ## HeaderBar
        self.header = Adw.HeaderBar()

        ## Central Box
        self.mainbox = self.factory.create_box_vertical(vexpand=True)
        self.win.set_child(self.mainbox)

        # Widgets
        ## Stack & Stack.Switcher
        stack = self._setup_stack()
        self.mainbox.append(stack)

        # Setup headerbar
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()
        self.win.set_titlebar(self.header)

        # Create settings
        self.setup_about_page()

        # Create settings
        # ~ self.setup_settings_page()

        self.check_repository()
        # ~ self.check_settings()

            # ~ self.setup_status_page()

    def check_repository(self):
        repo = self.backend.repo_config()
        dir_repo = repo['dir_docs']
        self.log.debug("Repo? '%s'", dir_repo)
        if self.backend.repo_validate(dir_repo):
            self.backend.repo_load(dir_repo)
            self.setup_workspace_page()
            self.setup_rename_page()
            self.win.present()
        else:
            self.log.debug("No repo detected in the configuration. Executing asssitant")
            assistant = MiAZAssistantRepo(self)
            assistant.set_transient_for(self.win)
            assistant.set_modal(True)
            assistant.present()
            self.log.debug("Repository assistant displayed")

    def menu_handler(self, action, state):
            """ Callback for  menu actions"""
            name = action.get_name()
            if name == 'settings':
                self.show_settings()
            elif name == 'about':
                self.show_about()
            elif name == 'close':
                self.quit()
            elif name == 'view':
                self.workspace.document_display()
            elif name == 'rename':
                self.workspace.document_rename()
            elif name == 'help':
                self.log.debug('Help!')
                show_shortcuts(self.win)

    def get_stack_page_by_name(self, name: str) -> Adw.ViewStackPage:
        widget = self.stack.get_child_by_name(name)
        return self.stack.get_page(widget)

    def show_stack_page_by_name(self, name: str = 'workspace'):
        self.stack.set_visible_child_name(name)
        title_widget = Gtk.Label()
        title_widget.set_markup('<b>MiAZ - %s</b>' % name.title())
        self.header.set_title_widget(title_widget=title_widget)

    def show_settings(self, *args):
        self.show_stack_page_by_name('settings')
        self.btnGoBack.show()

    def show_about(self, *args):
        self.show_stack_page_by_name('about')
        self.btnGoBack.show()

    def update_title(self, widget=None):
        header = self.get_header()
        title = header.get_title_widget()
        if title is not None:
            header.remove(title)
        if widget is None:
            widget = self.factory.create_label('MiAZ')
        header.set_title_widget(widget)


    def exit_app(self, *args):
        self.quit()

