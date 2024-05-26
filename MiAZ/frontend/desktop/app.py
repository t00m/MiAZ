#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: app.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontent/Desktop entry point
"""

import sys
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk


from MiAZ.backend import MiAZBackend
from MiAZ.backend.log import get_logger
from MiAZ.backend.pluginsystem import MiAZPluginManager, MiAZPluginType
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.widgets.assistant import MiAZAssistantRepo
from MiAZ.frontend.desktop.widgets.workspace import MiAZWorkspace
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.settings import MiAZAppSettings
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings
from MiAZ.frontend.desktop.widgets.about import MiAZAbout
from MiAZ.frontend.desktop.widgets.welcome import MiAZWelcome
from MiAZ.frontend.desktop.widgets.statusbar import MiAZStatusbar
from MiAZ.frontend.desktop.services.icm import MiAZIconManager
from MiAZ.frontend.desktop.services.factory import MiAZFactory
from MiAZ.frontend.desktop.services.actions import MiAZActions
from MiAZ.frontend.desktop.services.help import MiAZHelp



class MiAZApp(Gtk.Application):
    __gsignals__ = {
        "start-application-completed":  (GObject.SignalFlags.RUN_LAST, None, ()),
        "exit-application":  (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    plugins_loaded = False
    _miazobjs = {} # MiAZ Objects

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log = get_logger("MiAZ.App")
        self.log.debug("Starting MiAZ")

    def set_env(self, ENV: dict):
        self._env = ENV
        self._miazobjs['widgets'] = {}
        self._miazobjs['services'] = {}
        self.backend = self.add_service('backend', MiAZBackend(self))
        self.icman = self.add_service('icons', MiAZIconManager(self))
        self.conf = self.backend.get_config()
        GLib.set_application_name(ENV['APP']['name'])
        self.connect('activate', self._on_activate)

    def get_env(self):
        return self._env

    def _on_activate(self, app):
        ENV = self.get_env()
        self.win = self.add_widget('window', Gtk.ApplicationWindow(application=self))
        # ~ self.win.set_default_size(1280, 800)
        self.win.set_icon_name('MiAZ')
        self.win.connect('close-request', self._on_window_close_request)
        self.win.set_default_icon_name('MiAZ')
        self.theme = self.add_service('theme', Gtk.IconTheme.get_for_display(self.win.get_display()))
        self.theme.add_search_path(ENV['GPATH']['ICONS'])
        self.factory = self.add_service('factory', MiAZFactory(self))
        self.actions = self.add_service('actions', MiAZActions(self))
        self._setup_gui()
        self._setup_event_listener()
        self._setup_plugin_manager()
        self.log.debug("Executing MiAZ Desktop mode")
        self.check_repository()
        repository = self.get_service('repo')
        repository.connect('repository-switched', self._update_repo_settings)

    def _on_window_close_request(self, window):
        self.log.debug("Close application requested")
        self.emit("exit-application")
        self.exit_app()

    def _update_repo_settings(self, *args):
        repo_active = self.conf['App'].get('current')
        self.statusbar_message("Switched to repository '%s'" % repo_active)

    def _finish_configuration(self, *args):
        self.log.debug("Finish loading app")

    def load_plugins(self):
        workspace = self.get_widget('workspace')
        workspace_loaded = workspace is not None

        # Load System Plugins
        if workspace_loaded and not self.plugins_loaded:
            self.log.debug("Loading system plugins...")
            plugin_manager = self.get_service('plugin-manager')
            np = 0 # Number of system plugins
            ap = 0   # system plugins activated
            for plugin in self.plugin_manager.plugins:
                try:
                    ptype = plugin_manager.get_plugin_type(plugin)
                    if ptype == MiAZPluginType.SYSTEM:
                        plugin_manager.load_plugin(plugin)
                        ap += 1
                except Exception as error:
                    self.log.error(error)
                if ptype == MiAZPluginType.SYSTEM:
                    np += 1
            self.plugins_loaded = True
            self.log.debug("System plugins loaded: %d/%d", ap, np)
            self.plugins_loaded = True

            # Load User Plugins
            self.log.debug("Loading user plugins for this repository...")
            conf = self.backend.get_config()
            plugins = conf['Plugin']
            np = 0 # Number of user plugins
            ap = 0   # user plugins activated
            for plugin in self.plugin_manager.plugins:
                try:
                    ptype = plugin_manager.get_plugin_type(plugin)
                    if ptype == MiAZPluginType.USER:
                        pid = plugin.get_module_name()
                        if plugins.exists_used(pid):
                            plugin_manager.load_plugin(plugin)
                            ap += 1
                except Exception as error:
                    self.log.error(error)
                if ptype == MiAZPluginType.USER:
                    np += 1

            self.log.debug("User plugins loaded for this repoitory: %d/%d", ap, np)




    def _setup_plugin_manager(self):
        self.plugin_manager = self.add_service('plugin-manager', MiAZPluginManager(self))

    def _setup_event_listener(self):
        evk = Gtk.EventControllerKey.new()
        self.add_widget('window-event-controller', evk)
        evk.connect("key-pressed", self._on_key_press)
        self.win.add_controller(evk)

    def _on_key_press(self, event, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        if keyname == 'Escape':
            self.show_stack_page_by_name('workspace')

    def get_config(self, name: str):
        try:
            config = self.backend.get_config()
            return config[name]
        except KeyError:
            return None

    def _setup_stack(self):
        self.stack = self.add_widget('stack', Gtk.Stack())
        self.switcher = self.add_widget('switcher', Gtk.StackSwitcher())
        self.switcher.set_stack(self.stack)
        self.stack.set_vexpand(True)
        return self.stack

    # ~ def _setup_page_about(self):
        # ~ about = Gtk.AboutDialog(transient_for=self.props.active_window,
                                # ~ modal=True,
                                # ~ program_name='{{name}}',
                                # ~ logo_icon_name='{{appid}}',
                                # ~ version='{{project_version}}',
                                # ~ authors=['{{author_escape}}'],
                                # ~ copyright='© {{year}} {{author_escape}}')
        # ~ # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        # ~ about.set_translator_credits(_('translator-credits'))
        # ~ about.present()

        # ~ widget_about = self.get_widget('about')
        # ~ if widget_about is None:
            # ~ widget_about = self.add_widget('about', MiAZAbout(self))
            # ~ page_about = self.stack.add_titled(widget_about, 'about', 'MiAZ')
            # ~ page_about.set_icon_name('document-properties')

    def _setup_page_help(self):
        widget_help = self.get_widget('help')
        if widget_help is None:
            widget_help = self.add_widget('help', MiAZHelp(self))
            page_help = self.stack.add_titled(widget_help, 'help', 'MiAZ')
            page_help.set_icon_name('document-properties')
            page_help.set_visible(False)

    def _setup_page_welcome(self):
        widget_welcome = self.get_widget('welcome')
        if widget_welcome is None:
            widget_welcome = self.add_widget('welcome', MiAZWelcome(self))
            page_welcome = self.stack.add_titled(widget_welcome, 'welcome', 'MiAZ')
            page_welcome.set_icon_name('MiAZ')
            page_welcome.set_visible(True)

    def _setup_app_settings_window(self):
        widget_settings_app = self.get_widget('settings-app')
        if widget_settings_app is None:
            self.add_widget('settings-app', MiAZAppSettings(self))
            # ~ page_settings_app = self.stack.add_titled(widget_settings_app, 'settings_app', 'MiAZ')
            # ~ page_settings_app.set_icon_name('document-properties')
            # ~ page_settings_app.set_visible(False)

    def _setup_repo_settings_window(self):
        widget_settings_repo = self.get_widget('settings-repo')
        if widget_settings_repo is None:
            self.add_widget('settings-repo', MiAZRepoSettings(self))
            # ~ page_settings_repo = self.stack.add_titled(widget_settings_repo, 'settings_repo', 'MiAZ')
            # ~ page_settings_repo.set_icon_name('document-properties')
            # ~ page_settings_repo.set_visible(False)

    def _setup_page_workspace(self):
        widget_workspace = self.get_widget('workspace')
        if widget_workspace is None:
            widget_workspace = self.add_widget('workspace', MiAZWorkspace(self))
            page_workspace = self.stack.add_titled(widget_workspace, 'workspace', 'MiAZ')
            page_workspace.set_icon_name('document-properties')
            page_workspace.set_visible(True)
            self.show_stack_page_by_name('workspace')

    def _setup_page_rename(self):
        widget_rename = self.get_widget('rename')
        if widget_rename is None:
            widget_rename = self.add_widget('rename', MiAZRenameDialog(self))
            page_rename = self.stack.add_titled(widget_rename, 'rename', 'MiAZ')
            page_rename.set_icon_name('document-properties')
            page_rename.set_visible(False)

    def _setup_menu_app(self):
        # Add system menu button to the titlebar (left Side)
        widgets = []

        ## Current Repository Settings
        menu_repo = self.add_widget('workspace-menu-repo', Gio.Menu.new())
        section_common_in = self.add_widget('workspace-menu-repo-section-in', Gio.Menu.new())
        section_common_out = self.add_widget('workspace-menu-repo-section-out', Gio.Menu.new())
        section_danger = self.add_widget('workspace-menu-repo-section-danger', Gio.Menu.new())
        menu_repo.append_section(None, section_common_in)
        menu_repo.append_section(None, section_common_out)
        menu_repo.append_section(None, section_danger)

        # ~ ## Actions in
        # ~ menuitem = self.factory.create_menuitem(name='repo_settings', label='Repository settings', callback=self._on_handle_menu_repo, data=None, shortcuts=[])
        # ~ section_common_in.append_item(menuitem)

        # ~ ## Actions out
        # ~ submenu_backup = Gio.Menu.new()
        # ~ menu_backup = Gio.MenuItem.new_submenu(
            # ~ label = 'Backup...',
            # ~ submenu = submenu_backup,
        # ~ )
        # ~ section_common_out.append_item(menu_backup)
        # ~ menuitem = self.factory.create_menuitem('backup-config', '...only config', self._on_handle_menu_repo, None, [])
        # ~ submenu_backup.append_item(menuitem)
        # ~ menuitem = self.factory.create_menuitem('backup-data', '...only data', self._on_handle_menu_repo, None, [])
        # ~ submenu_backup.append_item(menuitem)
        # ~ menuitem = self.factory.create_menuitem('backup-all', '...config and data', self._on_handle_menu_repo, None, [])
        # ~ submenu_backup.append_item(menuitem)

        button = self.factory.create_button(icon_name='document-properties', callback=self.show_repo_settings)
        row = self.factory.create_actionrow(title=_('Repository settings'), subtitle=_('Manage current repository'), suffix=button)
        widgets.append(row)

        ## Application Settings
        button = self.factory.create_button('miaz-app-settings', callback=self.show_app_settings)
        row = self.factory.create_actionrow(title=_('Application settings'), subtitle=_('Manage MiAZ configuration'), suffix=button)
        widgets.append(row)

        ## Help
        button = self.factory.create_button('miaz-app-help')
        row = self.factory.create_actionrow(title=_('Help'), subtitle=_('Get help and tips'), suffix=button)
        widgets.append(row)

        ## About
        # ~ Everything you always wanted to know about this application but didn't dare to ask :)
        button = self.factory.create_button('miaz-app-about', callback=self.show_app_about)
        row = self.factory.create_actionrow(title=_('About'), subtitle=_("About this application"), suffix=button)
        widgets.append(row)


        ## Quit
        button = self.factory.create_button('miaz-app-quit', callback=self.exit_app)
        row = self.factory.create_actionrow(title=_('Quit'), subtitle=_('Terminate this application'), suffix=button)
        widgets.append(row)

        menubutton = self.factory.create_button_popover(icon_name='miaz-system-menu', title='', widgets=widgets)
        # ~ menubutton.get_style_context().add_class(class_name='flat')
        self.add_widget('headerbar-button-menu-system', menubutton)

        # ~ menu_headerbar = self.add_widget('menu-headerbar', Gio.Menu.new())
        # ~ section_common_in = Gio.Menu.new()
        # ~ section_common_out = Gio.Menu.new()
        # ~ section_danger = Gio.Menu.new()
        # ~ menu_headerbar.append_section(None, section_common_in)
        # ~ menu_headerbar.append_section(None, section_common_out)
        # ~ menu_headerbar.append_section(None, section_danger)
        # ~ self.add_widget('menu-headerbar-section-common-in', section_common_in)
        # ~ self.add_widget('menu-headerbar-section-common-out', section_common_out)
        # ~ self.add_widget('menu-headerbar-section-common-danger', section_danger)

        # ~ # Actions in
        # ~ menuitem = self.factory.create_menuitem('settings_app', _('Application settings'), self._handle_menu, None, [])
        # ~ section_common_in.append_item(menuitem)

        # ~ # Actions out
        # ~ menuitem = self.factory.create_menuitem('help', _('Help'), self._handle_menu, None, ["<Control>h", "<Control>H"])
        # ~ section_common_out.append_item(menuitem)
        # ~ menuitem = self.factory.create_menuitem('about', _('About'), self._handle_menu, None, [])
        # ~ section_common_out.append_item(menuitem)

        # ~ # Actions danger
        # ~ menuitem = self.factory.create_menuitem('quit', _('Quit'), self._handle_menu, None, ["<Control>q", "<Control>Q"])
        # ~ section_danger.append_item(menuitem)

        # ~ menubutton = self.factory.create_button_menu(icon_name='miaz-system-menu', menu=menu_headerbar)
        # ~ menubutton.set_always_show_arrow(False)
        # ~ self.add_widget('headerbar-button-menu-system', menubutton)
        # ~ self.header.pack_start(menubutton)

    def show_app_settings(self, *args):
        self._setup_app_settings_window()
        window = self.get_widget('settings-app')
        window.set_transient_for(self.win)
        window.set_modal(True)
        window.present()

    def show_repo_settings(self, *args):
        # ~ self.show_stack_page_by_name('settings_repo')
        self._setup_repo_settings_window()
        window = self.get_widget('settings-repo')
        window.set_transient_for(self.win)
        window.set_modal(True)
        window.present()

    def show_app_about(self, *args):
        # ~ window = self.get_widget('window')
        ENV = self.get_env()
        about = Gtk.AboutDialog()
        about.set_transient_for=self.win
        about.set_modal(True)
        about.set_logo_icon_name(ENV['APP']['ID'])
        about.set_program_name(ENV['APP']['name'])
        about.set_version(ENV['APP']['VERSION'])
        about.set_authors(ENV['APP']['documenters'])
        about.set_license_type(Gtk.License.GPL_3_0_ONLY)
        about.set_copyright('© 2024 %s' % ENV['APP']['author'])
        about.set_website('https://github.com/t00m/MiAZ')
        about.set_website_label('Github MiAZ repository')
        about.set_comments(ENV['APP']['description'])
        about.present()

    def show_workspace(self, *args):
        self.show_stack_page_by_name('workspace')

    def _setup_headerbar_left(self):
        headerbar = self.get_widget('headerbar')

        # System menu
        menubutton = self.get_widget('headerbar-button-menu-system')
        menubutton.set_has_frame(False)
        menubutton.get_style_context().add_class(class_name='flat')
        menubutton.set_valign(Gtk.Align.CENTER)
        headerbar.pack_start(menubutton)

        # Filters and Search box
        hbox = self.factory.create_box_horizontal(margin=0, spacing=0)
        hbox.get_style_context().add_class(class_name='linked')
        self.add_widget('headerbar-left-box', hbox)
        headerbar.pack_start(hbox)

    def _setup_headerbar_right(self):
        headerbar = self.get_widget('headerbar')
        hbox = self.factory.create_box_horizontal(margin=0, spacing=0)
        hbox.get_style_context().add_class(class_name='linked')
        self.add_widget('headerbar-right-box', hbox)
        btnBack = self.factory.create_button(icon_name='go-previous', title=_('Back'), callback=self.show_workspace, css_classes=['flat'])
        btnBack.set_visible(False)
        self.add_widget('app-header-button-back', btnBack)
        hbox.append(btnBack)
        headerbar.pack_end(hbox)

    def _setup_headerbar_center(self):
        pass

    def _setup_gui(self):
        # Widgets
        ## HeaderBar
        headerbar = self.add_widget('headerbar', Gtk.HeaderBar())
        self.win.set_titlebar(headerbar)

        ## Central Box
        self.mainbox = self.factory.create_box_vertical(margin=0, spacing=0, vexpand=True)
        self.win.set_child(self.mainbox)

        ## Stack & Stack.Switcher
        stack = self._setup_stack()
        self.mainbox.append(stack)

        # Setup system menu
        self._setup_menu_app()

        # Setup headerbar widgets
        self._setup_headerbar_left()
        self._setup_headerbar_center()
        self._setup_headerbar_right()

        # Create system pages
        # ~ self._setup_page_about()
        self._setup_page_welcome()
        self._setup_page_help()

        # Statusbar
        statusbar = self.add_widget('statusbar', MiAZStatusbar(self))
        self.mainbox.append(statusbar)

    def check_repository(self, repo_id: str = None):
        try:
            repository = self.get_service('repo')
            repo_dir = repository.get('dir_docs')
            self.log.debug("Using repo '%s'", repo_dir)
            if repository.validate(repo_dir):
                repository.load(repo_dir)
                self.log.debug("Setting up workspace")
                if self.get_widget('workspace') is None:
                    self._setup_page_workspace()
                    if not self.plugins_loaded:
                        # ~ self.log.debug("Rloading plugins")
                        self.load_plugins()
                if self.get_widget('rename') is None:
                    self._setup_page_rename()
                if self.get_widget('settings-repo') is None:
                    self._setup_repo_settings_window()
                workspace = self.get_widget('workspace')
                workspace.initialize_caches()
                self.show_stack_page_by_name('workspace')
                valid = True
                statusbar = self.get_widget('statusbar')
                name = self.conf['App'].get('current')
                statusbar.repo(name)
                statusbar.message("Repository loaded")
                self.emit('start-application-completed')
            else:
                valid = False
        except KeyError as error:
            self.log.debug("No repository active in the configuration")
            self.show_stack_page_by_name('welcome')
            valid = False
        window = self.get_widget('window')
        if window is not None:
            window.present()
        return valid

    def _handle_menu(self, action, *args):
        name = action.props.name
        if name == 'settings_app':
            self._setup_app_settings_window()
            window = self.get_widget('settings-app')
            window.set_transient_for(self.win)
            window.set_modal(True)
            window.present()
        elif name == 'about':
            ENV = self.get_env()
            about = Gtk.AboutDialog(transient_for=self.props.active_window,
                                modal=True,
                                program_name=ENV['APP']['name'],
                                logo_icon_name=ENV['APP']['ID'],
                                version=ENV['APP']['VERSION'],
                                authors=ENV['APP']['name'],
                                license=ENV['APP']['license'],
                                copyright='© {{2024}} %s <%s>' % (ENV['APP']['author'], ENV['APP']['author_email']))
            # ~ about.set_translator_credits(_('translator-credits'))
            about.present()
        elif name == 'close':
            self.quit()
        elif name == 'view':
            self.workspace.document_display()
        elif name == 'rename':
            self.workspace.document_rename()
        elif name == 'help':
            self.show_stack_page_by_name('help')
        elif name == 'quit':
            self.exit_app()

    def get_stack_page_by_name(self, name: str) -> Gtk.Stack:
        widget = self.stack.get_child_by_name(name)
        return self.stack.get_page(widget)

    def get_stack_page_widget_by_name(self, name:str) -> Gtk.Widget:
        return self.stack.get_child_by_name(name)

    def show_stack_page_by_name(self, name: str = 'workspace'):
        button = self.get_widget('app-header-button-back')
        toolbar_top = self.get_widget('workspace-toolbar-top')
        if name == 'workspace':
            button.set_visible(False)
            # ~ toolbar_top.set_visible(True)
        elif name == 'welcome':
            button.set_visible(False)
            # ~ toolbar_top.set_visible(False)
        else:
            button.set_visible(True)
            # ~ toolbar_top.set_visible(False)
        self.stack.set_visible_child_name(name)

    def exit_app(self, *args):
        self.emit("exit-application")
        self.quit()

    def add_service(self, name: str, service: GObject.GObject) -> GObject.GObject:
        if name not in self._miazobjs['services']:
            self._miazobjs['services'][name] = service
            return service
        else:
            self.log.error("A service with name '%s' already exists", name)

    def get_service(self, name):
        try:
            return self._miazobjs['services'][name]
        except KeyError:
            return None

    def add_widget(self, name: str, widget):
        # Add widget, but do not overwrite
        if name not in self._miazobjs['widgets']:
            self._miazobjs['widgets'][name] = widget
            return widget
        else:
            self.log.error("A widget with name '%s' already exists", name)

    def set_widget(self, name: str, widget):
        # Overwrite existing widget
        if name in self._miazobjs['widgets']:
            self._miazobjs['widgets'][name] = widget
            return widget
        else:
            self.log.error("A widget with name '%s' doesn't exists", name)

    def get_widget(self, name):
        try:
            return self._miazobjs['widgets'][name]
        except KeyError:
            return None

    def get_widgets(self):
        return self._miazobjs['widgets']

    def remove_widget(self, name: str):
        """
        Remove widget name from dictionary.
        They widget is not destroyed. It must be done by the developer.
        This method is mostly useful during plugins unloading.
        """
        deleted = False
        try:
            del(self._miazobjs['widgets'][name])
            deleted = True
        except KeyError:
            self.log.error("Widget '%s' doesn't exists", name)
        return deleted

    def statusbar_message(self, message: str):
        """Statusbar message"""
        statusbar = self.get_widget('statusbar')
        statusbar.message(message)
