#!/usr/bin/python
# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Icon manager

import os

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.status import MiAZStatus
from MiAZ.backend.watcher import MiAZWatcher
from MiAZ.backend.projects import MiAZProject
from MiAZ.frontend.desktop.widgets.settings import MiAZRepoSettings


class MiAZWorkflow(GObject.GObject):
    """
    Repository workflow
    """

    __gsignals__ = {
        "repository-switch-started": (GObject.SignalFlags.RUN_LAST, None, ()),
        "repository-switch-finished": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app):
        """
        Initialize workflow service.

        :param app: pointer to MiAZApp
        :type app: MiAZApp
        """
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Workflow')
        self.log.debug("Service Workflow initialized")

    def switch_start(self, *args):
        """Switch from one repository to another."""
        self.log.debug("Repository switch requested")
        actions = self.app.get_service('actions')
        repository = self.app.get_service('repo')
        try:
            self.app.set_status(MiAZStatus.BUSY)
            appconf = self.app.get_config('App')
            repo_loaded = False
            if repository.validate(repository.docs):
                repository.load(repository.docs)
                repo_loaded = True
        except Exception as error:
            #FIXME
            self.log.error(error)
            repo_loaded = False

        repo_id = appconf.get('current')
        self.log.debug(f"Repository '{repo_id}' loaded? {repo_loaded}")

        if repo_loaded:
            self.log.info(f"Repo Working directory: '{repository.docs}'")
            repo_settings = self.app.get_widget('settings-repo')
            if repo_settings is None:
                repo_settings = self.app.add_widget('settings-repo', MiAZRepoSettings(self.app))
                repo_settings.update()
            workspace = self.app.get_widget('workspace')
            workspace.initialize_caches()
            tgbPendingDocs = self.app.get_widget('workspace-togglebutton-pending-docs')
            tgbPendingDocs.connect('toggled', workspace.show_pending_documents)
            if not self.app.get_plugins_loaded():
                self.app.load_plugins()
            self.app.set_status(MiAZStatus.RUNNING)
            actions.show_stack_page_by_name('workspace')
            self.app.emit('application-started')
        else:
            actions.show_stack_page_by_name('welcome')
        window = self.app.get_widget('window')
        window.present()
        return repo_loaded

    def switch_finish(self, *args):
        """Finish switch repository operation"""
        repository = self.app.get_service('repo')
        self.app.set_service('Projects', MiAZProject(self.app))
        watcher = MiAZWatcher()
        watcher.set_path(repository.docs)
        watcher.set_active(active=True)
        self.app.set_service('watcher', watcher)
        self.log.debug("Repository switch finished")

        # Setup stack pages
        mainbox = self.app.get_widget('window-mainbox')
        page_workspace = self.app.get_widget('workspace')
        if page_workspace is None:
            mainbox._setup_page_workspace()

        # Setup Rename widget
        rename_widget = self.app.get_widget('rename')
        if rename_widget is None:
            mainbox._setup_widget_rename()

        headerbar = self.app.get_widget('headerbar')
        headerbar.set_visible(True)
        tgbSidebar = self.app.get_widget('workspace-togglebutton-filters')
        tgbSidebar.set_active(False)
        tgbSidebar.set_visible(False)
        btnWorkspace = self.app.get_widget('workspace-menu')
        btnWorkspace.set_visible(True)

        self.emit("repository-switch-finished")
