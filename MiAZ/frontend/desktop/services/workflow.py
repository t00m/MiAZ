#!/usr/bin/python
# File: icm.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Workflow module

from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.status import MiAZStatus
from MiAZ.backend.watcher import MiAZWatcher
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
        self.actions = self.app.get_service('actions')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.log.debug("Service Workflow initialized")

    def switch_start(self, *args):
        """Switch from one repository to another."""
        self.log.debug("Repository switch requested")
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
        self.log.debug(f"Repository error: {repository.get_error()}")

        window = self.app.get_widget('window')
        window.present()
        sidebar = self.app.get_widget('sidebar')
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
            workspace.emit('workspace-view-filtered')
            sidebar.set_visible(True)
            self.actions.show_stack_page_by_name('workspace')
            self.app.emit('application-started')
        else:
            self.actions.show_stack_page_by_name('welcome')
            sidebar.set_visible(False)
            parent = self.app.get_widget('window')
            title = _("Repository management")
            body = repository.get_error()
            self.srvdlg.show_error(title=title, body=body, parent=parent, width=400)

        return repo_loaded

    def switch_finish(self, *args):
        """Finish switch repository operation"""
        repository = self.app.get_service('repo')
        remote = self.util.is_remote_path(repository.docs)
        if remote:
            success, error = self.util.check_remote_directory_sync(repository.docs)
        else:
            success = True
            error = None

        if success:
            self.log.info(f"Remote directory '{repository.docs}' is available.")
        else:
            self.log.info(f"Remote directory '{repository.docs}' is NOT available. Reason: {error}")
            return

        watcher = MiAZWatcher(dirpath=repository.docs, remote=remote)
        watcher.set_active(active=True)
        self.app.set_service('watcher', watcher)
        self.log.debug("Repository switch finished")

        # Setup stack pages
        mainbox = self.app.get_widget('window-mainbox')
        page_workspace = self.app.get_widget('workspace')
        if page_workspace is None:
            mainbox._setup_page_workspace()

        headerbar = self.app.get_widget('headerbar')
        headerbar.set_visible(True)
        btnWorkspace = self.app.get_widget('workspace-menu')
        btnWorkspace.set_visible(True)

        self.emit("repository-switch-finished")
