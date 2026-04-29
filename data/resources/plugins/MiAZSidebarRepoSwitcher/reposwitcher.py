#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: reposwitcher.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: repo switcher plugin
"""

from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import GObject

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.models import Repository
from MiAZ.backend.config import MiAZConfigRepositories

plugin_info = {
        'Module':        'reposwitcher',
        'Name':          'MiAZSidebarRepoSwitcher',
        'Loader':        'Python3',
        'Description':   _('Sidebar Repository switcher'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      'Customisation and Personalisation',
        'Subcategory':   'User Interface'
    }

class MiAZSidebarRepoSwitcher(MiAZExtension):
    __gtype_name__ = 'MiAZSidebarRepoSwitcherPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        ## Get services
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')

        # Connect signals to startup
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        self.log.warning("Plugin deactivated")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # No need of menu item for plugin

            sidebar = self.app.get_widget('sidebar')
            sidebar_box_title = self.app.get_widget('sidebar-box-title')
            sidebar_title = self.app.get_widget('sidebar-title')
            dd_repo = self.app.get_widget('sidebar-repo-switcher')
            if dd_repo is None:
                #### Configure repository dropdown
                dd_repo = self.factory.create_dropdown_generic(item_type=Repository, ellipsize=False, enable_search=True)
                self.app.add_widget('sidebar-repo-switcher', dd_repo)
                dd_repo.set_valign(Gtk.Align.CENTER)
                dd_repo.set_hexpand(False)
                togglebutton = dd_repo.get_first_child()
                togglebutton.set_has_frame(False)
                dd_repo.set_show_arrow(True)
                self.actions.dropdown_populate(MiAZConfigRepositories, dd_repo, Repository, any_value=False, none_value=False)
                sidebar_box_title.remove(sidebar_title)
                sidebar_box_title.append(dd_repo)
                sidebar_box_title.set_hexpand(False)

                # Set active current repository
                config = self.app.get_config_dict()
                repo_id = config['App'].get('current')

                n = 0
                for repo in dd_repo.get_model():
                    if repo.id == repo_id:
                        dd_repo.set_selected(n)
                    n += 1

                dd_repo.connect("notify::selected-item", self._on_use_repo)

            # Plugin configured
            self.plugin.set_started(started=True)

    def _on_use_repo(self, *args):
        """Restart Application to avoid issues with plugins not being able to disable their functionality"""
        dd_repo = self.app.get_widget('sidebar-repo-switcher')
        repo = dd_repo.get_selected_item()
        if repo is None:
            return

        # Save chosen repository
        self.log.debug(f"Repository chosen: {repo.id}")
        config = self.app.get_config_dict()
        config['App'].set('current', repo.id)

        # Restart app
        self.actions.application_restart()
