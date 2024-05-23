#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: settings.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Manage App and Repository settings
"""

import os
from gettext import gettext as _

import gi
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZProjects
from MiAZ.frontend.desktop.widgets.configview import MiAZRepositories
from MiAZ.frontend.desktop.widgets.configview import MiAZUserPlugins
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPlugin
from MiAZ.frontend.desktop.widgets.dialogs import CustomDialog
from MiAZ.frontend.desktop.widgets.window import CustomWindow
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy, SentTo, Date
from MiAZ.backend.models import Extension, Project, Repository, Plugin
from MiAZ.backend.config import MiAZConfigRepositories
from MiAZ.backend.pluginsystem import MiAZPluginType


Configview = {}
Configview['Country'] = MiAZCountries
Configview['Group'] = MiAZGroups
Configview['Purpose'] = MiAZPurposes
Configview['SentBy'] = MiAZPeopleSentBy
Configview['SentTo'] = MiAZPeopleSentTo
Configview['Project'] = MiAZProjects
Configview['Plugin'] = MiAZUserPlugins
# ~ Configview['Date'] = Gtk.Calendar

class MiAZAppSettings(CustomWindow):
    __gtype_name__ = 'MiAZAppSettings'

    def __init__(self, app, **kwargs):
        self.app = app
        self.name = 'app-settings'
        self.title = 'Application settings'
        super().__init__(app, self.name, self.title, **kwargs)
        self.util = self.app.get_service('util')

    def _build_ui(self):
        self.set_default_size(1024, 728)
        headerbar = self.app.get_widget('window-%s-headerbar' % self.name)
        self.stack = self.app.add_widget('stack_settings', Gtk.Stack())
        self.stack.set_vexpand(True)
        self.switcher = self.app.add_widget('switcher_settings', Gtk.StackSwitcher())
        self.switcher.set_stack(self.stack)
        self.switcher.set_hexpand(False)
        headerbar.pack_start(self.switcher)
        self.mainbox.append(self.stack)
        widget = self._create_widget_for_repositories()
        page = self.stack.add_titled(widget, 'repos', 'Repositories')
        page.set_visible(True)
        widget = self._create_widget_for_plugins()
        page = self.stack.add_titled(widget, 'plugins', 'Plugins')
        page.set_visible(True)
        self.repo_is_set = False

    def _create_widget_for_repositories(self):
        row = self.factory.create_box_vertical(hexpand=True, vexpand=True)
        hbox = self.factory.create_box_horizontal()
        lblActive = Gtk.Label()
        lblActive.set_markup(_("Current active"))
        self.dd_repo = self.factory.create_dropdown_generic(item_type=Repository, ellipsize=False, enable_search=False)
        btnUseRepo = self.factory.create_button(icon_name='MiAZ', title=_('Load repo'), callback=self._on_use_repo)
        hbox.append(lblActive)
        hbox.append(self.dd_repo)
        hbox.append(btnUseRepo)
        self.actions.dropdown_populate(MiAZConfigRepositories, self.dd_repo, Repository, any_value=False, none_value=False)
        # DOC: By enabling this signal, repos are loaded automatically without pressing the button:
        # ~ self.dd_repo.connect("notify::selected-item", self._on_selected_repo)
        self.config['Repository'].connect('used-updated', self.actions.dropdown_populate, self.dd_repo, Repository, False, False)

        # Load last active repo
        repos_used = self.config['Repository'].load_used()
        self.log.debug("Repositories in use: %s", ','.join(repos_used.keys()))
        repo_active = self.config['App'].get('current')
        self.log.debug("Current active: %s", repo_active)
        if repo_active in repos_used:
            model = self.dd_repo.get_model()
            n = 0
            for item in model:
                if item.id == repo_active:
                    self.dd_repo.set_selected(n)
                n += 1
        row.append(hbox)
        configview = MiAZRepositories(self.app)
        configview.set_hexpand(True)
        configview.set_vexpand(True)
        configview.update()
        row.append(configview)
        return row

    def _on_use_repo(self, *args):
        repo_id = self.dd_repo.get_selected_item().id
        repo_dir = self.dd_repo.get_selected_item().title
        self.config['App'].set('current', repo_id)
        valid = self.app.check_repository()
        if valid:
            window = self.app.get_widget('window-%s' % self.name)
            window.hide()
            workspace = self.app.get_widget('workspace')
            workspace.clean_filters()
            workspace.update()
            self.log.debug("Repository %s loaded successfully", repo_id)
        else:
            self.log.error("Repository %s couldn't be loaded", repo_id)

    def _on_selected_repo(self, dropdown, gparamobj):
        try:
            repo_id = dropdown.get_selected_item().id
            repo_dir = dropdown.get_selected_item().title
            self.log.debug("Repository selected: %s[%s]", repo_id, repo_dir)
            self.config['App'].set('current', repo_id)
            self.app.check_repository()
        except AttributeError:
            # Probably the repository was removed from used view
            pass

    def _update_action_row_repo_source(self, name, dirpath):
        self.row_repo_source.set_title(name)
        self.row_repo_source.set_subtitle(dirpath)
        self.repo_is_set = True

    def is_repo_set(self):
        return self.repo_is_set

    def show_filechooser_source(self, *args):
        filechooser = self.factory.create_filechooser(
                    parent=self.app.win,
                    title=_('Choose target directory'),
                    target = 'FOLDER',
                    callback = self.on_filechooser_response_source,
                    data = None
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response, data):
        dialog.destroy()
        return

    def _create_widget_for_plugins(self):
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        notebook = Gtk.Notebook()
        notebook.set_show_border(False)
        notebook.set_tab_pos(Gtk.PositionType.LEFT)
        widget = self._create_widget_for_system_plugins()
        label = self.factory.create_notebook_label(icon_name='miaz-app-settings', title='System')
        notebook.append_page(widget, label)
        widget = self._create_widget_for_user_plugins()
        label = self.factory.create_notebook_label(icon_name='miaz-res-people', title='User')
        notebook.append_page(widget, label)
        vbox.append(notebook)
        return vbox

    def _create_widget_for_system_plugins(self):
        from MiAZ.backend.pluginsystem import MiAZPluginType
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)
        scrwin = self.factory.create_scrolledwindow()
        vbox.append(scrwin)
        pm = self.app.get_service('plugin-manager')
        pm.add_repo_plugins_dir()

        box = Gtk.ListBox.new()
        box.set_vexpand(True)
        scrwin.set_child(box)
        for plugin in pm.plugins:
            if pm.get_plugin_type(plugin) == MiAZPluginType.SYSTEM:
                title = "<b>%s</b>" % plugin.get_name()
                subtitle = plugin.get_description() + ' (v%s)' % plugin.get_version()
                active = plugin.is_loaded()
                row = self.factory.create_actionrow(title=title, subtitle=subtitle)
                box.append(row)
        return vbox

    def _create_widget_for_user_plugins(self):
        # Trick to remove widgets from  listbox in Gtk 4.8.3 (Debian 11)
        # as the method remove_all is not avaiable only since 4.12 :(
        self.listboxwidgets = []
        vbox = self.factory.create_box_vertical(margin=0, spacing=0, hexpand=True, vexpand=True)

        # Add/Remove
        hbox = self.factory.create_box_horizontal(margin=0, spacing=0, hexpand=True, vexpand=False)
        hbox.get_style_context().add_class(class_name='toolbar')
        hbox.append(self.factory.create_button(icon_name='miaz-list-add', title='Add plugin', callback=self._on_plugin_add))
        hbox.append(self.factory.create_button(icon_name='miaz-list-remove', title='Remove plugin', callback=self._on_plugin_remove))
        vbox.append(hbox)

        # Plugins
        scrwin = self.factory.create_scrolledwindow()
        self.app.add_widget('app-settings-plugins-user-scrwin', scrwin)
        vbox.append(scrwin)
        pm = self.app.get_service('plugin-manager')
        pm.add_repo_plugins_dir()
        view = MiAZColumnViewPlugin(self.app)
        view.set_hexpand(True)
        view.set_vexpand(True)
        self.app.add_widget('app-settings-plugins-user-view', view)
        scrwin.set_child(view)
        self.update_user_plugins()
        return vbox

    def update_user_plugins(self):
        ENV = self.app.get_env()
        plugin_manager = self.app.get_service('plugin-manager')
        plugin_manager.rescan_plugins()
        view = self.app.get_widget('app-settings-plugins-user-view')
        items = []
        item_type = Plugin
        for plugin in plugin_manager.plugins:
            ptype = plugin_manager.get_plugin_type(plugin)
            if ptype == MiAZPluginType.USER:
                pid = plugin.get_module_name()
                plugin_path = os.path.join(ENV['LPATH']['PLUGINS'], '%s.plugin' % pid)
                if os.path.exists(plugin_path):
                    title = plugin.get_description() #+ ' (v%s)' % plugin.get_version()
                    items.append(item_type(id=pid, title=title))
                    self.log.debug("Updating with plugin '%s'", pid)
        view.update(items)

        # ~ # Update listbox
        # ~ for plugin in pm.plugins:
            # ~ if pm.get_plugin_type(plugin) == MiAZPluginType.USER:
                # ~ title = "<b>%s</b>" % plugin.get_name()
                # ~ subtitle = plugin.get_description() + ' (v%s)' % plugin.get_version()
                # ~ active = plugin.is_loaded()
                # ~ row = self.factory.create_actionrow(title=title, subtitle=subtitle)
                # ~ listbox.append(row)
                # ~ self.listboxwidgets.append(row)

    def on_filechooser_response(self, dialog, response, data):
        if response == Gtk.ResponseType.ACCEPT:
            plugin_manager = self.app.get_service('plugin-manager')
            filechooser = dialog.get_filechooser_widget()
            gfile = filechooser.get_file()
            if gfile is None:
                    self.log.debug('No directory set. Do nothing.')
                    # FIXME: Show warning message. Priority: low
                    return
            plugin_path = gfile.get_path()
            imported = plugin_manager.import_plugin(plugin_path)
            self.log.debug("Plugin imported? %s", imported)
            if imported:
                self.update_user_plugins()
        dialog.destroy()

    def _on_plugin_add(self, *args):
        filechooser_dialog = self.factory.create_filechooser(
                    parent=self.app.win,
                    title=_('Upload a plugin'),
                    target = 'FILE',
                    callback = self.on_filechooser_response,
                    data = None
                    )
        plugin_filter = Gtk.FileFilter()
        plugin_filter.add_pattern('*.zip')
        filechooser_widget = filechooser_dialog.get_filechooser_widget()
        filechooser_widget.set_filter(plugin_filter)
        filechooser_dialog.show()

    def _on_plugin_remove(self, *args):
        ENV = self.app.get_env()
        plugin_manager = self.app.get_service('plugin-manager')
        view = self.app.get_widget('app-settings-plugins-user-view')
        module = view.get_selected_items()[0]
        plugin = plugin_manager.get_plugin_info(module.id)
        plugin_manager.unload_plugin(plugin)
        plugin_head = os.path.join(ENV['LPATH']['PLUGINS'], '%s.plugin' % module.id)
        plugin_body = os.path.join(ENV['LPATH']['PLUGINS'], '%s.py' % module.id)
        self.util.filename_delete(plugin_head)
        self.util.filename_delete(plugin_body)
        self.log.debug("Plugin '%s' deleted", module.id)
        self.app.message("Plugin '%s' deleted" % module.id)
        self.update_user_plugins()

    def get_plugin_status(self, name: str) -> bool:
        plugins = self.config['App'].get('plugins')
        if plugins is None:
            return False

        if name in plugins:
            return True
        return False

    def set_plugin_status(self, checkbox, plugin_name):
        active = checkbox.get_active()
        plugins = self.config['App'].get('plugins')
        if plugins is None:
            plugins = []
        if active:
            if not plugin_name in plugins:
                plugins.append(plugin_name)
        else:
            plugins.remove(plugin_name)
        self.config['App'].set('plugins', plugins)


class MiAZRepoSettings(CustomWindow):
    __gtype_name__ = 'MiAZRepoSettings'

    def __init__(self, app, **kwargs):
        self.name = 'repo-settings'
        self.title = 'Repository settings'
        super().__init__(app, self.name, self.title, **kwargs)

    def _build_ui(self):
        self.set_default_size(1024, 728)
        headerbar = self.app.get_widget('window-%s-headerbar' % self.name)
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_border(False)
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.mainbox.append(self.notebook)

        def create_tab(item_type):
            i_type = item_type.__gtype_name__
            i_title = _(item_type.__title__)
            page = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            page.set_vexpand(True)
            page.set_hexpand(True)
            selector = Configview[i_type](self.app)
            selector.set_vexpand(True)
            selector.update()
            box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
            box.append(selector)
            page.set_start_widget(box)
            wdgLabel = self.factory.create_box_horizontal()
            wdgLabel.get_style_context().add_class(class_name='caption')
            icon = self.app.icman.get_image_by_name('miaz-res-%s' % i_type.lower())
            icon.set_hexpand(False)
            icon.set_pixel_size(24)
            label = self.factory.create_label("<b>%s</b>" % i_title)
            label.set_xalign(0.0)
            label.set_hexpand(True)
            wdgLabel.append(icon)
            wdgLabel.append(label)
            wdgLabel.set_hexpand(True)
            return page, wdgLabel

        for item_type in [Country, Group, Purpose, Project, SentBy, SentTo, Plugin]:
            page, label = create_tab(item_type)
            self.notebook.append_page(page, label)

